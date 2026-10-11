"""Contract tests for UDisks2 enumeration, invariants, and safety filters."""

from woeusb_gui_flasher.disk_manager import DiskManager
from woeusb_gui_flasher.models import StorageDevice


def test_safety_filter_invariants():
    """Verify that internal, non-USB, and system drives are strictly excluded."""
    manager = DiskManager()

    # Case 1: Internal NVMe drive with root partition
    internal_nvme = StorageDevice(
        name="nvme0n1",
        path="/dev/nvme0n1",
        size_bytes=1_000_000_000_000,
        size_human="931.5 GB",
        is_removable=False,
        is_system_drive=True,
        mount_points=["/", "/boot", "/home"],
    )
    assert manager.filter_safe_device(internal_nvme) is False

    # Case 2: Internal SATA drive
    internal_sata = StorageDevice(
        name="sda",
        path="/dev/sda",
        size_bytes=500_000_000_000,
        size_human="465.7 GB",
        is_removable=False,
        is_system_drive=False,
        mount_points=[],
    )
    assert manager.filter_safe_device(internal_sata) is False

    # Case 3: USB Drive mounted with [SWAP]
    usb_with_swap = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=32_000_000_000,
        size_human="29.8 GB",
        is_removable=True,
        is_system_drive=False,
        mount_points=["[SWAP]"],
    )
    assert manager.filter_safe_device(usb_with_swap) is False

    # Case 4: Valid USB Thumb Drive
    valid_usb = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=32_000_000_000,
        size_human="29.8 GB",
        vendor="Kingston",
        model="DataTraveler",
        is_removable=True,
        is_system_drive=False,
        mount_points=["/run/media/user/USB"],
    )
    assert manager.filter_safe_device(valid_usb) is True


def test_parse_lsblk_json_output():
    """Verify parsing of lsblk output into StorageDevice domain models."""
    sample_lsblk = {
        "blockdevices": [
            {
                "name": "nvme0n1",
                "path": "/dev/nvme0n1",
                "size": 1000204886016,
                "rm": False,
                "tran": "nvme",
                "mountpoints": ["/"],
                "children": [{"name": "nvme0n1p1", "mountpoints": ["/boot/efi"]}],
            },
            {
                "name": "sdd",
                "path": "/dev/sdd",
                "size": 15500000000,
                "rm": True,
                "tran": "usb",
                "vendor": "SanDisk ",
                "model": "Cruzer Blade ",
                "mountpoints": [None],
                "children": [{"name": "sdd1", "mountpoints": ["/run/media/test/USB"]}],
            },
        ]
    }

    manager = DiskManager()
    devices = manager.parse_lsblk_data(sample_lsblk)

    assert len(devices) == 2
    # Only the USB device should be eligible
    eligible = [d for d in devices if manager.filter_safe_device(d)]
    assert len(eligible) == 1
    assert eligible[0].path == "/dev/sdd"
    assert eligible[0].vendor == "SanDisk"
    assert eligible[0].model == "Cruzer Blade"

