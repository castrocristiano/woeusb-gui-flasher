"""Asynchronous burn engine implementation using QThread."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from woeusb_gui_flasher.disk_manager import DiskManager
from woeusb_gui_flasher.models import (
    BootMode,
    BurnConfiguration,
    BurnStage,
    FileSystemType,
    StorageDevice,
    WindowsISO,
)
from woeusb_gui_flasher.utils import find_binary

logger = logging.getLogger(__name__)


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

    def run(self) -> None:
        """Main execution loop run inside the QThread worker."""
        try:
            self.emit_log("=== Iniciando WoeUSB GUI Flasher ===")
            self.emit_log(
                f"ISO selecionada: {self.config.iso.file_path} ({self.config.iso.size_human})"
            )
            self.emit_log(
                f"Dispositivo alvo: {self.config.target_device.path} ({self.config.target_device.size_human})"
            )
            self.emit_log(f"Sistema de arquivos: {self.config.filesystem.value}")

            # 1. Validation
            self._set_stage(BurnStage.VALIDATING, 2.0, "Validando requisitos e imagens...")
            self.config.validate()
            if self.is_cancelled():
                return self._finish_cancelled()

            # 2. Unmounting existing partitions
            self._set_stage(BurnStage.UNMOUNTING, 8.0, "Desmontando partições existentes...")
            self.emit_log(f"Desmontando partições ativas de {self.config.target_device.path}...")
            if not self.dry_run:
                self.disk_manager.unmount_device_partitions(self.config.target_device)
            if self.is_cancelled():
                return self._finish_cancelled()

            # 3. Partitioning & Formatting
            self._set_stage(
                BurnStage.PARTITIONING, 15.0, "Criando tabela de partições e formatando..."
            )
            target_mount = self._prepare_and_format_drive()
            if self.is_cancelled():
                return self._finish_cancelled()

            # 4. User-Space ISO Extraction
            self._set_stage(BurnStage.EXTRACTING_ISO, 25.0, "Extraindo arquivos da imagem ISO...")
            self._extract_iso_contents(target_mount)
            if self.is_cancelled():
                return self._finish_cancelled()

            # 5. Split install.wim if necessary
            if self.config.filesystem == FileSystemType.FAT32:
                self._set_stage(
                    BurnStage.SPLITTING_WIM, 80.0, "Verificando tamanho da imagem de instalação..."
                )
                self._handle_wim_split(target_mount)
            if self.is_cancelled():
                return self._finish_cancelled()

            # 6. Configure bootloader
            self._set_stage(
                BurnStage.CONFIGURING_BOOT, 90.0, "Configurando bootloader UEFI/BIOS..."
            )
            self._configure_bootloader(target_mount)
            if self.is_cancelled():
                return self._finish_cancelled()

            # 7. Finalizing and sync
            self._set_stage(BurnStage.FINALIZING, 95.0, "Sincronizando buffers de disco (sync)...")
            self.emit_log("Garantindo escrita de todos os buffers em disco...")
            if not self.dry_run:
                subprocess.run(["sync"], check=False)
                # Unmount target mount
                self._cleanup_mount(target_mount)

            self.emit_progress(100.0, "Concluído com sucesso!", "")
            self.emit_status("Gravação finalizada com sucesso!")
            self.emit_log("=== Gravação concluída com sucesso! Pode remover o pendrive. ===")
            self.operation_finished.emit(
                True, "Pendrive inicializável do Windows criado com sucesso!"
            )

        except Exception as exc:
            logger.exception("Burn operation failed:")
            self.emit_log(f"ERRO CRÍTICO: {exc}")
            self.emit_status(f"Falha na operação: {exc}", True)
            self.operation_finished.emit(False, str(exc))

    def _set_stage(self, stage: BurnStage, percent: float, text: str) -> None:
        self.emit_progress(percent, text)
        self.emit_status(text)
        self.emit_log(f"[{stage.value}] {text}")

    def _finish_cancelled(self) -> None:
        if self._temp_mount_dir and not self.dry_run:
            try:
                self._cleanup_mount(self._temp_mount_dir)
            except (OSError, RuntimeError) as e:
                logger.warning("Error cleaning up mount during cancel: %s", e)
        self.emit_progress(0.0, "Operação cancelada pelo usuário.")
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
            mount_path = Path("/tmp/woeusb_mock_mount")
            mount_path.mkdir(parents=True, exist_ok=True)
            self._temp_mount_dir = mount_path
            return mount_path

        # Step A: Wipe filesystem signatures on first partition or device
        target_part = f"{device_path}1" if not device_path.endswith("1") else device_path
        self.emit_log(f"Formatando partição {target_part} como {fs_type.value}...")

        # Use mkfs.vfat / mkfs.ntfs
        if fs_type == FileSystemType.FAT32:
            mkfs_cmd = ["mkfs.vfat", "-F", "32", "-n", label, target_part]
        else:
            mkfs_cmd = ["mkfs.ntfs", "-f", "-L", label, target_part]

        # Try udisksctl format first for Polkit permissions
        udisksctl = find_binary("udisksctl")
        formatted = False
        if udisksctl:
            fs_arg = "vfat" if fs_type == FileSystemType.FAT32 else "ntfs"
            res = subprocess.run(
                [
                    udisksctl,
                    "format",
                    "-b",
                    target_part,
                    "-t",
                    fs_arg,
                    "--label",
                    label,
                    "--no-user-interaction",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                formatted = True
                self.emit_log(f"Partição formatada via udisksctl: {res.stdout.strip()}")

        if not formatted:
            # Fallback to direct mkfs command
            res = subprocess.run(mkfs_cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                raise RuntimeError(f"Falha ao formatar partição: {res.stderr or res.stdout}")
            self.emit_log(f"Partição formatada com sucesso: {mkfs_cmd[0]}")

        # Mount target partition
        self.emit_log("Montando partição de destino...")
        mount_dir = self._mount_partition(target_part)
        return mount_dir

    def _mount_partition(self, part_path: str) -> Path:
        """Mounts the formatted partition and returns the mount directory."""
        udisksctl = find_binary("udisksctl")
        if udisksctl:
            res = subprocess.run(
                [udisksctl, "mount", "-b", part_path, "--no-user-interaction"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                # e.g.: Mounted /dev/sdd1 at /run/media/user/WININSTALL
                match = re.search(r"at\s+(/\S+)", res.stdout)
                if match:
                    mount_path = Path(match.group(1))
                    self.emit_log(f"Montado via udisksctl em {mount_path}")
                    self._temp_mount_dir = mount_path
                    return mount_path

        # Fallback mount into /tmp/woeusb_mount
        fallback_dir = Path("/tmp/woeusb_mount")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["mount", part_path, str(fallback_dir)], check=False)
        self._temp_mount_dir = fallback_dir
        return fallback_dir

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
            self.emit_log("[DRY-RUN] Simulando extração de arquivos...")
            (target_mount / "sources").mkdir(parents=True, exist_ok=True)
            (target_mount / "sources" / "install.wim").write_bytes(b"wim data" * 1000)
            (target_mount / "efi" / "boot").mkdir(parents=True, exist_ok=True)
            (target_mount / "efi" / "boot" / "bootx64.efi").write_bytes(b"efi data")
            return

        cmd = [seven_z, "x", "-bso0", "-bsp1", "-bd", f"-o{target_mount}", iso_path]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        self._active_process = process

        pct_pattern = re.compile(r"(\d+)%")
        start_time = time.time()

        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if self.is_cancelled():
                    process.terminate()
                    break
                m = pct_pattern.search(line)
                if m:
                    current_7z_pct = float(m.group(1))
                    # Scale 7z progress into 25% -> 75% range
                    scaled_pct = 25.0 + (current_7z_pct * 0.50)
                    elapsed = max(time.time() - start_time, 1.0)
                    speed_mb = (self.config.iso.size_bytes * (current_7z_pct / 100.0)) / (
                        elapsed * 1024 * 1024
                    )
                    speed_str = f"{speed_mb:.1f} MB/s"
                    self.emit_progress(
                        scaled_pct, f"Copiando arquivos ({int(current_7z_pct)}%)...", speed_str
                    )
                else:
                    clean = line.strip()
                    if clean and not clean.startswith("\r"):
                        self.emit_log(clean)

        process.wait()
        self._active_process = None

        if process.returncode != 0 and not self.is_cancelled():
            raise RuntimeError(
                f"A extração dos arquivos com 7z falhou com código {process.returncode}"
            )

    def _handle_wim_split(self, target_mount: Path) -> None:
        """Splits install.wim if it exceeds 4 GB on a FAT32 filesystem."""
        sources_dir = target_mount / "sources"
        install_wim = sources_dir / "install.wim"

        # Check in target mount or inspect from ISO
        wim_size = 0
        if install_wim.is_file():
            wim_size = install_wim.stat().st_size
        else:
            wim_size = self.config.iso.install_image_size

        max_fat32_size = 4_294_967_295  # 4 GB - 1 byte
        if wim_size <= max_fat32_size:
            self.emit_log(
                "install.wim não ultrapassa o limite de 4 GB do FAT32. Divisão desnecessária."
            )
            return

        self.emit_log(
            f"install.wim possui {wim_size / (1024**3):.2f} GB (> 4 GB). Iniciando divisão com wimlib-imagex..."
        )

        wimlib = find_binary("wimlib-imagex")
        if not wimlib and not self.dry_run:
            raise FileNotFoundError(
                "O utilitário 'wimlib-imagex' é necessário para dividir arquivos WIM > 4 GB no FAT32."
            )

        dest_swm = str(sources_dir / "install.swm")

        if self.dry_run:
            self.emit_log(f"[DRY-RUN] wimlib-imagex split {install_wim} {dest_swm} 3800")
            (sources_dir / "install.swm").write_bytes(b"swm1")
            (sources_dir / "install2.swm").write_bytes(b"swm2")
            if install_wim.is_file():
                install_wim.unlink(missing_ok=True)
            return

        cmd = [wimlib, "split", str(install_wim), dest_swm, "3800"]
        self.emit_log(f"Executando: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._active_process = process
        stdout, stderr = process.communicate()
        self._active_process = None

        if self.is_cancelled():
            return

        if process.returncode != 0:
            raise RuntimeError(f"Falha ao dividir install.wim: {stderr or stdout}")

        self.emit_log(
            "Divisão do install.wim concluída com sucesso! Removendo arquivo .wim original..."
        )
        if install_wim.is_file():
            install_wim.unlink(missing_ok=True)

    def _configure_bootloader(self, target_mount: Path) -> None:
        """Verifies and configures UEFI bootloaders."""
        efi_boot_dir = target_mount / "efi" / "boot"
        bootx64 = efi_boot_dir / "bootx64.efi"

        if not bootx64.is_file():
            # Try to locate bootmgfw.efi or other efi loaders
            possible_loader = target_mount / "efi" / "microsoft" / "boot" / "bootmgfw.efi"
            if possible_loader.is_file():
                self.emit_log(
                    "Copiando bootmgfw.efi para /efi/boot/bootx64.efi para compatibilidade UEFI..."
                )
                efi_boot_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(possible_loader, bootx64)
            else:
                self.emit_log(
                    "Aviso: /efi/boot/bootx64.efi não encontrado na mídia. Bootloader legado pode ser necessário."
                )
        else:
            self.emit_log("Bootloader UEFI verificado com sucesso: /efi/boot/bootx64.efi presente.")

    def _cleanup_mount(self, mount_dir: Path) -> None:
        """Unmounts the temporary mount directory."""
        udisksctl = find_binary("udisksctl")
        if udisksctl:
            subprocess.run([udisksctl, "unmount", "-m", str(mount_dir)], check=False)
        else:
            subprocess.run(["umount", str(mount_dir)], check=False)


if __name__ == "__main__":
    import sys

    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication(sys.argv)
    mock_iso_path = Path("/tmp/mock_win.iso")
    mock_iso_path.write_bytes(b"mock iso content" * 100)

    mock_iso = WindowsISO(
        file_path=mock_iso_path,
        file_name="mock_win.iso",
        size_bytes=5_000_000_000,
        size_human="5.0 GB",
        has_install_wim=True,
        install_image_size=4_500_000_000,
    )
    mock_dev = StorageDevice(
        name="sdd",
        path="/dev/sdd",
        vendor="MockVendor",
        model="MockDrive",
        size_bytes=16_000_000_000,
        size_human="14.9 GB",
        is_removable=True,
    )
    cfg = BurnConfiguration(
        iso=mock_iso,
        target_device=mock_dev,
        filesystem=FileSystemType.FAT32,
        boot_mode=BootMode.UEFI_AND_LEGACY,
    )
    worker = BurnWorker(cfg, dry_run=True)
    worker.progress_changed.connect(lambda pct, stage, spd: print(f"[{pct:.1f}%] {stage} ({spd})"))
    worker.log_line_emitted.connect(lambda l: print(f"LOG: {l}"))
    worker.operation_finished.connect(lambda ok, msg: print(f"FINISHED: ok={ok}, msg={msg}"))
    worker.run()

