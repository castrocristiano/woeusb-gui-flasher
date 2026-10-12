"""Unit tests for BurnWorker step logic with mocked subprocess/system calls."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from woeusb_gui_flasher import burn_engine
from woeusb_gui_flasher.burn_engine import BurnWorker, ProgressTracker
from woeusb_gui_flasher.models import (
    BurnConfiguration,
    FileSystemType,
    StorageDevice,
    WindowsISO,
)

GIB = 1024**3


class FakeProcess:
    """Minimal stand-in for subprocess.Popen with streaming stdout."""

    def __init__(self, output: str = "", returncode: int = 0) -> None:
        self.stdout = io.StringIO(output)
        self.returncode = returncode
        self.terminated = False

    def wait(self) -> int:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True


def make_worker(
    tmp_path: Path,
    dry_run: bool = False,
    fs: FileSystemType = FileSystemType.FAT32,
    wim_size: int = 0,
    has_wim: bool = False,
) -> BurnWorker:
    iso_file = tmp_path / "win.iso"
    iso_file.write_bytes(b"iso")
    iso = WindowsISO(
        file_path=iso_file,
        file_name="win.iso",
        size_bytes=10_000_000,
        size_human="10 MB",
        has_install_wim=has_wim,
        install_image_size=wim_size,
    )
    device = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=16_000_000_000,
        size_human="16 GB",
        is_removable=True,
    )
    config = BurnConfiguration(iso=iso, target_device=device, filesystem=fs)
    return BurnWorker(config, dry_run=dry_run)


@pytest.fixture
def temp_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(burn_engine, "TEMP_WIM_DIR", tmp_path / "wimtmp")
    monkeypatch.setattr(burn_engine, "FALLBACK_MOUNT_DIR", tmp_path / "fallback")
    monkeypatch.setattr(burn_engine, "MOCK_MOUNT_DIR", tmp_path / "mock")
    return tmp_path


# --- ProgressTracker ---


def test_progress_tracker_metrics_and_milestones():
    tracker = ProgressTracker(total_bytes=100 * 1024 * 1024)
    transferred, speed, eta = tracker.compute_metrics(50.0)
    assert transferred == 50 * 1024 * 1024
    assert speed > 0
    assert ":" in eta

    _, _, eta_zero = tracker.compute_metrics(0.0)
    assert eta_zero == "--:--"

    assert tracker.is_log_milestone(50.0) is True
    assert tracker.is_log_milestone(50.0) is False


# --- Cancellation / lifecycle ---


def test_request_cancel_terminates_active_process(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=True)
    proc = MagicMock()
    worker._active_process = proc
    worker.request_cancel()
    assert worker.is_cancelled() is True
    proc.terminate.assert_called_once()


def test_request_cancel_handles_terminate_error(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=True)
    proc = MagicMock()
    proc.terminate.side_effect = OSError("boom")
    worker._active_process = proc
    worker.request_cancel()
    assert worker.is_cancelled() is True


def test_run_reports_failure_on_exception(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=True)
    results = []
    worker.operation_finished.connect(lambda ok, msg: results.append((ok, msg)))
    with patch.object(worker.config, "validate", side_effect=ValueError("invalid")):
        worker.run()
    assert results == [(False, "invalid")]


@pytest.mark.parametrize(
    "step",
    [
        "_step_validate",
        "_step_unmount",
        "_step_extract",
        "_step_wim_split",
        "_step_bootloader",
    ],
)
def test_steps_finish_cancelled_when_abort_requested(qapp, tmp_path, temp_dirs, step):
    worker = make_worker(tmp_path, dry_run=True)
    results = []
    worker.operation_finished.connect(lambda ok, msg: results.append((ok, msg)))
    worker._abort_requested = True

    method = getattr(worker, step)
    with (
        patch.object(worker.config, "validate"),
        patch.object(worker, "_extract_iso_contents"),
        patch.object(worker, "_handle_wim_split"),
        patch.object(worker, "_configure_bootloader"),
    ):
        outcome = method(tmp_path) if step not in ("_step_validate", "_step_unmount") else method()

    assert outcome is False
    assert len(results) == 1
    assert results[0][0] is False


def test_run_stops_when_cancelled_after_format(qapp, tmp_path, temp_dirs):
    worker = make_worker(tmp_path, dry_run=True)
    results = []
    worker.operation_finished.connect(lambda ok, msg: results.append((ok, msg)))

    def fake_format():
        worker._abort_requested = True
        return tmp_path

    with (
        patch.object(worker.config, "validate"),
        patch.object(worker, "_step_format", side_effect=fake_format),
    ):
        worker.run()
    assert len(results) == 1
    assert results[0][0] is False


def test_finish_cancelled_cleans_mount(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=False)
    worker._temp_mount_dir = tmp_path / "mnt"
    with patch.object(worker, "_cleanup_mount") as cleanup:
        worker._finish_cancelled()
    cleanup.assert_called_once_with(tmp_path / "mnt")


def test_finish_cancelled_ignores_cleanup_errors(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=False)
    worker._temp_mount_dir = tmp_path / "mnt"
    with patch.object(worker, "_cleanup_mount", side_effect=OSError("busy")):
        worker._finish_cancelled()


def test_step_finalize_real_mode_syncs_and_cleans(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=False)
    results = []
    worker.operation_finished.connect(lambda ok, msg: results.append((ok, msg)))
    with (
        patch.object(burn_engine.subprocess, "run") as run,
        patch.object(worker, "_cleanup_mount") as cleanup,
    ):
        worker._step_finalize(tmp_path)
    run.assert_called_once()
    cleanup.assert_called_once_with(tmp_path)
    assert results[0][0] is True


def test_step_unmount_real_mode(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=False)
    with patch.object(worker.disk_manager, "unmount_device_partitions") as unmount:
        assert worker._step_unmount() is True
    unmount.assert_called_once()


# --- Formatting ---


def test_prepare_and_format_drive_real(qapp, tmp_path):
    worker = make_worker(tmp_path)
    with (
        patch.object(worker, "_format_partition") as fmt,
        patch.object(worker, "_mount_partition", return_value=tmp_path) as mount,
    ):
        result = worker._prepare_and_format_drive()
    assert result == tmp_path
    assert worker._target_part == "/dev/sdd1"
    fmt.assert_called_once()
    mount.assert_called_once_with("/dev/sdd1")


def test_format_partition_prefers_udisksctl(qapp, tmp_path):
    worker = make_worker(tmp_path)
    with (
        patch.object(burn_engine, "find_binary", return_value="/bin/x"),
        patch.object(worker, "_format_via_udisksctl", return_value=True) as ud,
        patch.object(worker, "_format_via_gdbus") as gd,
    ):
        worker._format_partition("/dev/sdd1", FileSystemType.FAT32, "LBL")
    ud.assert_called_once_with("/dev/sdd1", "vfat", "LBL")
    gd.assert_not_called()


def test_format_partition_falls_back_to_gdbus_then_mkfs(qapp, tmp_path):
    worker = make_worker(tmp_path)
    with (
        patch.object(burn_engine, "find_binary", return_value="/bin/x"),
        patch.object(worker, "_format_via_udisksctl", return_value=False),
        patch.object(worker, "_format_via_gdbus", return_value=True) as gd,
    ):
        worker._format_partition("/dev/sdd1", FileSystemType.NTFS, "LBL")
    gd.assert_called_once_with("/dev/sdd1", "ntfs", "LBL")

    with (
        patch.object(burn_engine, "find_binary", return_value=None),
        patch.object(worker, "_format_via_mkfs_fallback") as mkfs,
    ):
        worker._format_partition("/dev/sdd1", FileSystemType.FAT32, "LBL")
    mkfs.assert_called_once()


def test_format_via_udisksctl_and_gdbus(qapp, tmp_path):
    worker = make_worker(tmp_path)
    ok = MagicMock(returncode=0, stdout="done", stderr="")
    bad = MagicMock(returncode=1, stdout="", stderr="err")
    with patch.object(burn_engine.subprocess, "run", return_value=ok):
        assert worker._format_via_udisksctl("/dev/sdd1", "vfat", "L") is True
        assert worker._format_via_gdbus("/dev/sdd1", "vfat", "L") is True
    with patch.object(burn_engine.subprocess, "run", return_value=bad):
        assert worker._format_via_udisksctl("/dev/sdd1", "vfat", "L") is False
        assert worker._format_via_gdbus("/dev/sdd1", "vfat", "L") is False


def test_format_via_mkfs_fallback(qapp, tmp_path):
    worker = make_worker(tmp_path)
    ok = MagicMock(returncode=0, stdout="", stderr="")
    with patch.object(burn_engine.subprocess, "run", return_value=ok) as run:
        worker._format_via_mkfs_fallback("/dev/sdd1", FileSystemType.FAT32, "L")
        assert run.call_args[0][0][0] == "mkfs.vfat"
        worker._format_via_mkfs_fallback("/dev/sdd1", FileSystemType.NTFS, "L")
        assert run.call_args[0][0][0] == "mkfs.ntfs"

    bad = MagicMock(returncode=1, stdout="", stderr="fail")
    with (
        patch.object(burn_engine.subprocess, "run", return_value=bad),
        pytest.raises(RuntimeError),
    ):
        worker._format_via_mkfs_fallback("/dev/sdd1", FileSystemType.FAT32, "L")


# --- Mounting ---


def test_mount_via_udisksctl_parses_path(qapp, tmp_path):
    worker = make_worker(tmp_path)
    res = MagicMock(returncode=0, stdout="Mounted /dev/sdd1 at /run/media/u/WIN.")
    with patch.object(burn_engine.subprocess, "run", return_value=res):
        assert worker._mount_via_udisksctl("/dev/sdd1") == Path("/run/media/u/WIN.")
    res_bad = MagicMock(returncode=1, stdout="")
    with patch.object(burn_engine.subprocess, "run", return_value=res_bad):
        assert worker._mount_via_udisksctl("/dev/sdd1") is None


def test_mount_via_gdbus_parses_path(qapp, tmp_path):
    worker = make_worker(tmp_path)
    res = MagicMock(returncode=0, stdout="('/run/media/u/WIN',)")
    with patch.object(burn_engine.subprocess, "run", return_value=res):
        assert worker._mount_via_gdbus("/dev/sdd1") == Path("/run/media/u/WIN")
    res_bad = MagicMock(returncode=1, stdout="")
    with patch.object(burn_engine.subprocess, "run", return_value=res_bad):
        assert worker._mount_via_gdbus("/dev/sdd1") is None


def test_mount_partition_strategies(qapp, tmp_path, temp_dirs):
    worker = make_worker(tmp_path)
    with (
        patch.object(burn_engine, "find_binary", return_value="/bin/x"),
        patch.object(worker, "_mount_via_udisksctl", return_value=Path("/a")),
    ):
        assert worker._mount_partition("/dev/sdd1") == Path("/a")

    with (
        patch.object(burn_engine, "find_binary", return_value="/bin/x"),
        patch.object(worker, "_mount_via_udisksctl", return_value=None),
        patch.object(worker, "_mount_via_gdbus", return_value=Path("/b")),
    ):
        assert worker._mount_partition("/dev/sdd1") == Path("/b")

    with (
        patch.object(burn_engine, "find_binary", return_value=None),
        patch.object(burn_engine.subprocess, "run") as run,
    ):
        result = worker._mount_partition("/dev/sdd1")
    assert result == tmp_path / "fallback"
    assert result.is_dir()
    run.assert_called_once()


# --- Extraction ---


def test_build_7z_extract_cmd_excludes_big_wim(qapp, tmp_path):
    worker = make_worker(tmp_path, wim_size=5 * GIB, has_wim=True)
    cmd = worker._build_7z_extract_cmd("7z", tmp_path, "x.iso")
    assert "-xr!install.wim" in cmd
    assert "-xr!install.esd" in cmd

    small = make_worker(tmp_path, wim_size=GIB, has_wim=True)
    assert "-xr!install.wim" not in small._build_7z_extract_cmd("7z", tmp_path, "x.iso")


def test_extract_iso_requires_7z(qapp, tmp_path):
    worker = make_worker(tmp_path)
    with (
        patch.object(burn_engine, "find_binary", return_value=None),
        pytest.raises(FileNotFoundError),
    ):
        worker._extract_iso_contents(tmp_path)


def test_extract_iso_dry_run_creates_files(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=True)
    with patch.object(burn_engine, "find_binary", return_value=None):
        worker._extract_iso_contents(tmp_path)
    assert (tmp_path / "sources" / "install.wim").is_file()
    assert (tmp_path / "efi" / "boot" / "bootx64.efi").is_file()


def test_extract_iso_streams_progress(qapp, tmp_path):
    worker = make_worker(tmp_path)
    progress = []
    worker.progress_changed.connect(lambda p, s, sp: progress.append(p))
    proc = FakeProcess("10%\n50%\nextracting\n100%\n")
    with (
        patch.object(burn_engine, "find_binary", return_value="/usr/bin/7z"),
        patch.object(worker, "_spawn_streaming_process", return_value=proc),
    ):
        worker._extract_iso_contents(tmp_path)
    assert progress
    assert worker._active_process is None


def test_extract_iso_failure_raises(qapp, tmp_path):
    worker = make_worker(tmp_path)
    proc = FakeProcess("", returncode=2)
    with (
        patch.object(burn_engine, "find_binary", return_value="/usr/bin/7z"),
        patch.object(worker, "_spawn_streaming_process", return_value=proc),
        pytest.raises(RuntimeError),
    ):
        worker._extract_iso_contents(tmp_path)


def test_spawn_streaming_process_uses_popen(qapp, tmp_path):
    worker = make_worker(tmp_path)
    with patch.object(burn_engine.subprocess, "Popen") as popen:
        worker._spawn_streaming_process(["echo", "hi"])
    popen.assert_called_once()


def test_stream_output_chunks_cancel_terminates(qapp, tmp_path):
    worker = make_worker(tmp_path)
    worker._abort_requested = True
    proc = FakeProcess("line\n")
    handled: list[str] = []
    worker._stream_output_chunks(proc, handled.append)  # type: ignore[arg-type]
    assert proc.terminated is True
    assert handled == []

    no_stdout = MagicMock(stdout=None)
    worker._stream_output_chunks(no_stdout, handled.append)


# --- WIM split ---


def test_check_wim_split_needed(qapp, tmp_path):
    worker = make_worker(tmp_path, wim_size=GIB)
    sources = tmp_path / "sources"
    sources.mkdir()
    should, _, _ = worker._check_wim_split_needed(sources)
    assert should is False

    big = make_worker(tmp_path, wim_size=5 * GIB)
    should, _, _ = big._check_wim_split_needed(sources)
    assert should is True

    (sources / "install.wim").write_bytes(b"x" * 10)
    should, size, existing = worker._check_wim_split_needed(sources)
    assert should is True
    assert size == 10
    assert existing.is_file()


def test_handle_wim_split_skipped_when_small(qapp, tmp_path):
    worker = make_worker(tmp_path, wim_size=GIB)
    worker._handle_wim_split(tmp_path)
    assert not (tmp_path / "sources" / "install.swm").exists()


def test_handle_wim_split_dry_run(qapp, tmp_path):
    worker = make_worker(tmp_path, dry_run=True, wim_size=5 * GIB)
    with patch.object(burn_engine, "find_binary", return_value=None):
        worker._handle_wim_split(tmp_path)
    assert (tmp_path / "sources" / "install.swm").is_file()
    assert (tmp_path / "sources" / "install2.swm").is_file()


def test_handle_wim_split_requires_wimlib(qapp, tmp_path):
    worker = make_worker(tmp_path, wim_size=5 * GIB)
    with (
        patch.object(burn_engine, "find_binary", return_value=None),
        pytest.raises(FileNotFoundError),
    ):
        worker._handle_wim_split(tmp_path)


def test_handle_wim_split_existing_wim_is_removed(qapp, tmp_path, temp_dirs):
    worker = make_worker(tmp_path, wim_size=5 * GIB)
    sources = tmp_path / "target" / "sources"
    sources.mkdir(parents=True)
    existing = sources / "install.wim"
    existing.write_bytes(b"wim")
    with (
        patch.object(burn_engine, "find_binary", return_value="/bin/tool"),
        patch.object(worker, "_execute_wimlib_split") as split,
    ):
        worker._handle_wim_split(tmp_path / "target")
    split.assert_called_once()
    assert not existing.exists()


def test_handle_wim_split_extracts_wim_to_temp(qapp, tmp_path, temp_dirs):
    worker = make_worker(tmp_path, wim_size=5 * GIB)
    target = tmp_path / "target"
    target.mkdir()
    with (
        patch.object(burn_engine, "find_binary", return_value="/bin/tool"),
        patch.object(worker, "_extract_wim_to_temp_storage") as extract,
        patch.object(worker, "_execute_wimlib_split") as split,
    ):
        worker._handle_wim_split(target)
    extract.assert_called_once()
    split.assert_called_once()


def test_extract_wim_to_temp_storage(qapp, tmp_path, temp_dirs):
    worker = make_worker(tmp_path)
    proc = FakeProcess("50%\n")
    with patch.object(worker, "_spawn_streaming_process", return_value=proc):
        worker._extract_wim_to_temp_storage("7z", tmp_path / "w.wim", GIB)

    bad = FakeProcess("", returncode=1)
    with (
        patch.object(worker, "_spawn_streaming_process", return_value=bad),
        pytest.raises(RuntimeError),
    ):
        worker._extract_wim_to_temp_storage("7z", tmp_path / "w.wim", GIB)

    worker._abort_requested = True
    with patch.object(worker, "_spawn_streaming_process", return_value=FakeProcess("", 1)):
        worker._extract_wim_to_temp_storage("7z", tmp_path / "w.wim", GIB)


def test_execute_wimlib_split(qapp, tmp_path):
    worker = make_worker(tmp_path)
    progress = []
    worker.progress_changed.connect(lambda p, s, sp: progress.append(s))
    proc = FakeProcess("25%\nsplitting\n")
    with patch.object(worker, "_spawn_streaming_process", return_value=proc):
        worker._execute_wimlib_split("wimlib", tmp_path / "a.wim", tmp_path / "a.swm", GIB)
    assert progress

    bad = FakeProcess("", returncode=3)
    with (
        patch.object(worker, "_spawn_streaming_process", return_value=bad),
        pytest.raises(RuntimeError),
    ):
        worker._execute_wimlib_split("wimlib", tmp_path / "a.wim", tmp_path / "a.swm", GIB)

    worker._abort_requested = True
    with patch.object(worker, "_spawn_streaming_process", return_value=FakeProcess("", 1)):
        worker._execute_wimlib_split("wimlib", tmp_path / "a.wim", tmp_path / "a.swm", GIB)


# --- Bootloader ---


def test_configure_bootloader_variants(qapp, tmp_path):
    worker = make_worker(tmp_path)
    logs = []
    worker.log_line_emitted.connect(logs.append)

    # Missing everything -> warning
    worker._configure_bootloader(tmp_path)
    assert any(("Aviso" in line or "Warning" in line) for line in logs)

    # Fallback bootmgfw copy
    loader = tmp_path / "efi" / "microsoft" / "boot" / "bootmgfw.efi"
    loader.parent.mkdir(parents=True)
    loader.write_bytes(b"efi")
    worker._configure_bootloader(tmp_path)
    assert (tmp_path / "efi" / "boot" / "bootx64.efi").is_file()

    # Already present
    logs.clear()
    worker._configure_bootloader(tmp_path)
    assert any(("verificado" in line or "verified" in line) for line in logs)


# --- Cleanup ---


def test_cleanup_mount_strategies(qapp, tmp_path):
    worker = make_worker(tmp_path)
    with (
        patch.object(burn_engine, "find_binary", return_value="/bin/udisksctl"),
        patch.object(burn_engine.subprocess, "run") as run,
    ):
        worker._cleanup_mount(tmp_path)
    assert run.call_args[0][0][0] == "udisksctl"

    worker._target_part = "/dev/sdd1"
    with (
        patch.object(
            burn_engine, "find_binary", side_effect=lambda n: "/bin/gdbus" if n == "gdbus" else None
        ),
        patch.object(burn_engine.subprocess, "run") as run,
    ):
        worker._cleanup_mount(tmp_path)
    assert run.call_args[0][0][0] == "gdbus"

    with (
        patch.object(burn_engine, "find_binary", return_value=None),
        patch.object(burn_engine.subprocess, "run") as run,
    ):
        worker._cleanup_mount(tmp_path)
    assert run.call_args[0][0][0] == "umount"
