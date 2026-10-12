"""Integration tests for PySide6 UI components and MainWindow."""

from woeusb_gui_flasher.models import StorageDevice
from woeusb_gui_flasher.ui.components import (
    DriveSelectorCard,
    IsoSelectorCard,
    LogConsoleDrawer,
    OptionsCard,
    ProgressCard,
)
from woeusb_gui_flasher.ui.main_window import MainWindow


def test_ui_components_creation(qapp):
    iso_card = IsoSelectorCard()
    assert iso_card.get_iso() is None

    drive_card = DriveSelectorCard()
    devices = [
        StorageDevice(
            name="sdd",
            path="/dev/sdd",
            size_bytes=16_000_000_000,
            size_human="14.9 GB",
            vendor="Kingston",
            is_removable=True,
        )
    ]
    drive_card.populate_devices(devices)
    assert drive_card.get_selected_device() is not None

    options_card = OptionsCard()
    assert options_card.get_filesystem().value == "FAT32"

    progress_card = ProgressCard()
    progress_card.update_progress(50.0, "Extraindo...", "20 MB/s")
    assert progress_card.progress_bar.value() == 50

    log_drawer = LogConsoleDrawer()
    log_drawer.append_line("Teste de log")
    assert "Teste de log" in log_drawer.text_edit.toPlainText()


def test_main_window_creation(qapp):
    window = MainWindow()
    assert window.windowTitle() == "WoeUSB-GUI Flasher"
    assert window.btn_burn.isEnabled() is False
    assert window.btn_cancel.isEnabled() is False
