"""Domain entities, enums, and data models for WoeUSB GUI Flasher."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from woeusb_gui_flasher.i18n import tr


class FileSystemType(str, Enum):
    """Supported target filesystem types."""

    FAT32 = "FAT32"
    NTFS = "NTFS"


class BootMode(str, Enum):
    """Supported bootloader strategies."""

    UEFI_AND_LEGACY = "UEFI_AND_LEGACY"
    UEFI_ONLY = "UEFI_ONLY"


class BurnStage(str, Enum):
    """Lifecycle stages of the burning operation."""

    IDLE = "IDLE"
    VALIDATING = "VALIDATING"
    UNMOUNTING = "UNMOUNTING"
    PARTITIONING = "PARTITIONING"
    FORMATTING = "FORMATTING"
    MOUNTING = "MOUNTING"
    EXTRACTING_ISO = "EXTRACTING_ISO"
    SPLITTING_WIM = "SPLITTING_WIM"
    CONFIGURING_BOOT = "CONFIGURING_BOOT"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


MAX_TYPICAL_PENDRIVE_BYTES: int = 68_719_476_736  # 64 GiB (68.7 GB)


@dataclass
class StorageDevice:
    """Represents a block storage device identified by the operating system."""

    name: str
    path: str
    size_bytes: int
    size_human: str
    vendor: str = ""
    model: str = ""
    is_removable: bool = False
    is_system_drive: bool = False
    mount_points: list[str] = field(default_factory=list)
    partitions: list[str] = field(default_factory=list)

    @property
    def is_large_drive(self) -> bool:
        """True if the device exceeds standard flash drive capacity (> 64 GiB / 68.7 GB)."""
        return self.size_bytes > MAX_TYPICAL_PENDRIVE_BYTES

    def is_eligible_target(self, hide_large_drives: bool = False) -> bool:
        """A device is eligible if it is removable, >= 2 GB, not a system drive, and within size limit if filtering."""
        min_size = 2_000_000_000  # 2 GB
        if self.is_system_drive:
            return False
        if not self.is_removable:
            return False
        if self.size_bytes < min_size:
            return False
        if hide_large_drives and self.is_large_drive:
            return False
        # Double-check mount points for safety
        for mp in self.mount_points:
            if mp in ("/", "/boot", "/boot/efi", "/home", "/usr", "/var", "[SWAP]"):
                return False
        return True

    @property
    def display_name(self) -> str:
        """Formatted human label for UI dropdowns."""
        desc = f"{self.vendor} {self.model}".strip() or self.name
        return f"{self.path} ({self.size_human}) - {desc}"


@dataclass
class DiskCollisionCheckResult:
    """Result of checking whether ISO source and target device share the same physical disk."""

    has_collision: bool
    source_partition: str | None = None
    source_parent_disk: str | None = None
    target_parent_disk: str | None = None
    message: str = ""


@dataclass
class WindowsISO:
    """Represents a Windows installer disk image file."""

    file_path: Path
    file_name: str
    size_bytes: int
    size_human: str
    has_install_wim: bool = False
    has_install_esd: bool = False
    install_image_size: int = 0
    requires_split: bool = False
    is_valid: bool = False

    MAX_FAT32_FILE_SIZE = 4_294_967_295  # 4 GB - 1 byte

    def check_requires_split(self, target_fs: FileSystemType) -> bool:
        """Checks if install.wim exceeds the 4 GB limit on FAT32."""
        return (
            target_fs == FileSystemType.FAT32 and self.install_image_size > self.MAX_FAT32_FILE_SIZE
        )


@dataclass
class BurnConfiguration:
    """Configuration options for a burning operation."""

    iso: WindowsISO
    target_device: StorageDevice
    filesystem: FileSystemType = FileSystemType.FAT32
    boot_mode: BootMode = BootMode.UEFI_AND_LEGACY
    label: str = "WININSTALL"

    def validate(self) -> None:
        """Validates configuration sanity before execution."""
        if not self.target_device.is_eligible_target():
            raise ValueError(
                tr("model.validation.ineligible_device", device_path=self.target_device.path)
            )
        if not self.iso.file_path.is_file():
            raise FileNotFoundError(
                tr("model.validation.iso_not_found", iso_path=self.iso.file_path)
            )
        if self.target_device.size_bytes < self.iso.size_bytes:
            raise ValueError(
                tr(
                    "model.validation.insufficient_space",
                    device_size=self.target_device.size_human,
                    iso_size=self.iso.size_human,
                )
            )

        from woeusb_gui_flasher.disk_manager import DiskManager

        collision = DiskManager().check_same_disk_collision(self.iso.file_path, self.target_device)
        if collision.has_collision:
            raise ValueError(collision.message)


@dataclass
class BurnOperationState:
    """Current real-time state of the burning operation."""

    stage: BurnStage = BurnStage.IDLE
    stage_description: str = field(default_factory=lambda: tr("ui.progress.ready"))
    progress_percent: float = 0.0
    bytes_written: int = 0
    total_bytes: int = 0
    transfer_speed: str = "0.0 MB/s"
    elapsed_seconds: int = 0
    is_running: bool = False
    error_message: str | None = None
