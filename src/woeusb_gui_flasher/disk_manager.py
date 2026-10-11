"""Disk discovery, enumeration, security filtering, and partition unmounting."""

from __future__ import annotations

import json
import logging
import string
import subprocess
from pathlib import Path
from typing import Any

from woeusb_gui_flasher.models import DiskCollisionCheckResult, StorageDevice
from woeusb_gui_flasher.utils import find_binary, format_bytes

logger = logging.getLogger(__name__)

DEV_PREFIX = "/dev/"
SYSTEM_MOUNT_POINTS = {
    "/",
    "/boot",
    "/boot/efi",
    "/home",
    "/usr",
    "/var",
    "/etc",
    "[SWAP]",
}


class DiskManager:
    """Manages storage devices discovery, safety filters, and unmounting."""

    def __init__(self) -> None:
        # DiskManager is stateless; initialization requires no setup
        pass

    @staticmethod
    def get_parent_disk_name(device_or_partition: str | Path) -> str:
        """Normalizes a partition or block device path to its root physical disk path.

        Examples:
            /dev/sdd1 -> /dev/sdd
            /dev/sdd -> /dev/sdd
            /dev/nvme0n1p2 -> /dev/nvme0n1
            /dev/mmcblk0p1 -> /dev/mmcblk0
            sdd1 -> /dev/sdd
        """
        dev_str = str(device_or_partition).strip()
        if not dev_str:
            return ""

        if not dev_str.startswith(DEV_PREFIX):
            dev_str = f"{DEV_PREFIX}{dev_str}"

        name = dev_str[len(DEV_PREFIX) :]

        if name.startswith(("nvme", "mmcblk", "loop")):
            prefix, sep, suffix = name.rpartition("p")
            if sep and suffix.isdigit() and prefix:
                return f"{DEV_PREFIX}{prefix}"
            return f"{DEV_PREFIX}{name}"

        parent_name = name.rstrip(string.digits)
        return f"{DEV_PREFIX}{parent_name}"

    @staticmethod
    def _get_file_dev_maj_min(file_path: Path | str) -> str | None:
        try:
            resolved = Path(file_path).resolve()
            if not resolved.exists():
                return None
            stat_res = resolved.stat()
            dev_major = (stat_res.st_dev >> 8) & 0xFFF
            dev_minor = stat_res.st_dev & 0xFF
            return f"{dev_major}:{dev_minor}"
        except OSError as exc:
            logger.debug("Cannot stat %s: %s", file_path, exc)
            return None

    @staticmethod
    def _parse_mountinfo_source(line: str) -> tuple[str, str]:
        parts = line.strip().split()
        if len(parts) < 5:
            return "", ""
        maj_min = parts[2]
        try:
            sep_idx = parts.index("-")
            mount_source = parts[sep_idx + 2] if sep_idx + 2 < len(parts) else ""
        except ValueError:
            mount_source = ""
        return maj_min, mount_source

    def resolve_file_source_block_device(self, file_path: Path | str) -> str | None:
        """Determines the underlying partition or block device for a file path.

        Reads /proc/self/mountinfo to match the st_dev (major:minor) or mountpoint
        of the canonical resolved file path.
        """
        target_dev_str = self._get_file_dev_maj_min(file_path)
        if not target_dev_str:
            return None

        mountinfo_path = Path("/proc/self/mountinfo")
        if not mountinfo_path.exists():
            return None

        try:
            lines = mountinfo_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            logger.debug("Cannot read mountinfo: %s", exc)
            return None

        for line in lines:
            maj_min, mount_source = self._parse_mountinfo_source(line)
            if maj_min == target_dev_str and mount_source.startswith(DEV_PREFIX):
                return mount_source

        return None

    def check_same_disk_collision(
        self, iso_path: Path | str, target_device: StorageDevice
    ) -> DiskCollisionCheckResult:
        """Checks if the ISO file is stored on the same physical disk as the target device."""
        iso_p = Path(iso_path)
        source_part = self.resolve_file_source_block_device(iso_p)
        if not source_part:
            return DiskCollisionCheckResult(
                has_collision=False,
                message="Origem em sistema de arquivos sem dispositivo de bloco direto.",
            )

        source_parent = self.get_parent_disk_name(source_part)
        target_parent = self.get_parent_disk_name(target_device.path)

        if source_parent and target_parent and source_parent == target_parent:
            msg = (
                f"A imagem ISO selecionada ({iso_p.name}) está armazenada no mesmo disco físico "
                f"({source_parent}) que o dispositivo de destino ({target_device.path}). "
                "Para evitar perda de dados e corrupção, selecione outro pendrive ou transfira "
                "a ISO para outro disco."
            )
            logger.warning("Same-disk collision detected: %s == %s", source_parent, target_parent)
            return DiskCollisionCheckResult(
                has_collision=True,
                source_partition=source_part,
                source_parent_disk=source_parent,
                target_parent_disk=target_parent,
                message=msg,
            )

        return DiskCollisionCheckResult(
            has_collision=False,
            source_partition=source_part,
            source_parent_disk=source_parent,
            target_parent_disk=target_parent,
            message="Origem e destino em discos físicos distintos.",
        )

    def filter_safe_device(self, device: StorageDevice, hide_large_drives: bool = True) -> bool:
        """Determines if a device is safe and eligible for formatting."""
        return device.is_eligible_target(hide_large_drives=hide_large_drives)

    @staticmethod
    def _collect_mountpoints_and_partitions(
        item: dict[str, Any],
    ) -> tuple[set[str], list[str]]:
        mount_points: set[str] = set()
        partitions: list[str] = []

        for mp in item.get("mountpoints", []):
            if mp:
                mount_points.add(str(mp))

        for child in item.get("children", []):
            child_name = child.get("name", "")
            partitions.append(child.get("path", f"{DEV_PREFIX}{child_name}"))
            for mp in child.get("mountpoints", []):
                if mp:
                    mount_points.add(str(mp))

        return mount_points, partitions

    @staticmethod
    def _is_system_mount(mount_points: set[str]) -> bool:
        return any(mp in SYSTEM_MOUNT_POINTS for mp in mount_points)

    def _parse_single_blockdevice(self, item: dict[str, Any]) -> StorageDevice:
        name = item.get("name", "")
        path = item.get("path", f"{DEV_PREFIX}{name}")
        try:
            size_bytes = int(item.get("size", 0))
        except (ValueError, TypeError):
            size_bytes = 0

        rm_flag = bool(item.get("rm", False))
        tran = (item.get("tran") or "").lower()
        is_removable = rm_flag or (tran == "usb")

        vendor = (item.get("vendor") or "").strip()
        model = (item.get("model") or "").strip()

        mount_points, partitions = self._collect_mountpoints_and_partitions(item)
        is_system = self._is_system_mount(mount_points)

        return StorageDevice(
            name=name,
            path=path,
            size_bytes=size_bytes,
            size_human=format_bytes(size_bytes),
            vendor=vendor,
            model=model,
            is_removable=is_removable,
            is_system_drive=is_system,
            mount_points=list(mount_points),
            partitions=partitions,
        )

    def parse_lsblk_data(self, data: dict[str, Any]) -> list[StorageDevice]:
        """Parses JSON data returned by lsblk -J -b into StorageDevice objects."""
        return [self._parse_single_blockdevice(item) for item in data.get("blockdevices", [])]

    def get_removable_devices(self, hide_large_drives: bool = True) -> list[StorageDevice]:
        """Discovers block devices and returns only safe, removable USB drives."""
        # Try D-Bus UDisks2 enumeration first
        devices = self._get_devices_via_udisks2()
        if not devices:
            devices = self._get_devices_via_lsblk()

        # Strict safety filtering
        safe_devices = [
            d for d in devices if self.filter_safe_device(d, hide_large_drives=hide_large_drives)
        ]
        logger.info(
            "Found %d total devices, %d eligible USB drives (hide_large_drives=%s)",
            len(devices),
            len(safe_devices),
            hide_large_drives,
        )
        return safe_devices

    def _get_devices_via_lsblk(self) -> list[StorageDevice]:
        """Discovers devices by calling lsblk with JSON output."""
        lsblk = find_binary("lsblk")
        if not lsblk:
            logger.warning("lsblk binary not found")
            return []

        try:
            cmd = [
                lsblk,
                "-J",
                "-b",
                "-o",
                "NAME,PATH,SIZE,ROTA,RM,MODEL,VENDOR,TRAN,MOUNTPOINTS,FSTYPE",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            return self.parse_lsblk_data(data)
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
            logger.exception("Error enumerating devices with lsblk")
            return []

    def _get_devices_via_udisks2(self) -> list[StorageDevice]:
        """Discovers devices via system D-Bus org.freedesktop.UDisks2 if available."""
        # Optional native Gio/dasbus interface
        try:
            from gi.repository import Gio

            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.freedesktop.UDisks2",
                "/org/freedesktop/UDisks2",
                "org.freedesktop.DBus.ObjectManager",
                None,
            )
            managed_objects = proxy.GetManagedObjects()
            if not managed_objects:
                return []

            # Fallback to lsblk parser if D-Bus structure is empty
            return self._get_devices_via_lsblk()
        except (ImportError, AttributeError, OSError, RuntimeError) as exc:
            logger.debug("D-Bus UDisks2 query unavailable: %s", exc)
            return []

    @staticmethod
    def _unmount_with_udisksctl(udisksctl: str, part: str) -> bool:
        res = subprocess.run(
            [udisksctl, "unmount", "-b", part, "--force"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            logger.info("Successfully unmounted %s via udisksctl", part)
            return True
        return "not mounted" in res.stderr.lower()

    @staticmethod
    def _unmount_with_gdbus(gdbus: str, part: str) -> bool:
        part_name = Path(part).name
        res = subprocess.run(
            [
                gdbus,
                "call",
                "--system",
                "--dest",
                "org.freedesktop.UDisks2",
                "--object-path",
                f"/org/freedesktop/UDisks2/block_devices/{part_name}",
                "--method",
                "org.freedesktop.UDisks2.Filesystem.Unmount",
                "{}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            logger.info("Successfully unmounted %s via gdbus UDisks2", part)
            return True
        return "notmounted" in (res.stderr.lower() or res.stdout.lower())

    @staticmethod
    def _unmount_with_umount(umount: str, part: str) -> None:
        res = subprocess.run(
            [umount, "-f", part],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0 and "not mounted" not in res.stderr.lower():
            logger.warning("umount returned: %s", res.stderr.strip())

    def _unmount_single_target(
        self,
        part: str,
        udisksctl: str | None,
        gdbus: str | None,
        umount: str | None,
    ) -> None:
        logger.info("Attempting to unmount %s", part)
        unmounted = False
        if udisksctl:
            unmounted = self._unmount_with_udisksctl(udisksctl, part)
        elif gdbus:
            unmounted = self._unmount_with_gdbus(gdbus, part)

        if not unmounted and umount:
            self._unmount_with_umount(umount, part)

    def unmount_device_partitions(self, device: StorageDevice) -> bool:
        """Unmounts all mounted partitions belonging to the device."""
        udisksctl = find_binary("udisksctl")
        gdbus = find_binary("gdbus")
        umount = find_binary("umount")

        targets_to_unmount = device.partitions or [device.path]
        for part in targets_to_unmount:
            self._unmount_single_target(part, udisksctl, gdbus, umount)

        return True
