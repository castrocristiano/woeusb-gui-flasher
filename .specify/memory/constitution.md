# WoeUSB-GUI Constitution

## Core Principles

### I. Safety & Non-Destructive Protection (NON-NEGOTIABLE)
- Disk writing operations are inherently destructive. The application MUST strictly safeguard internal drives, root partitions, EFI system partitions, and mounted operating system volumes from accidental formatting or overwriting.
- Device discovery must filter by removable USB media (`TRAN=usb` / `RM=true`) by default.
- Any destructive operation requires explicit user confirmation, clearly displaying the target device path, vendor/model, size, and existing labels.

### II. Universal Linux Execution via Flatpak
- The application MUST run seamlessly on any Linux distribution through **Flatpak** (`org.woeusb.WoeUsbGui`).
- To operate within Flatpak's unprivileged sandbox:
  - Low-level disk formatting and partition operations are mediated through the standard host D-Bus daemon `org.freedesktop.UDisks2` (with Polkit authentication).
  - ISO handling is performed in user-space (using bundled `7z` / archive extraction and `wimlib-imagex`) directly into the mounted filesystem, eliminating any dependency on kernel loop devices (`mount -o loop`).
  - Fallback execution on the host (`flatpak-spawn --host`) is supported when native host CLI execution is selected.

### III. Responsive & Asynchronous Architecture
- The GUI MUST NEVER block or freeze during disk operations, ISO scanning, or command execution.
- All disk enumeration, ISO inspection, and write processes must run in dedicated background worker threads (`QThread` / `QProcess`).
- Clean process lifecycle management: canceling or closing the application must safely interrupt operations and trigger cleanup of temporary resources.

### IV. Observability & User Feedback
- Real-time stream parsing: provide smooth percentage updates (`0-100%`), operation stage indicators (formatting, copying, splitting WIM, configuring bootloader), and elapsed time.
- Integrated log drawer: provide accessible, readable, and copyable execution logs for troubleshooting.

### V. Native Linux Desktop Integration
- Built using **Python 3** and **PySide6 (Qt 6)** with the KDE / Freedesktop Flatpak runtime, providing native Wayland/X11 rendering and automatic dark/light theme adaptation across all distributions.
- Compliant `.desktop` launcher and SVG app icon.

## Technology Stack & Constraints
- **Language**: Python 3 (3.11+)
- **GUI Framework**: PySide6 (Qt 6)
- **Packaging**: Flatpak (`org.woeusb.WoeUsbGui`)
- **Flatpak Runtime**: `org.kde.Platform` (6.x) or `org.freedesktop.Platform` (24.08)
- **Disk Daemon**: `org.freedesktop.UDisks2` over D-Bus
- **User-space Tools**: `wimlib-imagex`, `7z` (p7zip)

## Governance
This Constitution establishes the foundational principles for WoeUSB-GUI. All feature specifications, architecture plans, and task breakdowns must adhere to these tenets.

**Version**: 1.1.0 | **Ratified**: 2026-10-10 | **Last Amended**: 2026-10-10
