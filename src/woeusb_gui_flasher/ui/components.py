"""Reusable UI widgets for WoeUSB GUI Flasher."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from woeusb_gui_flasher.models import BootMode, FileSystemType, StorageDevice, WindowsISO
from woeusb_gui_flasher.utils import inspect_iso_file


class CardFrame(QFrame):
    """Clean framed container with subtle border."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            CardFrame {
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 8px;
                padding: 12px;
                background-color: palette(window);
            }
            """
        )


class IsoSelectorCard(CardFrame):
    """Component to browse and display selected Windows ISO."""

    iso_selected = Signal(object)  # WindowsISO

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_iso: WindowsISO | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("<b>1. Imagem de Instalação do Windows (ISO)</b>")
        layout.addWidget(title)

        row = QHBoxLayout()
        self.lbl_path = QLabel("Nenhum arquivo ISO selecionado...")
        self.lbl_path.setStyleSheet("color: gray;")
        row.addWidget(self.lbl_path, stretch=1)

        btn_browse = QPushButton("Procurar...")
        btn_browse.clicked.connect(self._on_browse_clicked)
        row.addWidget(btn_browse)
        layout.addLayout(row)

        self.lbl_details = QLabel("")
        self.lbl_details.setStyleSheet("color: #0284c7; font-size: 11px;")
        layout.addWidget(self.lbl_details)

    def _on_browse_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem ISO do Windows",
            str(Path.home()),
            "Imagens de Disco (*.iso);;Todos os Arquivos (*)",
        )
        if file_path:
            self.set_iso_path(Path(file_path))

    def set_iso_path(self, path: Path) -> None:
        info = inspect_iso_file(path)
        self._current_iso = WindowsISO(
            file_path=path,
            file_name=info["file_name"],
            size_bytes=info["size_bytes"],
            size_human=info["size_human"],
            has_install_wim=info.get("has_install_wim", False),
            has_install_esd=info.get("has_install_esd", False),
            install_image_size=info.get("install_image_size", 0),
            is_valid=info.get("is_valid", True),
        )
        self.lbl_path.setText(str(path))
        self.lbl_path.setStyleSheet("font-weight: bold;")

        details = f"Tamanho: {self._current_iso.size_human}"
        if self._current_iso.has_install_wim:
            details += " | Imagem: install.wim detectado"
        elif self._current_iso.has_install_esd:
            details += " | Imagem: install.esd detectado"
        self.lbl_details.setText(details)

        self.iso_selected.emit(self._current_iso)

    def get_iso(self) -> WindowsISO | None:
        return self._current_iso


class DriveSelectorCard(CardFrame):
    """Component to list and refresh removable USB devices."""

    drive_selected = Signal(object)  # StorageDevice
    refresh_requested = Signal()
    filter_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._devices: list[StorageDevice] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("<b>2. Pendrive / Mídia USB de Destino</b>")
        layout.addWidget(title)

        row = QHBoxLayout()
        self.combo_drives = QComboBox()
        self.combo_drives.currentIndexChanged.connect(self._on_selection_changed)
        row.addWidget(self.combo_drives, stretch=1)

        self.btn_refresh = QPushButton("Atualizar")
        self.btn_refresh.clicked.connect(lambda: self.refresh_requested.emit())
        row.addWidget(self.btn_refresh)
        layout.addLayout(row)

        self.chk_hide_large = QCheckBox("Ocultar discos grandes (> 64 GB)")
        self.chk_hide_large.setChecked(True)
        self.chk_hide_large.setToolTip(
            "Oculta discos rígidos externos e SSDs de grande capacidade para evitar seleção acidental de mídias de backup."
        )
        self.chk_hide_large.toggled.connect(self._on_filter_toggled)
        layout.addWidget(self.chk_hide_large)

        self.lbl_warning = QLabel("Apenas pendrives USB removíveis elegíveis são exibidos.")
        self.lbl_warning.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.lbl_warning)

    def _on_filter_toggled(self, checked: bool) -> None:
        self.filter_toggled.emit(checked)

    def is_hide_large_drives_active(self) -> bool:
        return self.chk_hide_large.isChecked()

    def populate_devices(self, devices: list[StorageDevice]) -> None:
        self._devices = devices
        self.combo_drives.clear()
        if not devices:
            msg = (
                "Nenhum pendrive USB detectado (desmarque 'Ocultar discos grandes' caso use HD/SSD)"
                if self.is_hide_large_drives_active()
                else "Nenhum pendrive USB removível detectado"
            )
            self.combo_drives.addItem(msg)
            self.combo_drives.setEnabled(False)
            self.drive_selected.emit(None)
            return

        self.combo_drives.setEnabled(True)
        for dev in devices:
            self.combo_drives.addItem(dev.display_name, dev)

        self._on_selection_changed(0)

    def _on_selection_changed(self, index: int) -> None:
        if 0 <= index < len(self._devices):
            self.drive_selected.emit(self._devices[index])
        else:
            self.drive_selected.emit(None)

    def get_selected_device(self) -> StorageDevice | None:
        index = self.combo_drives.currentIndex()
        if 0 <= index < len(self._devices):
            return self._devices[index]
        return None


class OptionsCard(CardFrame):
    """Component for filesystem and bootloader configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("<b>3. Opções de Formatação e Boot</b>")
        layout.addWidget(title)

        row = QHBoxLayout()
        self.rb_fat32 = QRadioButton("FAT32 (Recomendado - UEFI + Legacy BIOS)")
        self.rb_fat32.setChecked(True)
        self.rb_ntfs = QRadioButton("NTFS")

        self.fs_group = QButtonGroup(self)
        self.fs_group.addButton(self.rb_fat32)
        self.fs_group.addButton(self.rb_ntfs)

        row.addWidget(self.rb_fat32)
        row.addWidget(self.rb_ntfs)
        row.addStretch()
        layout.addLayout(row)

    def get_filesystem(self) -> FileSystemType:
        if self.rb_fat32.isChecked():
            return FileSystemType.FAT32
        return FileSystemType.NTFS

    def get_boot_mode(self) -> BootMode:
        return BootMode.UEFI_AND_LEGACY


class ProgressCard(CardFrame):
    """Component displaying real-time progress, stage description and speed."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        row_header = QHBoxLayout()
        self.lbl_stage = QLabel("Pronto para iniciar gravação.")
        self.lbl_stage.setStyleSheet("font-weight: bold; color: #0f172a;")
        self.lbl_speed = QLabel("")
        self.lbl_speed.setStyleSheet("color: #0284c7; font-weight: bold; font-size: 11px;")
        row_header.addWidget(self.lbl_stage, stretch=1)
        row_header.addWidget(self.lbl_speed)
        layout.addLayout(row_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                text-align: center;
                height: 22px;
                background-color: #f1f5f9;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #0284c7;
                border-radius: 5px;
            }
            """
        )
        layout.addWidget(self.progress_bar)

    def update_progress(self, percent: float, stage_text: str, speed: str = "") -> None:
        self.progress_bar.setValue(int(percent))
        self.progress_bar.setFormat(f"{int(percent)}% - {stage_text}")
        self.lbl_stage.setText(stage_text)
        self.lbl_speed.setText(speed)

    def reset(self) -> None:
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.lbl_stage.setText("Pronto para iniciar gravação.")
        self.lbl_speed.setText("")


class LogConsoleDrawer(QWidget):
    """Collapsible live log output with auto-scroll and copy button."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.btn_toggle = QPushButton("▼ Ocultar Logs")
        self.btn_toggle.clicked.connect(self._toggle_view)
        header.addWidget(self.btn_toggle)

        btn_copy = QPushButton("Copiar Logs")
        btn_copy.clicked.connect(self._copy_logs)
        header.addWidget(btn_copy)
        header.addStretch()
        layout.addLayout(header)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("monospace", 9))
        self.text_edit.setStyleSheet(
            "background-color: #0f172a; color: #f8fafc; border-radius: 6px;"
        )
        layout.addWidget(self.text_edit)

    def append_line(self, line: str) -> None:
        self.text_edit.append(line)
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    def _toggle_view(self) -> None:
        if self.text_edit.isVisible():
            self.text_edit.hide()
            self.btn_toggle.setText("▶ Exibir Logs")
        else:
            self.text_edit.show()
            self.btn_toggle.setText("▼ Ocultar Logs")

    def _copy_logs(self) -> None:
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text_edit.toPlainText())
