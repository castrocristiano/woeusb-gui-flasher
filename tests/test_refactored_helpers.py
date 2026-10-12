"""Unit tests for refactored helper functions in burn_engine, disk_manager, and utils."""

from __future__ import annotations

import io
import re
from unittest.mock import MagicMock, patch

from woeusb_gui_flasher.burn_engine import BurnWorker, ProgressTracker
from woeusb_gui_flasher.disk_manager import DiskManager
from woeusb_gui_flasher.models import (
    BurnConfiguration,
    StorageDevice,
    WindowsISO,
)
from woeusb_gui_flasher.utils import (
    _handle_process_abort,
    _match_iso_install_image,
    _parse_7z_archive_listing,
    _parse_7z_size,
    find_binary,
    inspect_iso_file,
    run_command_streaming,
)

# --- Utils tests ---


def test_find_binary(monkeypatch, tmp_path):
    assert find_binary("python3") is not None
    assert find_binary("nonexistent_binary_xyz_123") is None

    app_bin = tmp_path / "app_bin"
    app_bin.mkdir()
    fake_tool = app_bin / "mock_tool"
    fake_tool.write_text("#!/bin/sh\nexit 0")
    fake_tool.chmod(0o755)

    with patch("woeusb_gui_flasher.utils.Path") as mock_path:
        mock_path.return_value = app_bin
        # default fallback to which
        assert find_binary("ls") is not None


def test_utils_parse_7z_helpers():
    assert _parse_7z_size("Size = 1048576") == 1048576
    assert _parse_7z_size("Size = invalid") == 0

    info = {"has_install_wim": False, "has_install_esd": False, "install_image_size": 0}
    _match_iso_install_image(info, "sources/install.wim", 5000)
    assert info["has_install_wim"] is True
    assert info["install_image_size"] == 5000

    info2 = {"has_install_wim": False, "has_install_esd": False, "install_image_size": 0}
    _match_iso_install_image(info2, r"sources\install.esd", 4000)
    assert info2["has_install_esd"] is True
    assert info2["install_image_size"] == 4000

    # listing
    sample_stdout = (
        "Path = sources/boot.wim\nSize = 100\nPath = sources/install.wim\nSize = 5000000\n"
    )
    info3 = {"has_install_wim": False, "has_install_esd": False, "install_image_size": 0}
    _parse_7z_archive_listing(sample_stdout, info3)
    assert info3["has_install_wim"] is True
    assert info3["install_image_size"] == 5000000


def test_inspect_iso_file(tmp_path):
    iso_file = tmp_path / "win.iso"
    iso_file.write_bytes(b"content")

    with (
        patch("woeusb_gui_flasher.utils.find_binary", return_value="/usr/bin/7z"),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Path = sources/install.wim\nSize = 4500000000\n",
        )
        res = inspect_iso_file(iso_file)
        assert res["is_valid"] is True
        assert res["has_install_wim"] is True
        assert res["install_image_size"] == 4500000000

    with patch("woeusb_gui_flasher.utils.find_binary", return_value=None):
        res_no_7z = inspect_iso_file(iso_file)
        assert res_no_7z["is_valid"] is True
        assert res_no_7z["has_install_wim"] is False


def test_run_command_streaming_and_abort():
    lines = []
    ret = run_command_streaming(["echo", "hello"], line_callback=lines.append)
    assert ret == 0
    assert "hello" in lines

    # abort check
    mock_proc = MagicMock()
    mock_proc.stdout = io.StringIO("line1\nline2\n")
    mock_proc.poll.return_value = None
    abort_code = _handle_process_abort(mock_proc, "echo")
    assert abort_code == -1
    mock_proc.terminate.assert_called_once()


# --- DiskManager helpers tests ---


def test_disk_manager_mountinfo_helpers():
    line = "31 1 8:1 / / rw,relatime - ext4 /dev/sda1 rw"
    maj_min, source = DiskManager._parse_mountinfo_source(line)
    assert maj_min == "8:1"
    assert source == "/dev/sda1"

    invalid_line = "short line"
    m, s = DiskManager._parse_mountinfo_source(invalid_line)
    assert m == ""
    assert s == ""


def test_disk_manager_unmount_targets():
    manager = DiskManager()

    with patch("subprocess.run") as mock_run:
        # udisksctl success
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        assert manager._unmount_with_udisksctl("/bin/udisksctl", "/dev/sdd1") is True

        # udisksctl not mounted
        mock_run.return_value = MagicMock(returncode=1, stderr="Error: not mounted")
        assert manager._unmount_with_udisksctl("/bin/udisksctl", "/dev/sdd1") is True

        # gdbus success
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        assert manager._unmount_with_gdbus("/bin/gdbus", "/dev/sdd1") is True

        # umount
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager._unmount_with_umount("/bin/umount", "/dev/sdd1")

    # unmount single target fallback
    with (
        patch.object(manager, "_unmount_with_udisksctl", return_value=False),
        patch.object(manager, "_unmount_with_gdbus", return_value=False),
        patch.object(manager, "_unmount_with_umount") as mock_umount,
    ):
        manager._unmount_single_target("/dev/sdd1", "/bin/udisksctl", None, "/bin/umount")
        mock_umount.assert_called_once_with("/bin/umount", "/dev/sdd1")


# --- BurnEngine helpers tests ---


def test_burn_engine_extract_line_and_handlers(qapp, tmp_path):
    # Test _extract_next_line
    line, buf = BurnWorker._extract_next_line("Hello\rWorld")
    assert line == "Hello"
    assert buf == "World"

    line2, buf2 = BurnWorker._extract_next_line("Hello\nWorld")
    assert line2 == "Hello"
    assert buf2 == "World"

    none_line, same_buf = BurnWorker._extract_next_line("NoNewlineHere")
    assert none_line is None
    assert same_buf == "NoNewlineHere"

    iso = WindowsISO(
        file_path=tmp_path / "mock.iso",
        file_name="mock.iso",
        size_bytes=10,
        size_human="10 B",
    )
    target = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=100,
        size_human="100 B",
    )
    config = BurnConfiguration(iso=iso, target_device=target)
    worker = BurnWorker(config, dry_run=True)

    tracker = ProgressTracker(total_bytes=10_000_000)
    pct_pattern = re.compile(r"(\d+)%")

    # Progress lines
    logs = []
    progs = []
    worker.progress_changed.connect(lambda p, s, sp: progs.append((p, s, sp)))
    worker.log_line_emitted.connect(logs.append)

    worker._handle_7z_line("50% 1234 files", pct_pattern, tracker)
    assert len(progs) == 1
    assert "Copiando arquivos: 50%" in progs[0][1]

    worker._handle_7z_line("Arbitrary log message", pct_pattern, tracker)
    assert "Arbitrary log message" in logs

    # Wimlib line
    worker._handle_wimlib_line("75%", pct_pattern, tracker, 10_000_000)
    assert len(progs) == 2
    assert "Dividindo install.wim: 75%" in progs[1][1]
