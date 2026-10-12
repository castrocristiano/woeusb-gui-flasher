"""Unit tests for domain models and utility functions."""

import pytest

from woeusb_gui_flasher.models import (
    BootMode,
    BurnConfiguration,
    FileSystemType,
    StorageDevice,
    WindowsISO,
)
from woeusb_gui_flasher.utils import format_bytes


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    assert format_bytes(1024 * 1024 * 1024 * 5) == "5.0 GB"
    assert format_bytes(5_500_000_000) == "5.12 GB"


def test_storage_device_eligibility():
    # Eligible USB thumb drive
    usb_drive = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        vendor="SanDisk",
        model="Ultra",
        is_removable=True,
        is_system_drive=False,
    )
    assert usb_drive.is_eligible_target() is True
    assert "/dev/sdd" in usb_drive.display_name

    # Ineligible: System drive
    sys_drive = StorageDevice(
        name="sda",
        path="/dev/sda",
        size_bytes=500_000_000_000,
        size_human="465.7 GB",
        is_removable=False,
        is_system_drive=True,
        mount_points=["/"],
    )
    assert sys_drive.is_eligible_target() is False

    # Ineligible: Too small (< 2 GB)
    small_drive = StorageDevice(
        name="sde",
        path="/dev/sde",
        size_bytes=1_000_000_000,
        size_human="953.7 MB",
        is_removable=True,
        is_system_drive=False,
    )
    assert small_drive.is_eligible_target() is False


def test_windows_iso_requires_split(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_bytes(b"dummy")

    # WIM <= 4 GB: no split needed
    iso_small = WindowsISO(
        file_path=iso_file,
        file_name="test.iso",
        size_bytes=5_000_000_000,
        size_human="4.65 GB",
        has_install_wim=True,
        install_image_size=3_800_000_000,
    )
    assert iso_small.check_requires_split(FileSystemType.FAT32) is False

    # WIM > 4 GB on FAT32: split required
    iso_large = WindowsISO(
        file_path=iso_file,
        file_name="test.iso",
        size_bytes=6_000_000_000,
        size_human="5.58 GB",
        has_install_wim=True,
        install_image_size=4_800_000_000,
    )
    assert iso_large.check_requires_split(FileSystemType.FAT32) is True
    assert iso_large.check_requires_split(FileSystemType.NTFS) is False


def test_burn_configuration_validation(tmp_path):
    iso_file = tmp_path / "windows.iso"
    iso_file.write_bytes(b"dummy data" * 1000)

    iso = WindowsISO(
        file_path=iso_file,
        file_name="windows.iso",
        size_bytes=10_000,
        size_human="10 KB",
    )
    device = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=8_000_000_000,
        size_human="7.45 GB",
        is_removable=True,
        is_system_drive=False,
    )
    config = BurnConfiguration(
        iso=iso,
        target_device=device,
        filesystem=FileSystemType.FAT32,
        boot_mode=BootMode.UEFI_AND_LEGACY,
    )
    config.validate()  # Should not raise

    # Test error with invalid device
    device.is_system_drive = True
    with pytest.raises(ValueError, match=r"(não é elegível|not eligible)"):
        config.validate()
