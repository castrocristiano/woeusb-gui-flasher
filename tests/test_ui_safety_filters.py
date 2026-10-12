"""UI integration tests for large drive filter checkbox and same-disk warning."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from woeusb_gui_flasher.models import StorageDevice, WindowsISO
from woeusb_gui_flasher.ui.components import DriveSelectorCard
from woeusb_gui_flasher.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_drive_selector_card_has_large_drive_filter(qapp):
    card = DriveSelectorCard()
    assert hasattr(card, "chk_hide_large")
    # Must be checked by default
    assert card.chk_hide_large.isChecked()
    assert card.is_hide_large_drives_active()


def test_drive_selector_card_filter_toggled_signal(qapp):
    card = DriveSelectorCard()
    signals_received = []
    card.filter_toggled.connect(lambda val: signals_received.append(val))

    card.chk_hide_large.setChecked(False)
    assert signals_received == [False]
    assert not card.is_hide_large_drives_active()

    card.chk_hide_large.setChecked(True)
    assert signals_received == [False, True]
    assert card.is_hide_large_drives_active()


def test_main_window_filter_drives(qapp):
    with patch("woeusb_gui_flasher.disk_manager.find_binary", return_value="/bin/lsblk"):
        win = MainWindow()
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
            patch.object(
                win.disk_manager, "_get_devices_via_lsblk", return_value=[dev_16g, dev_1tb]
            ),
            patch.object(win.disk_manager, "_get_devices_via_udisks2", return_value=[]),
        ):
            # When checkbox is checked (default), only 16G appears
            win.card_drive.chk_hide_large.setChecked(True)
            win._refresh_drives()
            assert win.card_drive.combo_drives.count() == 1
            assert "/dev/sdd" in win.card_drive.combo_drives.itemText(0)

            # When checkbox is unchecked, both appear
            win.card_drive.chk_hide_large.setChecked(False)
            assert win.card_drive.combo_drives.count() == 2


def test_main_window_same_disk_collision_shows_warning(qapp, tmp_path):
    with patch("woeusb_gui_flasher.disk_manager.find_binary", return_value="/bin/lsblk"):
        win = MainWindow()
        win.show()
        iso_file = tmp_path / "Win10.iso"
        iso_file.write_text("iso")

        iso = WindowsISO(
            file_path=iso_file,
            file_name="Win10.iso",
            size_bytes=4_000_000_000,
            size_human="4.0 GB",
            is_valid=True,
        )

        drive = StorageDevice(
            name="sdc",
            path="/dev/sdc",
            size_bytes=16_000_000_000,
            size_human="14.9 GB",
            is_removable=True,
        )

        from woeusb_gui_flasher.models import DiskCollisionCheckResult

        # 1. Collision case
        coll_res = DiskCollisionCheckResult(
            has_collision=True,
            source_parent_disk="/dev/sdc",
            target_parent_disk="/dev/sdc",
            message="Aviso: A ISO está no mesmo disco de destino.",
        )
        with patch.object(win.disk_manager, "check_same_disk_collision", return_value=coll_res):
            win._selected_iso = iso
            win._selected_drive = drive
            win._update_burn_button_state()

            assert not win.btn_burn.isEnabled()
            assert win.lbl_collision_warning.isVisible()
            assert "mesmo disco" in win.lbl_collision_warning.text().lower()

        # 2. No collision case
        no_coll_res = DiskCollisionCheckResult(
            has_collision=False,
            message="OK",
        )
        with patch.object(win.disk_manager, "check_same_disk_collision", return_value=no_coll_res):
            win._update_burn_button_state()

            assert win.btn_burn.isEnabled()
            assert not win.lbl_collision_warning.isVisible()


def test_drive_selector_tooltip_and_empty_state(qapp):
    card = DriveSelectorCard()
    assert len(card.chk_hide_large.toolTip()) > 10

    # Test empty state with filter active
    card.chk_hide_large.setChecked(True)
    card.populate_devices([])
    assert any(w in card.combo_drives.itemText(0).lower() for w in ("desmarque", "uncheck"))
