"""Main window for WoeUSB GUI Flasher."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from woeusb_gui_flasher.burn_engine import BurnWorker
from woeusb_gui_flasher.disk_manager import DiskManager
from woeusb_gui_flasher.i18n import tr
from woeusb_gui_flasher.models import (
    BurnConfiguration,
    StorageDevice,
    WindowsISO,
)
from woeusb_gui_flasher.ui.components import (
    DriveSelectorCard,
    IsoSelectorCard,
    LogConsoleDrawer,
    OptionsCard,
    ProgressCard,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("ui.main.window_title"))
        self.resize(650, 720)

        self.disk_manager = DiskManager()
        self._current_worker: BurnWorker | None = None
        self._selected_iso: WindowsISO | None = None
        self._selected_drive: StorageDevice | None = None

        self._setup_ui()
        self._refresh_drives()

    def _setup_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        # 1. ISO Selector Card
        self.card_iso = IsoSelectorCard(self)
        self.card_iso.iso_selected.connect(self._on_iso_selected)
        layout.addWidget(self.card_iso)

        # 2. Drive Selector Card
        self.card_drive = DriveSelectorCard(self)
        self.card_drive.drive_selected.connect(self._on_drive_selected)
        self.card_drive.refresh_requested.connect(self._refresh_drives)
        self.card_drive.filter_toggled.connect(self._refresh_drives)
        layout.addWidget(self.card_drive)

        # 3. Format Options Card
        self.card_options = OptionsCard(self)
        layout.addWidget(self.card_options)

        # 4. Progress Card
        self.card_progress = ProgressCard(self)
        layout.addWidget(self.card_progress)

        # Warning for same-disk collision
        self.lbl_collision_warning = QLabel("")
        self.lbl_collision_warning.setStyleSheet(
            """
            QLabel {
                background-color: #fef2f2;
                color: #b91c1c;
                border: 1px solid #f87171;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 500;
                font-size: 12px;
            }
            """
        )
        self.lbl_collision_warning.setWordWrap(True)
        self.lbl_collision_warning.setVisible(False)
        layout.addWidget(self.lbl_collision_warning)

        # Action Buttons
        row_actions = QHBoxLayout()
        self.btn_burn = QPushButton(tr("ui.main.start_burn_button"))
        self.btn_burn.setStyleSheet(
            """
            QPushButton {
                background-color: #0284c7;
                color: white;
                font-weight: bold;
                padding: 10px 24px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
            }
            """
        )
        self.btn_burn.setEnabled(False)
        self.btn_burn.clicked.connect(self._on_burn_clicked)
        row_actions.addWidget(self.btn_burn, stretch=1)

        self.btn_cancel = QPushButton(tr("ui.main.cancel_button"))
        self.btn_cancel.setStyleSheet(
            """
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                padding: 10px 18px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
            }
            """
        )
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        row_actions.addWidget(self.btn_cancel)

        layout.addLayout(row_actions)

        # 5. Log Console Drawer
        self.log_drawer = LogConsoleDrawer(self)
        layout.addWidget(self.log_drawer, stretch=1)

    def _refresh_drives(self) -> None:
        """Refreshes the connected safe USB drives."""
        hide_large = self.card_drive.is_hide_large_drives_active()
        devices = self.disk_manager.get_removable_devices(hide_large_drives=hide_large)
        self.card_drive.populate_devices(devices)

    def _on_iso_selected(self, iso: WindowsISO | None) -> None:
        self._selected_iso = iso
        self._update_burn_button_state()

    def _on_drive_selected(self, drive: StorageDevice | None) -> None:
        self._selected_drive = drive
        self._update_burn_button_state()

    def _update_burn_button_state(self) -> None:
        ready = (
            self._selected_iso is not None
            and self._selected_drive is not None
            and self._current_worker is None
        )
        if ready and self._selected_iso and self._selected_drive:
            collision = self.disk_manager.check_same_disk_collision(
                self._selected_iso.file_path,
                self._selected_drive,
            )
            if collision.has_collision:
                self.btn_burn.setEnabled(False)
                self.lbl_collision_warning.setText(collision.message)
                self.lbl_collision_warning.setVisible(True)
                return

        self.lbl_collision_warning.setVisible(False)
        self.btn_burn.setEnabled(ready)

    def _on_burn_clicked(self) -> None:
        """Handles click on 'Start Burn' with safety confirmation."""
        if not self._selected_iso or not self._selected_drive:
            return

        # Modal Safety Confirmation (NON-NEGOTIABLE)
        dev = self._selected_drive
        msg = tr(
            "ui.main.confirm_format_body",
            path=dev.path,
            vendor=dev.vendor,
            model=dev.model,
            size=dev.size_human,
        )

        reply = QMessageBox.warning(
            self,
            tr("ui.main.confirm_format_title"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Prepare configuration
        config = BurnConfiguration(
            iso=self._selected_iso,
            target_device=self._selected_drive,
            filesystem=self.card_options.get_filesystem(),
            boot_mode=self.card_options.get_boot_mode(),
        )

        # Disable configuration UI during burn
        self.card_iso.setEnabled(False)
        self.card_drive.setEnabled(False)
        self.card_options.setEnabled(False)
        self.btn_burn.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.card_progress.reset()

        # Start worker thread
        self._current_worker = BurnWorker(config)
        self._current_worker.progress_changed.connect(self.card_progress.update_progress)
        self._current_worker.log_line_emitted.connect(self.log_drawer.append_line)
        self._current_worker.operation_finished.connect(self._on_operation_finished)

        self._current_worker.start()

    def _on_cancel_clicked(self) -> None:
        """Handles click on 'Cancel Operation'."""
        if self._current_worker:
            reply = QMessageBox.question(
                self,
                tr("ui.main.confirm_cancel_title"),
                tr("ui.main.confirm_cancel_body"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.btn_cancel.setEnabled(False)
                self._current_worker.request_cancel()

    def _on_operation_finished(self, success: bool, message: str) -> None:
        """Handler called when worker finishes."""
        self._current_worker = None

        # Re-enable configuration UI
        self.card_iso.setEnabled(True)
        self.card_drive.setEnabled(True)
        self.card_options.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self._update_burn_button_state()

        if success:
            QMessageBox.information(
                self,
                tr("ui.main.finished_success_title"),
                tr("ui.main.finished_success_body", message=message),
            )
        else:
            QMessageBox.critical(
                self,
                tr("ui.main.finished_failure_title"),
                tr("ui.main.finished_failure_body", message=message),
            )
