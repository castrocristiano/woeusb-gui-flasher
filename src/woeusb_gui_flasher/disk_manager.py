"""Disk discovery, enumeration, security filtering, and partition unmounting."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from woeusb_gui_flasher.models import StorageDevice
from woeusb_gui_flasher.utils import find_binary, format_bytes

logger = logging.getLogger(__name__)

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
        pass

    def filter_safe_device(self, device: StorageDevice) -> bool:
        """Determines if a device is safe and eligible for formatting."""
        return device.is_eligible_target()

    def parse_lsblk_data(self, data: dict[str, Any]) -> list[StorageDevice]:
        """Parses JSON data returned by lsblk -J -b into StorageDevice objects."""
        devices: list[StorageDevice] = []

        for item in data.get("blockdevices", []):
            name = item.get("name", "")
            path = item.get("path", f"/dev/{name}")
            try:
                size_bytes = int(item.get("size", 0))
            except (ValueError, TypeError):
                size_bytes = 0

            rm_flag = bool(item.get("rm", False))
            tran = (item.get("tran") or "").lower()
            is_removable = rm_flag or (tran == "usb")

            vendor = (item.get("vendor") or "").strip()
            model = (item.get("model") or "").strip()

            # Collect mountpoints from device and all children
            mount_points: set[str] = set()
            partitions: list[str] = []

            for mp in item.get("mountpoints", []):
                if mp:
                    mount_points.add(str(mp))

            for child in item.get("children", []):
                child_name = child.get("name", "")
                partitions.append(child.get("path", f"/dev/{child_name}"))
                for mp in child.get("mountpoints", []):
                    if mp:
                        mount_points.add(str(mp))

            # Safety check: is it a system drive?
            is_system = False
            for mp in mount_points:
                if mp in SYSTEM_MOUNT_POINTS:
                    is_system = True
                    break

            device = StorageDevice(
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
            devices.append(device)

        return devices

    def get_removable_devices(self) -> list[StorageDevice]:
        """Discovers block devices and returns only safe, removable USB drives."""
        # Try D-Bus UDisks2 enumeration first
        devices = self._get_devices_via_udisks2()
        if not devices:
            devices = self._get_devices_via_lsblk()

        # Strict safety filtering
        safe_devices = [d for d in devices if self.filter_safe_device(d)]
        logger.info(
            "Found %d total devices, %d eligible USB drives",
            len(devices),
            len(safe_devices),
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
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
            logger.error("Error enumerating devices with lsblk: %s", exc)
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

    def unmount_device_partitions(self, device: StorageDevice) -> bool:
        """Unmounts all mounted partitions belonging to the device."""
        udisksctl = find_binary("udisksctl")
        gdbus = find_binary("gdbus")
        umount = find_binary("umount")

        success = True
        targets_to_unmount = device.partitions or [device.path]

        for part in targets_to_unmount:
            logger.info("Attempting to unmount %s", part)
            if udisksctl:
                res = subprocess.run(
                    [udisksctl, "unmount", "-b", part, "--force"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0:
                    logger.info("Successfully unmounted %s via udisksctl", part)
                    continue
                # If error is 'not mounted', that's fine
                if "not mounted" in res.stderr.lower():
                    continue
            elif gdbus:
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
                    continue
                if "notmounted" in (res.stderr.lower() or res.stdout.lower()):
                    continue

            if umount:
                res = subprocess.run(
                    [umount, "-f", part],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode != 0 and "not mounted" not in res.stderr.lower():
                    logger.warning("umount returned: %s", res.stderr.strip())

        return success
