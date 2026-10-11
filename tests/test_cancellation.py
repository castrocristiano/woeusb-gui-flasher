"""Unit and integration tests for cancellation and error recovery in BurnWorker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from woeusb_gui_flasher.burn_engine import BurnWorker
from woeusb_gui_flasher.models import (
    BootMode,
    BurnConfiguration,
    FileSystemType,
    StorageDevice,
    WindowsISO,
)


def test_burn_worker_cancel_before_run(qapp, tmp_path):
    iso_file = tmp_path / "mock.iso"
    iso_file.write_bytes(b"content")

    iso = WindowsISO(
        file_path=iso_file,
        file_name="mock.iso",
        size_bytes=5 * 1024 * 1024 * 1024,
        size_human="5.0 GB",
        has_install_wim=True,
        has_install_esd=False,
        install_image_size=4_500_000_000,
    )
    dev = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        vendor="Kingston",
        model="DataTraveler",
        size_bytes=16 * 1024 * 1024 * 1024,
        size_human="14.9 GB",
        is_removable=True,
        is_system_drive=False,
    )
    config = BurnConfiguration(
        iso=iso,
        target_device=dev,
        filesystem=FileSystemType.FAT32,
        boot_mode=BootMode.UEFI_AND_LEGACY,
    )

    worker = BurnWorker(config, dry_run=True)
    worker.request_cancel()
    assert worker.is_cancelled() is True

    finished_results = []
    worker.operation_finished.connect(lambda ok, msg: finished_results.append((ok, msg)))

    worker.run()
    assert len(finished_results) == 1
    success, message = finished_results[0]
    assert success is False
    assert "cancelada" in message.lower()


def test_burn_worker_cancels_active_process(qapp, tmp_path):
    iso_file = tmp_path / "mock.iso"
    iso_file.write_bytes(b"content")

    iso = WindowsISO(
        file_path=iso_file,
        file_name="mock.iso",
        size_bytes=5 * 1024 * 1024 * 1024,
        size_human="5.0 GB",
        has_install_wim=True,
        has_install_esd=False,
        install_image_size=4_500_000_000,
    )
    dev = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        vendor="Kingston",
        model="DataTraveler",
        size_bytes=16 * 1024 * 1024 * 1024,
        size_human="14.9 GB",
        is_removable=True,
        is_system_drive=False,
    )
    config = BurnConfiguration(
        iso=iso,
        target_device=dev,
        filesystem=FileSystemType.FAT32,
        boot_mode=BootMode.UEFI_AND_LEGACY,
    )

    worker = BurnWorker(config, dry_run=False)
    mock_process = MagicMock()
    worker._active_process = mock_process

    worker.request_cancel()
    mock_process.terminate.assert_called_once()
    assert worker.is_cancelled() is True


def test_burn_worker_cleans_up_mount_on_cancel(qapp, tmp_path):
    iso_file = tmp_path / "mock.iso"
    iso_file.write_bytes(b"content")

    iso = WindowsISO(
        file_path=iso_file,
        file_name="mock.iso",
        size_bytes=5 * 1024 * 1024 * 1024,
        size_human="5.0 GB",
        has_install_wim=True,
        has_install_esd=False,
        install_image_size=4_500_000_000,
    )
    dev = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        vendor="Kingston",
        model="DataTraveler",
        size_bytes=16 * 1024 * 1024 * 1024,
        size_human="14.9 GB",
        is_removable=True,
        is_system_drive=False,
    )
    config = BurnConfiguration(
        iso=iso,
        target_device=dev,
        filesystem=FileSystemType.FAT32,
        boot_mode=BootMode.UEFI_AND_LEGACY,
    )

    worker = BurnWorker(config, dry_run=False)
    worker._temp_mount_dir = Path("/run/media/mock_mount")

    with patch.object(worker, "_cleanup_mount") as mock_cleanup:
        worker.request_cancel()
        worker._finish_cancelled()
        mock_cleanup.assert_called_once_with(Path("/run/media/mock_mount"))
