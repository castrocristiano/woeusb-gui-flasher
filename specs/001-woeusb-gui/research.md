# Research & Technical Decisions: WoeUSB GUI Flasher

**Feature**: WoeUSB GUI Flasher (`001-woeusb-gui`)  
**Status**: Completed  
**Date**: 2026-10-10  

---

## 1. D-Bus UDisks2 Communication & Device Safety

### Context
Writing to block devices (`/dev/sdX`) is an intrinsically destructive operation. In an unprivileged Flatpak container, raw device nodes in `/dev` are inaccessible without root privileges, and executing `sudo` or `pkexec` directly within the sandbox is restricted.

### Decision
Use the host system D-Bus daemon `org.freedesktop.UDisks2` via Python D-Bus bindings (`dasbus` or `Gio.DBusProxy`), supplemented by `lsblk -J -b` and `udisksctl` as a CLI fallback.

- **Enumeration**: Query `/org/freedesktop/UDisks2/block_devices/*` to extract partition and drive properties.
- **Safety Filtering**:
  - Only accept drives where `org.freedesktop.UDisks2.Drive.ConnectionBus == 'usb'` OR `Removable == true`.
  - Discard all devices where `HintSystem == true` or where child partitions are mounted on `/`, `/boot`, `/boot/efi`, `/home`, `[SWAP]`, or other core OS mount points.
  - Reject internal NVMe (`/dev/nvme*`) and internal SATA drives unless explicitly overridden in advanced settings with triple confirmation.
- **Partitioning & Formatting**:
  - Call `org.freedesktop.UDisks2.Block.Format()` with `type='vfat'` (or `ntfs`) and `label='WINDOWS_USB'`.
  - Polkit triggers the desktop native authentication dialog on the host (e.g. KDE PolicyKit / GNOME Shell agent) without exposing root credentials to the sandbox.

### Rationale
- Standard Freedesktop architecture supported out-of-the-box on 99% of modern Linux distributions.
- Polkit rules allow desktop users in active sessions to format removable USB drives without requiring full root password prompts on many desktop environments.
- Completely non-destructive: Impossible to format internal disks without matching USB removable filter.

### Alternatives Considered
- Direct `pkexec dd` / `pkexec mkfs`: Rejected because spawning `pkexec` directly inside Flatpak fails without complex `flatpak-spawn --host` pipelines, and bypasses Polkit's granular disk policy controls.
- Running GUI as root (`sudo woeusb-gui`): Strongly discouraged by Wayland and Qt guidelines; security risk.

---

## 2. ISO Inspection & User-Space Extraction

### Context
Standard Linux CLI tools (including original `woeusb` bash scripts) mount Windows ISOs using `mount -o loop -t udf <iso> <mountpoint>`. In Flatpak containers, `mount` syscall is blocked by the seccomp filter (`EPERM` / `CAP_SYS_ADMIN` required).

### Decision
Extract the Windows ISO in **user-space** using `7z` (from `p7zip`) or an ISO extractor library.
- Command: `7z x -bso0 -bsp1 -bd -o<target_mount> <iso_path>`
- Progress tracking: `7z` emits progress percentages via standard output (`-bsp1`) which is parsed in real time by `QProcess` or worker reader threads.

### Rationale
- `7z` parses UDF and ISO 9660 formats entirely in unprivileged user space.
- Works identical in Flatpak sandbox as on bare metal host.
- Zero kernel module or loopback device dependencies.

### Alternatives Considered
- `pycdlib`: Python library for ISO 9660 / UDF. Rejected because pure-Python extraction of 5+ GB images is significantly slower than native C/C++ `7z` and has limited support for UDF 2.60 used in modern Windows 11 ISOs.
- `fuseiso`: Requires `/dev/fuse` which requires extra Flatpak permissions (`--device=/dev/fuse`).

---

## 3. Handling Large WIM Files (> 4 GB) on FAT32 (Split WIM)

### Context
- FAT32 filesystems have an absolute maximum individual file size of 4,294,967,295 bytes (4 GB - 1 byte).
- Modern Windows 10 and Windows 11 installation images (`install.wim`) typically exceed 4.5 GB (often 5.2 GB to 6.0 GB).
- However, standard UEFI firmware natively only boots from FAT32 partitions (without special third-party NTFS UEFI drivers that break Secure Boot).

### Decision
Implement automatic WIM splitting using `wimlib-imagex`.
- When the target filesystem is FAT32 and `sources/install.wim` in the ISO exceeds 4 GB:
  1. The user-space ISO extraction selectively excludes or extracts `install.wim`.
  2. `wimlib-imagex split <install.wim> <target_mount>/sources/install.swm 3800` is invoked.
  3. `install.wim` is replaced by `install.swm`, `install2.swm`, etc. (each < 3.8 GB).
- Windows Setup and Windows PE natively support `.swm` split images without any registry or boot modifications.

### Rationale
- Retains 100% compatibility with standard UEFI Secure Boot (no need to disable Secure Boot in BIOS).
- `wimlib` is lightweight, fast, open-source (GPLv3), and readily compiled inside Flatpak.

### Alternatives Considered
- Formatting as NTFS exclusively: Requires UEFI NTFS driver (e.g. Rufus UEFI:NTFS or Ventoy), which prompts Secure Boot violation errors on modern OEM PCs unless user disables Secure Boot.
- Dual-partition scheme (FAT32 boot + NTFS data): Complex partition table that older BIOS systems or certain Windows installers fail to discover properly.

---

## 4. Asynchronous Architecture & Real-Time Progress

### Context
Disk formatting, 5+ GB file extractions, and WIM splits take anywhere from 3 to 15 minutes depending on USB flash drive write speed (typically 10-40 MB/s for USB 2.0 / 3.0). Any blocking call on the Qt GUI main thread causes the window manager to mark the window as "Not Responding" and freezes UI rendering.

### Decision
Use a dedicated `QThread` worker architecture (`BurnWorker`) decoupled via Qt Signals & Slots:
- Signals:
  - `progress_updated(percentage: int, stage_name: str, speed_str: str)`
  - `status_message(message: str)`
  - `log_emitted(line: str)`
  - `operation_finished(success: bool, error_message: str)`
- Lifecycle:
  - The worker maintains an abort flag (`self._abort_requested`).
  - Child processes (`7z`, `wimlib-imagex`, `sync`) are managed with clean termination (`SIGTERM` followed by graceful cleanup) upon user cancellation.

### Rationale
- Guarantees 60 FPS UI performance.
- Enables live log stream inspection and precise progress calculation.
- Clean resource deallocation upon cancellation.

---

## 5. Universal Flatpak Sandbox Integration

### Decision
Package the application with Flatpak ID `org.woeusb.WoeUsbGui` using the KDE / Qt 6 runtime (`org.kde.Platform` 6.6+ or `org.freedesktop.Platform` 24.08).
- Permissions:
  - `--socket=wayland` and `--socket=fallback-x11`: Native Wayland rendering with X11 fallback.
  - `--system-talk-name=org.freedesktop.UDisks2`: Direct D-Bus communication with host disk daemon.
  - `--filesystem=host:ro`: Read access to user ISO images wherever stored.
  - `--filesystem=/run/media:rw`: Write access to mounted removable media.
  - `--device=dri`: Hardware-accelerated GUI rendering.

---

## Summary of Architectural Choices

| Component | Choice | Reason |
| :--- | :--- | :--- |
| **GUI Framework** | PySide6 (Qt 6) | Native Wayland/KDE/GNOME look-and-feel, robust QThread model |
| **Disk Operations** | UDisks2 (D-Bus) | Polkit authentication on host, sandbox safe |
| **ISO Reader** | 7z (`p7zip`) | User-space extraction, no loop devices |
| **WIM Handling** | `wimlib-imagex` | Splits > 4 GB WIMs for FAT32 UEFI Secure Boot |
| **Packaging** | Flatpak | Universal installation across all Linux distributions |

