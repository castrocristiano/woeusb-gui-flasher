"""Unit tests for BurnWorker execution flow and subprocess coordination."""

from woeusb_gui_flasher.burn_engine import BurnWorker
from woeusb_gui_flasher.models import (
    BootMode,
    BurnConfiguration,
    FileSystemType,
    StorageDevice,
    WindowsISO,
)


def test_burn_worker_dry_run_execution(qapp, tmp_path):
    iso_file = tmp_path / "mock.iso"
    iso_file.write_bytes(b"mock iso content" * 100)

    iso = WindowsISO(
        file_path=iso_file,
        file_name="mock.iso",
        size_bytes=1000,
        size_human="1 KB",
        has_install_wim=True,
        install_image_size=5_000_000_000,  # triggers split logic
    )
    device = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
        is_system_drive=False,
    )
    config = BurnConfiguration(
        iso=iso,
        target_device=device,
        filesystem=FileSystemType.FAT32,
        boot_mode=BootMode.UEFI_AND_LEGACY,
    )

    worker = BurnWorker(config, dry_run=True)

    results = []
    worker.operation_finished.connect(lambda success, msg: results.append((success, msg)))

    # Execute directly in-thread for deterministic testing
    worker.run()

    assert len(results) == 1
    success, msg = results[0]
    assert success is True
    assert any(w in msg.lower() for w in ("sucesso", "successfully"))


def test_burn_worker_cancellation(qapp, tmp_path):
    iso_file = tmp_path / "mock.iso"
    iso_file.write_bytes(b"content")

    iso = WindowsISO(
        file_path=iso_file,
        file_name="mock.iso",
        size_bytes=100,
        size_human="100 B",
    )
    device = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=8_000_000_000,
        size_human="7.45 GB",
        is_removable=True,
    )
    config = BurnConfiguration(iso=iso, target_device=device)

    worker = BurnWorker(config, dry_run=True)
    worker.request_cancel()
    assert worker.is_cancelled() is True

    results = []
    worker.operation_finished.connect(lambda success, msg: results.append((success, msg)))
    worker.run()

    assert len(results) == 1
    success, msg = results[0]
    assert success is False
    assert any(w in msg.lower() for w in ("cancelada", "cancelled"))


def test_progress_tracker_metrics():
    from woeusb_gui_flasher.burn_engine import ProgressTracker

    total = 5_000_000_000  # 5 GB
    tracker = ProgressTracker(total_bytes=total)

    # 50%
    transferred, speed_mb, eta_str = tracker.compute_metrics(50.0)
    assert transferred == 2_500_000_000
    assert speed_mb > 0
    assert ":" in eta_str

    # 0%
    transferred_0, _, _ = tracker.compute_metrics(0.0)
    assert transferred_0 == 0

    # Milestone checking
    assert tracker.is_log_milestone(10.0)
    assert not tracker.is_log_milestone(11.0)
    assert tracker.is_log_milestone(20.0)
