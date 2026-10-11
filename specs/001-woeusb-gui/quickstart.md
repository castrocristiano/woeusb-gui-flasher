# Quickstart & Validation Guide: WoeUSB GUI Flasher

**Feature**: WoeUSB GUI Flasher (`001-woeusb-gui`)  
**Status**: Ready for Validation  
**Date**: 2026-10-10  

---

## 1. Prerequisites

### Local Development Environment
- Python 3.11+ (Python 3.12 recommended)
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- System packages (for running from source):
  - Ubuntu/Debian: `sudo apt install p7zip-full wimtools udisks2 libgl1`
  - Fedora: `sudo dnf install p7zip p7zip-plugins wimlib-utils udisks2`
  - Arch: `sudo pacman -S p7zip wimlib udisks2`

### Flatpak Testing Environment (Optional / Packaging Validation)
- `flatpak` and `flatpak-builder`
- SDK/Platform: `flatpak install flathub org.kde.Platform//6.6 org.kde.Sdk//6.6` (or `org.freedesktop.Platform//24.08`)

---

## 2. Setup & Installation

Clone and initialize the Python development environment:

```bash
# Clone the repository
git clone https://github.com/castrocristiano/woeusb-gui-flasher.git
cd woeusb-gui-flasher

# Sync dependencies with uv
uv sync
```

---

## 3. Running Validation Tests

### 3.1 Unit & Contract Tests
Run the automated test suite with coverage:

```bash
uv run pytest -v
```

**Expected Outcome**:
All tests pass with exit code `0`.

---

## 4. End-to-End Validation Scenarios

### Scenario 1: Non-Destructive Drive Detection
1. Connect a USB thumb drive (>= 8 GB).
2. Launch the application:
   ```bash
   uv run woeusb-gui
   ```
3. Observe the **Target Drive** dropdown.
4. **Validation Check**:
   - The USB thumb drive appears in the list with capacity, vendor, and device node.
   - Internal NVMe/SATA drives (`/dev/nvme0n1`, `/dev/sda` containing root `/`) DO NOT appear anywhere in the dropdown.
   - Unplugging the USB drive and clicking "Recarregar Dispositivos" immediately removes the device from the list.

### Scenario 2: ISO Inspection & WIM Split Detection
1. Click "Procurar..." and select a Windows 10/11 `.iso` image.
2. **Validation Check**:
   - The application parses the image metadata in user space.
   - Displays ISO name, formatted size (e.g. `5.23 GB`).
   - If `install.wim` > 4 GB, a badge/indicator shows that automatic WIM splitting will be applied for FAT32 compatibility.

### Scenario 3: Execution Simulation / Mock Dry-Run
Run the mock verification script to validate progress signals, state transitions, and cancellation without formatting real hardware:

```bash
uv run python -m woeusb_gui_flasher.burn_engine --dry-run
```

**Expected Outcome**:
Transitions cleanly through all states:
`IDLE -> VALIDATING -> UNMOUNTING -> FORMATTING -> EXTRACTING_ISO -> SPLITTING_WIM -> FINALIZING -> COMPLETED`.

---

## 5. Flatpak Build Verification

To verify that the application builds and bundles cleanly inside the Flatpak sandbox:

```bash
# Build the flatpak into a temporary build dir
flatpak-builder --user --install --force-clean build-dir org.woeusb.WoeUsbGui.yml

# Run the flatpak container
flatpak run org.woeusb.WoeUsbGui
```

**Validation Check**:
The Qt 6 application opens seamlessly on both Wayland and X11 sessions, connects to host `UDisks2`, and enumerates USB devices.

