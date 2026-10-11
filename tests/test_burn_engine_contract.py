"""Contract tests for Burn Engine Qt worker signals and state contract."""

import pytest
from PySide6.QtCore import QCoreApplication

from woeusb_gui_flasher.burn_engine import BurnWorker
from woeusb_gui_flasher.models import (
    BootMode,
    BurnConfiguration,
    FileSystemType,
    StorageDevice,
    WindowsISO,
)


@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_burn_worker_signals_contract(qapp, tmp_path):
    iso_file = tmp_path / "win.iso"
    iso_file.write_bytes(b"test")

    iso = WindowsISO(
        file_path=iso_file,
        file_name="win.iso",
        size_bytes=1000,
        size_human="1 KB",
    )
    device = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
    )
    config = BurnConfiguration(
        iso=iso,
        target_device=device,
        filesystem=FileSystemType.FAT32,
        boot_mode=BootMode.UEFI_AND_LEGACY,
    )

    worker = BurnWorker(config)

    # Validate signal presence
    assert hasattr(worker, "progress_changed")
    assert hasattr(worker, "log_line_emitted")
    assert hasattr(worker, "status_updated")
    assert hasattr(worker, "operation_finished")

    signals_received = []

    def on_progress(percent, stage, speed):
        signals_received.append(("progress", percent, stage, speed))

    def on_log(line):
        signals_received.append(("log", line))

    def on_status(msg, is_warning):
        signals_received.append(("status", msg, is_warning))

    def on_finish(success, msg):
        signals_received.append(("finished", success, msg))

    worker.progress_changed.connect(on_progress)
    worker.log_line_emitted.connect(on_log)
    worker.status_updated.connect(on_status)
    worker.operation_finished.connect(on_finish)

    worker.emit_log("Iniciando gravação de teste...")
    worker.emit_progress(25.0, "Formatando mídia...", "15 MB/s")
    worker.emit_status("Operação em andamento", False)

    assert any(s[0] == "log" and "Iniciando" in s[1] for s in signals_received)
    assert any(s[0] == "progress" and s[1] == 25.0 for s in signals_received)
    assert any(s[0] == "status" and s[1] == "Operação em andamento" for s in signals_received)

