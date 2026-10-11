"""Unit tests for DiskManager and unmounting logic."""

from unittest.mock import patch

from woeusb_gui_flasher.disk_manager import DiskManager
from woeusb_gui_flasher.models import StorageDevice


def test_get_removable_devices_mocked():
    sample_lsblk = {
        "blockdevices": [
            {
                "name": "sda",
                "path": "/dev/sda",
                "size": 500000000000,
                "rm": False,
                "tran": "sata",
                "mountpoints": ["/"],
            },
            {
                "name": "sdb",
                "path": "/dev/sdb",
                "size": 32000000000,
                "rm": True,
                "tran": "usb",
                "vendor": "Kingston",
                "model": "DataTraveler",
                "mountpoints": [None],
                "children": [
                    {"name": "sdb1", "path": "/dev/sdb1", "mountpoints": ["/run/media/user/USB"]}
                ],
            },
        ]
    }

    manager = DiskManager()
    with (
        patch.object(
            manager, "_get_devices_via_lsblk", return_value=manager.parse_lsblk_data(sample_lsblk)
        ),
        patch.object(manager, "_get_devices_via_udisks2", return_value=[]),
    ):
        devices = manager.get_removable_devices()
        assert len(devices) == 1
        assert devices[0].path == "/dev/sdb"
        assert devices[0].is_eligible_target() is True


def test_unmount_device_partitions():
    device = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
        partitions=["/dev/sdd1"],
    )
    manager = DiskManager()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        success = manager.unmount_device_partitions(device)
        assert success is True
        assert mock_run.called
