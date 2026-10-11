"""Asynchronous burn engine implementation using QThread."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from woeusb_gui_flasher.disk_manager import DiskManager
from woeusb_gui_flasher.models import (
    BurnConfiguration,
    BurnStage,
    FileSystemType,
)
from woeusb_gui_flasher.utils import find_binary, format_bytes

logger = logging.getLogger(__name__)

# --- Conversion & Size Constants ---
BYTES_PER_MIB: int = 1024 * 1024
BYTES_PER_GIB: int = 1024 * 1024 * 1024
MAX_FAT32_FILE_SIZE_BYTES: int = 4_294_967_295  # 4 GiB - 1 byte
DEFAULT_WIM_SPLIT_CHUNK_SIZE_MB: str = "3800"

# --- Progress Allocation Benchmarks (0.0 to 100.0) ---
STAGE_PCT_START: float = 0.0
STAGE_PCT_VALIDATING: float = 2.0
STAGE_PCT_UNMOUNTING: float = 8.0
STAGE_PCT_PARTITIONING: float = 15.0
STAGE_PCT_EXTRACTION_BASE: float = 25.0
STAGE_PCT_EXTRACTION_SPAN: float = 50.0  # Scales 0-100% to 25-75%
STAGE_PCT_WIM_SPLIT_BASE: float = 75.0
STAGE_PCT_WIM_SPLIT_SPAN: float = 15.0  # Scales 0-100% to 75-90%
STAGE_PCT_CONFIGURING_BOOT: float = 90.0
STAGE_PCT_FINALIZING: float = 95.0
STAGE_PCT_COMPLETED: float = 100.0

# --- Process Streaming & Logging Milestones ---
STREAM_BUFFER_CHUNK_SIZE: int = 64
LOG_MILESTONE_STEP_PERCENT: float = 5.0
LOG_MILESTONE_MIN_SECONDS: float = 3.0
MIN_ELAPSED_SECONDS: float = 0.5

# --- File, Directory & D-Bus Constants ---
INSTALL_WIM_FILENAME: str = "install.wim"
INSTALL_ESD_FILENAME: str = "install.esd"
INSTALL_SWM_FILENAME: str = "install.swm"
SOURCES_DIRNAME: str = "sources"
BOOTX64_EFI_FILENAME: str = "bootx64.efi"
BOOTMGFW_EFI_FILENAME: str = "bootmgfw.efi"

TEMP_WIM_DIR: Path = Path(tempfile.gettempdir()) / "woeusb_temp"
FALLBACK_MOUNT_DIR: Path = Path(tempfile.gettempdir()) / "woeusb_mount"
MOCK_MOUNT_DIR: Path = Path(tempfile.gettempdir()) / "woeusb_mock_mount"

DBUS_UDISKS2_DEST: str = "org.freedesktop.UDisks2"
DBUS_UDISKS2_BLOCK_PATH: str = "/org/freedesktop/UDisks2/block_devices"


@dataclass
class ProgressTracker:
    """Computes transfer speeds, transferred byte amounts, and estimated remaining time."""

    total_bytes: int
    start_time: float = field(default_factory=time.time)
    last_log_percent: float = -LOG_MILESTONE_STEP_PERCENT
    last_log_time: float = 0.0

    def compute_metrics(self, current_pct: float) -> tuple[int, float, str]:
        """Calculates (bytes_transferred, speed_mb_s, eta_formatted)."""
        clamped_pct = max(0.0, min(100.0, current_pct))
        transferred = int(self.total_bytes * (clamped_pct / 100.0))
        elapsed = max(time.time() - self.start_time, MIN_ELAPSED_SECONDS)
        speed_mb_s = (transferred / BYTES_PER_MIB) / elapsed

        remaining_bytes = max(self.total_bytes - transferred, 0)
        speed_bytes_s = transferred / elapsed
        if speed_bytes_s > 0:
            remaining_seconds = int(remaining_bytes / speed_bytes_s)
            eta_formatted = f"{remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}"
        else:
            eta_formatted = "--:--"

        return transferred, speed_mb_s, eta_formatted

    def is_log_milestone(self, current_pct: float) -> bool:
        """Determines if the current progress constitutes a periodic milestone for logging."""
        now = time.time()
        time_diff = now - self.last_log_time
        pct_diff = current_pct - self.last_log_percent

        if pct_diff >= LOG_MILESTONE_STEP_PERCENT or (
            time_diff >= LOG_MILESTONE_MIN_SECONDS and pct_diff >= 1.0
        ):
            self.last_log_percent = current_pct
            self.last_log_time = now
            return True
        return False


class BurnWorker(QThread):
    """Worker thread that executes the full Windows USB creation process."""

    # Signals
    progress_changed = Signal(float, str, str)  # percent, stage_text, speed_text
    log_line_emitted = Signal(str)  # log line
    status_updated = Signal(str, bool)  # message, is_warning
    operation_finished = Signal(bool, str)  # success, message

    def __init__(self, config: BurnConfiguration, dry_run: bool = False) -> None:
        super().__init__()
        self.config = config
        self.dry_run = dry_run
        self._abort_requested = False
        self._active_process: subprocess.Popen | None = None
        self._temp_mount_dir: Path | None = None
        self._target_part: str | None = None
        self.disk_manager = DiskManager()

    def request_cancel(self) -> None:
        """Requests graceful cancellation of the ongoing burn operation."""
        self._abort_requested = True
        self.emit_log("Solicitação de cancelamento recebida pelo usuário...")
        if self._active_process:
            try:
                self._active_process.terminate()
            except (OSError, RuntimeError) as exc:
                logger.warning("Error terminating active process: %s", exc)

    def is_cancelled(self) -> bool:
        return self._abort_requested

    def emit_log(self, text: str) -> None:
        logger.info(text)
        self.log_line_emitted.emit(text)

    def emit_progress(self, percent: float, stage_text: str, speed: str = "") -> None:
        self.progress_changed.emit(percent, stage_text, speed)

    def emit_status(self, message: str, is_warning: bool = False) -> None:
        self.status_updated.emit(message, is_warning)

    def _set_stage(self, stage: BurnStage, percent: float, text: str) -> None:
        self.emit_progress(percent, text)
        self.emit_status(text)
        self.emit_log(f"[{stage.value}] {text}")

    def run(self) -> None:
        """Main execution loop run inside the QThread worker."""
        try:
            self._log_initial_banner()

            # 1. Validation & Safety Pre-checks
            if not self._step_validate():
                return

            # 2. Unmounting existing partitions
            if not self._step_unmount():
                return

            # 3. Partitioning & Formatting
            target_mount = self._step_format()
            if self.is_cancelled():
                return self._finish_cancelled()

            # 4. User-Space ISO Extraction
            if not self._step_extract(target_mount):
                return

            # 5. Split install.wim if necessary
            if self.config.filesystem == FileSystemType.FAT32 and not self._step_wim_split(
                target_mount
            ):
                return

            # 6. Configure bootloader
            if not self._step_bootloader(target_mount):
                return

            # 7. Finalizing, disk sync and unmount
            self._step_finalize(target_mount)

        except Exception as exc:
            logger.exception("Burn operation failed:")
            self.emit_log(f"ERRO CRÍTICO: {exc}")
            self.emit_status(f"Falha na operação: {exc}", True)
            self.operation_finished.emit(False, str(exc))

    def _log_initial_banner(self) -> None:
        self.emit_log("=== Iniciando WoeUSB GUI Flasher ===")
        self.emit_log(
            f"ISO selecionada: {self.config.iso.file_path} ({self.config.iso.size_human})"
        )
        self.emit_log(
            f"Dispositivo alvo: {self.config.target_device.path} ({self.config.target_device.size_human})"
        )
        self.emit_log(f"Sistema de arquivos: {self.config.filesystem.value}")

    def _step_validate(self) -> bool:
        self._set_stage(
            BurnStage.VALIDATING, STAGE_PCT_VALIDATING, "Validando requisitos e imagens..."
        )
        self.config.validate()
        if self.is_cancelled():
            self._finish_cancelled()
            return False
        return True

    def _step_unmount(self) -> bool:
        self._set_stage(
            BurnStage.UNMOUNTING, STAGE_PCT_UNMOUNTING, "Desmontando partições existentes..."
        )
        self.emit_log(f"Desmontando partições ativas de {self.config.target_device.path}...")
        if not self.dry_run:
            self.disk_manager.unmount_device_partitions(self.config.target_device)
        if self.is_cancelled():
            self._finish_cancelled()
            return False
        return True

    def _step_format(self) -> Path:
        self._set_stage(
            BurnStage.PARTITIONING,
            STAGE_PCT_PARTITIONING,
            "Criando tabela de partições e formatando...",
        )
        return self._prepare_and_format_drive()

    def _step_extract(self, target_mount: Path) -> bool:
        self._set_stage(
            BurnStage.EXTRACTING_ISO,
            STAGE_PCT_EXTRACTION_BASE,
            "Extraindo arquivos da imagem ISO...",
        )
        self._extract_iso_contents(target_mount)
        if self.is_cancelled():
            self._finish_cancelled()
            return False
        return True

    def _step_wim_split(self, target_mount: Path) -> bool:
        self._set_stage(
            BurnStage.SPLITTING_WIM,
            STAGE_PCT_WIM_SPLIT_BASE,
            "Verificando tamanho da imagem de instalação...",
        )
        self._handle_wim_split(target_mount)
        if self.is_cancelled():
            self._finish_cancelled()
            return False
        return True

    def _step_bootloader(self, target_mount: Path) -> bool:
        self._set_stage(
            BurnStage.CONFIGURING_BOOT,
            STAGE_PCT_CONFIGURING_BOOT,
            "Configurando bootloader UEFI/BIOS...",
        )
        self._configure_bootloader(target_mount)
        if self.is_cancelled():
            self._finish_cancelled()
            return False
        return True

    def _step_finalize(self, target_mount: Path) -> None:
        self._set_stage(
            BurnStage.FINALIZING, STAGE_PCT_FINALIZING, "Sincronizando buffers de disco (sync)..."
        )
        self.emit_log("Garantindo escrita de todos os buffers em disco...")
        if not self.dry_run:
            subprocess.run(["sync"], check=False)
            self._cleanup_mount(target_mount)

        self.emit_progress(STAGE_PCT_COMPLETED, "Concluído com sucesso!", "")
        self.emit_status("Gravação finalizada com sucesso!")
        self.emit_log("=== Gravação concluída com sucesso! Pode remover o pendrive. ===")
        self.operation_finished.emit(True, "Pendrive inicializável do Windows criado com sucesso!")

    def _finish_cancelled(self) -> None:
        if self._temp_mount_dir and not self.dry_run:
            try:
                self._cleanup_mount(self._temp_mount_dir)
            except (OSError, RuntimeError) as e:
                logger.warning("Error cleaning up mount during cancel: %s", e)
        self.emit_progress(STAGE_PCT_START, "Operação cancelada pelo usuário.")
        self.emit_status("Operação cancelada.")
        self.emit_log("=== Processo cancelado pelo usuário. Limpeza concluída. ===")
        self.operation_finished.emit(False, "Operação cancelada pelo usuário.")

    def _prepare_and_format_drive(self) -> Path:
        """Partitions and formats the USB thumb drive."""
        device_path = self.config.target_device.path
        fs_type = self.config.filesystem
        label = self.config.label

        if self.dry_run:
            self.emit_log(
                f"[DRY-RUN] Formatando {device_path} como {fs_type.value} com rótulo '{label}'..."
            )
            MOCK_MOUNT_DIR.mkdir(parents=True, exist_ok=True)
            self._temp_mount_dir = MOCK_MOUNT_DIR
            return MOCK_MOUNT_DIR

        target_part = f"{device_path}1" if not device_path.endswith("1") else device_path
        self._target_part = target_part
        self.emit_log(f"Formatando partição {target_part} como {fs_type.value}...")

        self._format_partition(target_part, fs_type, label)

        self.emit_log("Montando partição de destino...")
        return self._mount_partition(target_part)

    def _format_partition(self, target_part: str, fs_type: FileSystemType, label: str) -> None:
        """Formats the partition using UDisks2 D-Bus, udisksctl, or native mkfs fallback."""
        fs_arg = "vfat" if fs_type == FileSystemType.FAT32 else "ntfs"

        if find_binary("udisksctl") and self._format_via_udisksctl(target_part, fs_arg, label):
            return

        if find_binary("gdbus") and self._format_via_gdbus(target_part, fs_arg, label):
            return

        self._format_via_mkfs_fallback(target_part, fs_type, label)

    def _format_via_udisksctl(self, target_part: str, fs_arg: str, label: str) -> bool:
        cmd = [
            "udisksctl",
            "format",
            "-b",
            target_part,
            "-t",
            fs_arg,
            "--label",
            label,
            "--no-user-interaction",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            self.emit_log(f"Partição formatada via udisksctl: {res.stdout.strip()}")
            return True
        return False

    def _format_via_gdbus(self, target_part: str, fs_arg: str, label: str) -> bool:
        part_name = Path(target_part).name
        cmd = [
            "gdbus",
            "call",
            "--system",
            "--dest",
            DBUS_UDISKS2_DEST,
            "--object-path",
            f"{DBUS_UDISKS2_BLOCK_PATH}/{part_name}",
            "--method",
            "org.freedesktop.UDisks2.Block.Format",
            fs_arg,
            f"{{'label': <'{label}'>}}",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            self.emit_log(f"Partição formatada via UDisks2 (D-Bus): {target_part}")
            return True
        self.emit_log(f"Aviso UDisks2 format: {res.stderr.strip() or res.stdout.strip()}")
        return False

    def _format_via_mkfs_fallback(
        self, target_part: str, fs_type: FileSystemType, label: str
    ) -> None:
        if fs_type == FileSystemType.FAT32:
            mkfs_cmd = ["mkfs.vfat", "-F", "32", "-n", label, target_part]
        else:
            mkfs_cmd = ["mkfs.ntfs", "-f", "-L", label, target_part]

        res = subprocess.run(mkfs_cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise RuntimeError(f"Falha ao formatar partição: {res.stderr or res.stdout}")
        self.emit_log(f"Partição formatada com sucesso via mkfs: {mkfs_cmd[0]}")

    def _mount_partition(self, part_path: str) -> Path:
        """Mounts the formatted partition and returns the mount directory."""
        if find_binary("udisksctl"):
            mount_path = self._mount_via_udisksctl(part_path)
            if mount_path:
                return mount_path

        if find_binary("gdbus"):
            mount_path = self._mount_via_gdbus(part_path)
            if mount_path:
                return mount_path

        FALLBACK_MOUNT_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["mount", part_path, str(FALLBACK_MOUNT_DIR)], check=False)
        self._temp_mount_dir = FALLBACK_MOUNT_DIR
        return FALLBACK_MOUNT_DIR

    def _mount_via_udisksctl(self, part_path: str) -> Path | None:
        cmd = ["udisksctl", "mount", "-b", part_path, "--no-user-interaction"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            match = re.search(r"at\s+(/\S+)", res.stdout)
            if match:
                mount_path = Path(match.group(1))
                self.emit_log(f"Montado via udisksctl em {mount_path}")
                self._temp_mount_dir = mount_path
                return mount_path
        return None

    def _mount_via_gdbus(self, part_path: str) -> Path | None:
        part_name = Path(part_path).name
        cmd = [
            "gdbus",
            "call",
            "--system",
            "--dest",
            DBUS_UDISKS2_DEST,
            "--object-path",
            f"{DBUS_UDISKS2_BLOCK_PATH}/{part_name}",
            "--method",
            "org.freedesktop.UDisks2.Filesystem.Mount",
            "{}",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            match = re.search(r"'(/\S+)'", res.stdout)
            if match:
                mount_path = Path(match.group(1))
                self.emit_log(f"Montado via UDisks2 (D-Bus) em {mount_path}")
                self._temp_mount_dir = mount_path
                return mount_path
        return None

    def _extract_iso_contents(self, target_mount: Path) -> None:
        """Extracts Windows ISO files directly in user space using 7z."""
        seven_z = find_binary("7z")
        if not seven_z and not self.dry_run:
            raise FileNotFoundError(
                "O utilitário '7z' (p7zip) é necessário mas não foi encontrado no sistema."
            )

        iso_path = str(self.config.iso.file_path)
        self.emit_log(f"Iniciando extração com 7z para {target_mount}...")

        if self.dry_run:
            self._simulate_dry_run_extraction(target_mount)
            return

        cmd = self._build_7z_extract_cmd(seven_z, target_mount, iso_path)
        process = self._spawn_streaming_process(cmd)
        self._active_process = process

        tracker = ProgressTracker(total_bytes=self.config.iso.size_bytes)
        self._stream_7z_progress(process, tracker)

        process.wait()
        self._active_process = None

        if process.returncode != 0 and not self.is_cancelled():
            raise RuntimeError(
                f"A extração dos arquivos com 7z falhou com código {process.returncode}"
            )

    def _simulate_dry_run_extraction(self, target_mount: Path) -> None:
        self.emit_log("[DRY-RUN] Simulando extração de arquivos...")
        (target_mount / SOURCES_DIRNAME).mkdir(parents=True, exist_ok=True)
        (target_mount / SOURCES_DIRNAME / INSTALL_WIM_FILENAME).write_bytes(b"wim data" * 1000)
        (target_mount / "efi" / "boot").mkdir(parents=True, exist_ok=True)
        (target_mount / "efi" / "boot" / BOOTX64_EFI_FILENAME).write_bytes(b"efi data")

    def _build_7z_extract_cmd(self, seven_z: str, target_mount: Path, iso_path: str) -> list[str]:
        wim_size = self.config.iso.install_image_size
        needs_wim_split = (
            self.config.filesystem == FileSystemType.FAT32
            and self.config.iso.has_install_wim
            and wim_size > MAX_FAT32_FILE_SIZE_BYTES
        )
        cmd = [seven_z, "x", "-bso0", "-bsp1", "-bd"]
        if needs_wim_split:
            self.emit_log(
                "install.wim > 4 GB: excluindo da extração direta FAT32 para evitar erro de limite de 4 GB..."
            )
            cmd.extend([f"-xr!{INSTALL_WIM_FILENAME}", f"-xr!{INSTALL_ESD_FILENAME}"])
        cmd.extend([f"-o{target_mount}", iso_path])
        return cmd

    def _spawn_streaming_process(self, cmd: list[str]) -> subprocess.Popen:
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=STREAM_BUFFER_CHUNK_SIZE,
            universal_newlines=True,
        )

    @staticmethod
    def _extract_next_line(buffer: str) -> tuple[str | None, str]:
        if "\r" not in buffer and "\n" not in buffer:
            return None, buffer
        idx_r = buffer.find("\r")
        idx_n = buffer.find("\n")
        idx = min(idx_r, idx_n) if (idx_r != -1 and idx_n != -1) else max(idx_r, idx_n)
        return buffer[:idx].strip(), buffer[idx + 1 :]

    def _stream_output_chunks(
        self,
        process: subprocess.Popen,
        line_handler: Callable[[str], None],
    ) -> None:
        if not process.stdout:
            return
        buffer = ""
        for chunk in iter(lambda: process.stdout.read(STREAM_BUFFER_CHUNK_SIZE), ""):
            if self.is_cancelled():
                process.terminate()
                break
            buffer += chunk
            while True:
                line, buffer = self._extract_next_line(buffer)
                if line is None:
                    break
                if line:
                    line_handler(line)

    def _handle_7z_line(
        self,
        line: str,
        pct_pattern: re.Pattern,
        tracker: ProgressTracker,
    ) -> None:
        m = pct_pattern.search(line)
        if not m:
            self.emit_log(line)
            return

        current_pct = float(m.group(1))
        scaled_pct = STAGE_PCT_EXTRACTION_BASE + (current_pct * (STAGE_PCT_EXTRACTION_SPAN / 100.0))
        transferred, speed_mb, eta_str = tracker.compute_metrics(current_pct)

        stage_desc = (
            f"Copiando arquivos: {current_pct:.0f}% "
            f"({format_bytes(transferred)} / {format_bytes(tracker.total_bytes)})"
        )
        speed_desc = f"Escrita: {speed_mb:.1f} MB/s | Restante: {eta_str}"

        self.emit_progress(scaled_pct, stage_desc, speed_desc)

        if tracker.is_log_milestone(current_pct):
            self.emit_log(
                f"[COPIA] {stage_desc} | Velocidade: {speed_mb:.1f} MB/s | ETA: {eta_str}"
            )

    def _stream_7z_progress(self, process: subprocess.Popen, tracker: ProgressTracker) -> None:
        pct_pattern = re.compile(r"(\d+)%")
        self._stream_output_chunks(
            process,
            lambda line: self._handle_7z_line(line, pct_pattern, tracker),
        )

    def _handle_wim_split(self, target_mount: Path) -> None:
        """Splits install.wim if it exceeds 4 GB on a FAT32 filesystem."""
        sources_dir = target_mount / SOURCES_DIRNAME
        sources_dir.mkdir(parents=True, exist_ok=True)
        dest_swm = sources_dir / INSTALL_SWM_FILENAME

        should_split, wim_size, existing_wim = self._check_wim_split_needed(sources_dir)
        if not should_split:
            return

        self.emit_log(
            f"install.wim possui {wim_size / BYTES_PER_GIB:.2f} GB (> 4 GB). Iniciando divisão com wimlib-imagex..."
        )

        wimlib = find_binary("wimlib-imagex")
        seven_z = find_binary("7z")
        if not wimlib and not self.dry_run:
            raise FileNotFoundError(
                "O utilitário 'wimlib-imagex' é necessário para dividir arquivos WIM > 4 GB no FAT32."
            )

        if self.dry_run:
            self._simulate_dry_run_wim_split(sources_dir, existing_wim)
            return

        TEMP_WIM_DIR.mkdir(parents=True, exist_ok=True)
        temp_wim = TEMP_WIM_DIR / INSTALL_WIM_FILENAME

        try:
            if existing_wim.is_file():
                wim_to_split = existing_wim
            else:
                self._extract_wim_to_temp_storage(seven_z, temp_wim, wim_size)
                wim_to_split = temp_wim

            self._execute_wimlib_split(wimlib, wim_to_split, dest_swm, wim_size)

            self.emit_log("Divisão do install.wim concluída com sucesso! Volumes .swm criados.")
            if existing_wim.is_file():
                existing_wim.unlink(missing_ok=True)
        finally:
            if temp_wim.is_file():
                temp_wim.unlink(missing_ok=True)

    def _check_wim_split_needed(self, sources_dir: Path) -> tuple[bool, int, Path]:
        wim_size = self.config.iso.install_image_size
        existing_wim = sources_dir / INSTALL_WIM_FILENAME
        if existing_wim.is_file():
            wim_size = existing_wim.stat().st_size

        if wim_size <= MAX_FAT32_FILE_SIZE_BYTES and not existing_wim.is_file():
            self.emit_log(
                "install.wim não ultrapassa o limite de 4 GB do FAT32. Divisão desnecessária."
            )
            return False, wim_size, existing_wim

        return True, wim_size, existing_wim

    def _simulate_dry_run_wim_split(self, sources_dir: Path, existing_wim: Path) -> None:
        self.emit_log(
            f"[DRY-RUN] wimlib-imagex split install.wim {sources_dir / INSTALL_SWM_FILENAME} {DEFAULT_WIM_SPLIT_CHUNK_SIZE_MB}"
        )
        (sources_dir / INSTALL_SWM_FILENAME).write_bytes(b"swm1")
        (sources_dir / "install2.swm").write_bytes(b"swm2")
        if existing_wim.is_file():
            existing_wim.unlink(missing_ok=True)

    def _extract_wim_to_temp_storage(self, seven_z: str, temp_wim: Path, wim_size: int) -> None:
        self.emit_log(f"Extraindo install.wim para armazenamento temporário em {TEMP_WIM_DIR}...")
        extract_cmd = [
            seven_z,
            "e",
            "-bso0",
            "-bsp1",
            "-bd",
            f"-o{TEMP_WIM_DIR}",
            "-y",
            str(self.config.iso.file_path),
            f"{SOURCES_DIRNAME}/{INSTALL_WIM_FILENAME}",
        ]
        proc = self._spawn_streaming_process(extract_cmd)
        self._active_process = proc

        tracker = ProgressTracker(total_bytes=wim_size)
        self._stream_7z_progress(proc, tracker)

        proc.wait()
        self._active_process = None

        if self.is_cancelled():
            return
        if proc.returncode != 0:
            raise RuntimeError(f"Falha ao extrair install.wim: código {proc.returncode}")

    def _handle_wimlib_line(
        self,
        line: str,
        pct_pattern: re.Pattern,
        tracker: ProgressTracker,
        wim_size: int,
    ) -> None:
        m = pct_pattern.search(line)
        if not m:
            self.emit_log(line)
            return

        pct = float(m.group(1))
        scaled_pct = STAGE_PCT_WIM_SPLIT_BASE + (pct * (STAGE_PCT_WIM_SPLIT_SPAN / 100.0))
        transferred, speed_mb, eta_str = tracker.compute_metrics(pct)
        stage_desc = (
            f"Dividindo install.wim: {pct:.0f}% "
            f"({format_bytes(transferred)} / {format_bytes(wim_size)})"
        )
        speed_desc = f"Escrita: {speed_mb:.1f} MB/s | Restante: {eta_str}"
        self.emit_progress(scaled_pct, stage_desc, speed_desc)

    def _execute_wimlib_split(
        self, wimlib: str, wim_to_split: Path, dest_swm: Path, wim_size: int
    ) -> None:
        self.emit_log(
            f"Dividindo install.wim em volumes .swm de {DEFAULT_WIM_SPLIT_CHUNK_SIZE_MB} MB diretamente no pendrive..."
        )
        cmd = [
            wimlib,
            "split",
            str(wim_to_split),
            str(dest_swm),
            DEFAULT_WIM_SPLIT_CHUNK_SIZE_MB,
        ]
        self.emit_log(f"Executando: {' '.join(cmd)}")
        process = self._spawn_streaming_process(cmd)
        self._active_process = process

        pct_pattern = re.compile(r"(\d+)%")
        tracker = ProgressTracker(total_bytes=wim_size)
        self._stream_output_chunks(
            process,
            lambda line: self._handle_wimlib_line(line, pct_pattern, tracker, wim_size),
        )

        process.wait()
        self._active_process = None

        if self.is_cancelled():
            return
        if process.returncode != 0:
            raise RuntimeError(f"Falha ao dividir install.wim com código {process.returncode}")

    def _configure_bootloader(self, target_mount: Path) -> None:
        """Verifies and configures UEFI bootloaders."""
        efi_boot_dir = target_mount / "efi" / "boot"
        bootx64 = efi_boot_dir / BOOTX64_EFI_FILENAME

        if not bootx64.is_file():
            possible_loader = target_mount / "efi" / "microsoft" / "boot" / BOOTMGFW_EFI_FILENAME
            if possible_loader.is_file():
                self.emit_log(
                    f"Copiando {BOOTMGFW_EFI_FILENAME} para /efi/boot/{BOOTX64_EFI_FILENAME} para compatibilidade UEFI..."
                )
                efi_boot_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(possible_loader, bootx64)
            else:
                self.emit_log(
                    f"Aviso: /efi/boot/{BOOTX64_EFI_FILENAME} não encontrado na mídia. Bootloader legado pode ser necessário."
                )
        else:
            self.emit_log(
                f"Bootloader UEFI verificado com sucesso: /efi/boot/{BOOTX64_EFI_FILENAME} presente."
            )

    def _cleanup_mount(self, mount_dir: Path) -> None:
        """Unmounts the temporary mount directory."""
        if find_binary("udisksctl"):
            subprocess.run(["udisksctl", "unmount", "-m", str(mount_dir)], check=False)
        elif find_binary("gdbus") and self._target_part:
            part_name = Path(self._target_part).name
            subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--system",
                    "--dest",
                    DBUS_UDISKS2_DEST,
                    "--object-path",
                    f"{DBUS_UDISKS2_BLOCK_PATH}/{part_name}",
                    "--method",
                    "org.freedesktop.UDisks2.Filesystem.Unmount",
                    "{}",
                ],
                check=False,
            )
        else:
            subprocess.run(["umount", str(mount_dir)], check=False)
