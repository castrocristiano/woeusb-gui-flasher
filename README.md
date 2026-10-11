# WoeUSB-GUI (Windows Bootable USB Flasher)

A modern, reliable Linux desktop application built with Python and **PySide6 / Qt 6** for creating bootable Windows installation USB drives from official ISO disk images. Designed for all major Linux distributions (Arch Linux, Fedora, Ubuntu, Debian, BigLinux, Manjaro) and universally packaged via **Flatpak** (`org.woeusb.WoeUsbGui`).

[![Flathub](https://img.shields.io/badge/Flathub-org.woeusb.WoeUsbGui-blue?logo=flathub)](https://flathub.org/apps/org.woeusb.WoeUsbGui)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Python: >=3.11](https://img.shields.io/badge/Python->=3.11-green.svg)
![Qt: 6 (PySide6)](https://img.shields.io/badge/Qt-6-green.svg)
![AppStream: Validated](https://img.shields.io/badge/AppStream-Validated-brightgreen.svg)

🌐 **Language**: **English** | [Português (Brasil)](README.pt-BR.md)

---

## 📸 Interface

![WoeUSB-GUI Main Interface](assets/screenshots/main-window.png)

---

## ✨ Key Features

- **Strict Data Protection & Drive Safety**:
  - Device enumeration powered by D-Bus `UDisks2` and `lsblk`.
  - Filters and displays **only** removable USB drives with capacity $\ge$ 2 GB.
  - Automatically hides and protects all internal storage drives, system partitions (`/`, `/boot`, `/home`), and swap devices.
  - Mandatory confirmation modal showing device vendor, model, capacity, and path before formatting.
- **Unprivileged User-Space ISO Extraction**:
  - Direct ISO extraction utilizing `7z` (`p7zip`), eliminating risky elevated loop mounts (`mount -o loop`).
- **Automatic UEFI Secure Boot Compatibility (FAT32)**:
  - Formats drives to FAT32 with standard UEFI bootloader structure (`/efi/boot/bootx64.efi`).
  - Automatically splits `install.wim` files larger than 4 GB into `.swm` chunks via `wimlib-imagex split`, overcoming the FAT32 single-file size barrier seamlessly.
- **Modern & Responsive Qt 6 GUI**:
  - Fully asynchronous operation via background `QThread` workers, maintaining smooth 60 FPS UI responsiveness.
  - Real-time progress bar, phase indicators, and transfer speed estimation.
  - Expandable detailed log drawer with one-click clipboard copying.
  - Safe task cancellation with clean process termination and unmounting.
- **Flathub Quality Compliant**:
  - Strict sandboxing adhering to Flathub Quality Guidelines.
  - Wayland-native with X11 fallback and hardware-accelerated rendering.

---

## 🚀 Installation & Usage

### 1. Install via Flathub (Recommended)

Once published on Flathub, install and launch WoeUSB-GUI using:

```bash
# Install from Flathub
flatpak install flathub org.woeusb.WoeUsbGui

# Run the application
flatpak run org.woeusb.WoeUsbGui
```

### 2. Building and Testing with Flatpak Locally

WoeUSB-GUI uses the KDE 6.6 runtime (`org.kde.Platform`), which provides full PySide6 and Qt 6 support:

```bash
# 1. Install required KDE 6.6 runtime and SDK
flatpak install flathub org.kde.Platform//6.6 org.kde.Sdk//6.6

# 2. Build and install into local user repository
flatpak-builder --force-clean --user --install build-dir org.woeusb.WoeUsbGui.yml

# 3. Launch the installed Flatpak
flatpak run org.woeusb.WoeUsbGui
```

### 3. Running from Source (Development)

#### Prerequisites:
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (or `venv` + `pip`)
- System dependencies: `p7zip` (`7z`), `wimlib`, `dosfstools` (`mkfs.vfat`), `udisks2`

```bash
# Clone the repository
git clone https://github.com/castrocristiano/woeusb-gui-flasher.git
cd woeusb-gui-flasher

# Sync dependencies using uv
uv sync

# Launch the application
uv run woeusb-gui
# Or via the convenience launcher script:
./run.sh
```

---

## 🔒 Sandboxing & Security Permissions

To operate securely inside the Flatpak sandbox while managing USB storage, WoeUSB-GUI requires specific permissions:

| Permission | Reason |
| :--- | :--- |
| `--system-talk-name=org.freedesktop.UDisks2` | Enumerates removable drives, formats partitions, and handles mounts safely through the host's UDisks2 service without root privileges. |
| `--filesystem=/run/media:rw` | Writes extracted Windows installation files to USB mount points created by UDisks2. |
| `--filesystem=host:ro` | Allows the user to select Windows `.iso` images stored in their home directory, Downloads, or secondary disks. |
| `--socket=wayland` / `--socket=fallback-x11` | Provides graphical interface display on both modern Wayland and X11 desktop sessions. |
| `--device=dri` | Enables hardware-accelerated GUI rendering. |

For a comprehensive explanation of permissions and Flathub policies, see [docs/FLATHUB.md](docs/FLATHUB.md).

---

## 🧪 Testing & Validation

### Automated Test Suite

The project includes unit, contract, and UI tests using `pytest` and `pytest-qt`:

```bash
# Run tests in offscreen mode
uv run pytest

# Run tests with code coverage report
uv run pytest --cov=woeusb_gui_flasher
```

### AppStream & Desktop Metadata Validation

Validate metadata integrity against Freedesktop and Flathub quality specifications:

```bash
# Validate Desktop entry
desktop-file-validate assets/org.woeusb.WoeUsbGui.desktop

# Validate AppStream MetaInfo (pedantic mode)
appstreamcli validate --no-net --pedantic assets/org.woeusb.WoeUsbGui.metainfo.xml
```

---

## 📁 Repository Structure

```
woeusb-gui-flasher/
├── assets/
│   ├── org.woeusb.WoeUsbGui.desktop     # Desktop launcher integration
│   ├── org.woeusb.WoeUsbGui.metainfo.xml # AppStream / Flathub metadata
│   ├── org.woeusb.WoeUsbGui.svg         # Application vector icon
│   └── screenshots/
│       └── main-window.png              # UI screenshot for Flathub & AppStream
├── docs/
│   └── FLATHUB.md                       # Comprehensive Flathub packaging & review guide
├── specs/
│   └── 001-woeusb-gui/                  # Spec-Driven Development artifacts
├── src/
│   └── woeusb_gui_flasher/
│       ├── main.py                      # Application entry point
│       ├── models.py                    # Domain models and dataclasses
│       ├── utils.py                     # Byte formatting and subprocess helpers
│       ├── disk_manager.py              # Safe disk discovery via UDisks2/lsblk
│       ├── burn_engine.py               # Asynchronous burning worker (QThread)
│       └── ui/
│           ├── components.py            # Reusable UI widgets and cards
│           └── main_window.py           # Main window and confirmation modal
├── tests/                               # Comprehensive unit and UI test suite
├── CONTRIBUTING.md                      # Contribution guidelines
├── org.woeusb.WoeUsbGui.yml             # Flatpak build manifest
└── pyproject.toml                       # Python package configuration
```

---

## 🤝 Contributing

Contributions are welcome! Please check [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on code style, tests, and the pull request process.

---

## 🤖 Generative AI Disclosure

In full adherence to the [Flathub Generative AI Policy](https://docs.flathub.org/docs/for-app-authors/requirements/):

- **Application Code & Documentation**: Parts of the codebase, test suites, and documentation were drafted with the assistance of Generative AI tools (LLM coding assistants) under the direct supervision, architectural guidance, and review of the human author.
- **Human Verification & Safety**: All critical logic—particularly hardware drive enumeration safety filters, UDisks2 communication, and WIM splitting routines—has been audited, tested, and validated by the maintainer.
- **Flathub Manifest & Packaging**: The Flatpak manifest (`org.woeusb.WoeUsbGui.yml`) is curated, tested locally, and maintained by a human developer. In compliance with Flathub submission rules, all Flathub pull requests, commit messages, and review communications are conducted manually by human maintainers without automated bots.

---

## 📜 License

This project is licensed under the **GPL-3.0-or-later** license. See the [LICENSE](LICENSE) file for details. AppStream metadata is licensed under **CC0-1.0**.

