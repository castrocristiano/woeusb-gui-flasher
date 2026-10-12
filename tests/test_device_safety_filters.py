"""Unit and contract tests for large drive filtering and same-disk collision prevention."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from woeusb_gui_flasher.disk_manager import DiskManager
from woeusb_gui_flasher.models import (
    BurnConfiguration,
    DiskCollisionCheckResult,
    StorageDevice,
    WindowsISO,
)


def test_storage_device_is_large_drive():
    # 16 GB pendrive -> not large
    dev_16g = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
    )
    assert not dev_16g.is_large_drive
    assert dev_16g.is_eligible_target(hide_large_drives=True)
    assert dev_16g.is_eligible_target(hide_large_drives=False)

    # 64 GB commercial pendrive (64 GiB limit) -> not large
    dev_64g = StorageDevice(
        name="sde",
        path="/dev/sde",
        size_bytes=64_000_000_000,
        size_human="59.6 GB",
        is_removable=True,
    )
    assert not dev_64g.is_large_drive
    assert dev_64g.is_eligible_target(hide_large_drives=True)

    # 1 TB external USB HDD -> large drive
    dev_1tb = StorageDevice(
        name="sdc",
        path="/dev/sdc",
        size_bytes=1_000_000_000_000,
        size_human="931.5 GB",
        is_removable=True,
    )
    assert dev_1tb.is_large_drive
    # When hiding large drives, should NOT be eligible
    assert not dev_1tb.is_eligible_target(hide_large_drives=True)
    # When NOT hiding large drives, SHOULD be eligible
    assert dev_1tb.is_eligible_target(hide_large_drives=False)


def test_disk_manager_filter_safe_device_with_hide_large():
    dm = DiskManager()
    dev_16g = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
    )
    dev_1tb = StorageDevice(
        name="sdc",
        path="/dev/sdc",
        size_bytes=1_000_000_000_000,
        size_human="931.5 GB",
        is_removable=True,
    )

    assert dm.filter_safe_device(dev_16g, hide_large_drives=True)
    assert not dm.filter_safe_device(dev_1tb, hide_large_drives=True)
    assert dm.filter_safe_device(dev_1tb, hide_large_drives=False)


def test_disk_manager_get_removable_devices_filters_large():
    dm = DiskManager()
    dev_16g = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
    )
    dev_1tb = StorageDevice(
        name="sdc",
        path="/dev/sdc",
        size_bytes=1_000_000_000_000,
        size_human="931.5 GB",
        is_removable=True,
    )

    with (
        patch.object(dm, "_get_devices_via_lsblk", return_value=[dev_16g, dev_1tb]),
        patch.object(dm, "_get_devices_via_udisks2", return_value=[]),
    ):
        # Default hide_large_drives=True
        filtered = dm.get_removable_devices(hide_large_drives=True)
        assert len(filtered) == 1
        assert filtered[0].path == "/dev/sdd"

        # When hide_large_drives=False
        all_devs = dm.get_removable_devices(hide_large_drives=False)
        assert len(all_devs) == 2
        assert {d.path for d in all_devs} == {"/dev/sdd", "/dev/sdc"}


def test_get_parent_disk_name():
    assert DiskManager.get_parent_disk_name("/dev/sdd1") == "/dev/sdd"
    assert DiskManager.get_parent_disk_name("/dev/sdd") == "/dev/sdd"
    assert DiskManager.get_parent_disk_name("sdd1") == "/dev/sdd"
    assert DiskManager.get_parent_disk_name("/dev/sdc2") == "/dev/sdc"
    assert DiskManager.get_parent_disk_name("/dev/nvme0n1p2") == "/dev/nvme0n1"
    assert DiskManager.get_parent_disk_name("/dev/nvme0n1") == "/dev/nvme0n1"
    assert DiskManager.get_parent_disk_name("/dev/mmcblk0p1") == "/dev/mmcblk0"
    assert DiskManager.get_parent_disk_name("") == ""


def test_resolve_file_source_block_device(tmp_path):
    dm = DiskManager()
    test_file = tmp_path / "test.iso"
    test_file.write_text("dummy")

    fake_mountinfo = (
        "36 29 8:34 / /run/media/cristiano/Dados rw,nosuid,nodev shared:23 - ext4 /dev/sdc2 rw\n"
        "37 29 0:45 / /tmp rw,nosuid,nodev shared:24 - tmpfs tmpfs rw\n"
    )

    with patch.object(Path, "read_text", return_value=fake_mountinfo):
        fake_stat = MagicMock()
        fake_stat.st_dev = (8 << 8) | 34  # major=8, minor=34
        with patch.object(Path, "stat", return_value=fake_stat):
            block_dev = dm.resolve_file_source_block_device(test_file)
            assert block_dev == "/dev/sdc2"


def test_check_same_disk_collision():
    dm = DiskManager()
    target_dev = StorageDevice(
        name="sdc",
        path="/dev/sdc",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
    )

    # Collision: ISO on /dev/sdc2, target is /dev/sdc
    with patch.object(dm, "resolve_file_source_block_device", return_value="/dev/sdc2"):
        res = dm.check_same_disk_collision(Path("/run/media/test.iso"), target_dev)
        assert res.has_collision
        assert res.source_parent_disk == "/dev/sdc"
        assert res.target_parent_disk == "/dev/sdc"
        assert any(w in res.message.lower() for w in ("mesmo disco", "same physical disk"))

    # No collision: ISO on /dev/nvme0n1p2, target is /dev/sdc
    with patch.object(dm, "resolve_file_source_block_device", return_value="/dev/nvme0n1p2"):
        res = dm.check_same_disk_collision(Path("/home/test.iso"), target_dev)
        assert not res.has_collision

    # No block dev (e.g. tmpfs)
    with patch.object(dm, "resolve_file_source_block_device", return_value=None):
        res = dm.check_same_disk_collision(Path("/tmp/test.iso"), target_dev)
        assert not res.has_collision


def test_burn_configuration_same_disk_validation(tmp_path):
    iso_file = tmp_path / "Win10.iso"
    iso_file.write_text("iso content")

    iso = WindowsISO(
        file_path=iso_file,
        file_name="Win10.iso",
        size_bytes=4_000_000_000,
        size_human="4.0 GB",
        is_valid=True,
    )

    target_dev = StorageDevice(
        name="sdc",
        path="/dev/sdc",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
    )

    config = BurnConfiguration(
        iso=iso,
        target_device=target_dev,
    )

    collision_res = DiskCollisionCheckResult(
        has_collision=True,
        source_parent_disk="/dev/sdc",
        target_parent_disk="/dev/sdc",
        message="A ISO de origem está no mesmo disco físico do destino.",
    )

    with (
        patch(
            "woeusb_gui_flasher.disk_manager.DiskManager.check_same_disk_collision",
            return_value=collision_res,
        ),
        pytest.raises(ValueError, match="mesmo disco"),
    ):
        config.validate()


def test_burn_worker_aborts_on_same_disk_collision(tmp_path):
    from woeusb_gui_flasher.burn_engine import BurnWorker

    iso_file = tmp_path / "Win10.iso"
    iso_file.write_text("iso content")

    iso = WindowsISO(
        file_path=iso_file,
        file_name="Win10.iso",
        size_bytes=4_000_000_000,
        size_human="4.0 GB",
        is_valid=True,
    )

    target_dev = StorageDevice(
        name="sdc",
        path="/dev/sdc",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
    )

    config = BurnConfiguration(iso=iso, target_device=target_dev)
    worker = BurnWorker(config)

    finish_signals = []
    worker.operation_finished.connect(lambda success, msg: finish_signals.append((success, msg)))

    collision_res = DiskCollisionCheckResult(
        has_collision=True,
        source_parent_disk="/dev/sdc",
        target_parent_disk="/dev/sdc",
        message="A ISO de origem está no mesmo disco físico do destino.",
    )

    with (
        patch(
            "woeusb_gui_flasher.disk_manager.DiskManager.check_same_disk_collision",
            return_value=collision_res,
        ),
        patch.object(worker.disk_manager, "unmount_device_partitions") as mock_unmount,
    ):
        # unmount_device_partitions MUST NOT be called if validation fails
        worker.run()
        mock_unmount.assert_not_called()

    assert len(finish_signals) == 1
    success, msg = finish_signals[0]
    assert not success
    assert "mesmo disco" in msg.lower()
