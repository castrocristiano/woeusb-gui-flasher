"""Utility functions for byte formatting, process execution, and system helpers."""

from __future__ import annotations

import logging
import math
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def format_bytes(size_bytes: int) -> str:
    """Format an integer byte count into a human-readable string (e.g. 5.12 GB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = math.floor(math.log(size_bytes, 1024))
    i = min(i, len(units) - 1)
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {units[i]}"


def find_binary(name: str) -> str | None:
    """Locate an executable binary in standard PATH or Flatpak /app/bin."""
    # Check Flatpak /app/bin first if inside Flatpak
    app_bin = Path("/app/bin") / name
    if app_bin.is_file() and os.access(app_bin, os.X_OK):
        return str(app_bin)
    found = shutil.which(name)
    return found


def run_command_streaming(
    cmd: list[str],
    line_callback: Callable[[str], None] | None = None,
    abort_check: Callable[[], bool] | None = None,
) -> int:
    """Execute a command and stream stdout/stderr lines in real time.

    Returns the process exit code.
    """
    logger.debug("Executing command: %s", " ".join(cmd))
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    try:
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if abort_check and abort_check():
                    logger.warning("Abort requested, terminating process: %s", cmd[0])
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return -1
                clean_line = line.strip()
                if clean_line and line_callback:
                    line_callback(clean_line)
        process.stdout.close()
        process.wait()
        return process.returncode
    except (OSError, RuntimeError) as exc:
        logger.error("Command execution error: %s", exc)
        process.kill()
        return -1


def inspect_iso_file(iso_path: Path) -> dict:
    """Inspect a Windows ISO file to detect size and install image presence."""
    if not iso_path.is_file():
        raise FileNotFoundError(f"Arquivo ISO não encontrado: {iso_path}")

    size_bytes = iso_path.stat().st_size
    info = {
        "file_path": iso_path,
        "file_name": iso_path.name,
        "size_bytes": size_bytes,
        "size_human": format_bytes(size_bytes),
        "has_install_wim": False,
        "has_install_esd": False,
        "install_image_size": 0,
        "is_valid": True,
    }

    # If 7z is available, list archive contents to inspect install.wim/esd
    seven_z = find_binary("7z")
    if seven_z:
        try:
            res = subprocess.run(
                [seven_z, "l", "-slt", str(iso_path)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            current_path = ""
            for line in res.stdout.splitlines():
                if line.startswith("Path = "):
                    current_path = line[len("Path = ") :].strip()
                elif line.startswith("Size = ") and current_path:
                    try:
                        f_size = int(line[len("Size = ") :].strip())
                    except ValueError:
                        f_size = 0
                    normalized_path = current_path.replace("\\", "/").lower()
                    if normalized_path.endswith("sources/install.wim"):
                        info["has_install_wim"] = True
                        info["install_image_size"] = f_size
                    elif normalized_path.endswith("sources/install.esd"):
                        info["has_install_esd"] = True
                        if not info["has_install_wim"]:
                            info["install_image_size"] = f_size
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            logger.warning("Could not inspect ISO with 7z: %s", exc)

    return info
