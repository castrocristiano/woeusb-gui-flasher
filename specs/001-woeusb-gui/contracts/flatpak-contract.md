# Interface Contract: Flatpak Packaging & Sandbox Configuration

**Feature**: WoeUSB GUI Flasher (`001-woeusb-gui`)  
**Application ID**: `org.woeusb.WoeUsbGui`  
**Manifest Format**: YAML / JSON (`flatpak-builder` specification)  

---

## 1. Application Identity

- **App ID**: `org.woeusb.WoeUsbGui`
- **Runtime**: `org.kde.Platform` or `org.freedesktop.Platform`
- **Runtime Version**: `6.6` (KDE) or `24.08` (Freedesktop)
- **SDK**: `org.kde.Sdk` or `org.freedesktop.Sdk`
- **Command**: `woeusb-gui`

---

## 2. Finish Args (Sandbox Permissions)

| Flag | Purpose | Invariant |
| :--- | :--- | :--- |
| `--socket=wayland` | Native Wayland desktop display server connection | Required for modern Linux desktops (Fedora, BigLinux, Ubuntu 24.04+) |
| `--socket=fallback-x11` | X11 display server fallback | Required when Wayland is not active |
| `--share=ipc` | Shared memory IPC | Smooth Qt 6 rendering performance |
| `--device=dri` | Direct Rendering Infrastructure | Hardware GPU acceleration |
| `--filesystem=host:ro` | Read-only access to host filesystem | Allows selecting ISO files anywhere on user mounts |
| `--filesystem=/run/media:rw` | Read-write access to `/run/media` | Enables reading/writing directly to UDisks2 mounted USB sticks |
| `--system-talk-name=org.freedesktop.UDisks2` | D-Bus access to host UDisks2 service | Enables secure disk discovery, unmounting, formatting, and mounting |
| `--talk-name=org.freedesktop.Flatpak` | Flatpak portal communication | Optional host command fallback (`flatpak-spawn --host`) |

---

## 3. Bundled Modules

1. **`wimlib`**:
   - Source: `https://wimlib.net/downloads/wimlib-1.14.5.tar.gz`
   - Buildsystem: `autotools`
   - Config options: `--without-fuse`, `--without-ntfs-3g`
   - Target binary: `/app/bin/wimlib-imagex`

2. **`p7zip`** (or modern `7zip`):
   - Buildsystem: `generic`
   - Target binary: `/app/bin/7z`

3. **`woeusb-gui`**:
   - Python code installed to `/app/lib/python3.11/site-packages/woeusb_gui_flasher`
   - Launcher executable installed to `/app/bin/woeusb-gui`
   - Desktop entry installed to `/app/share/applications/org.woeusb.WoeUsbGui.desktop`
   - Icon installed to `/app/share/icons/hicolor/scalable/apps/org.woeusb.WoeUsbGui.svg`
   - AppStream metainfo installed to `/app/share/metainfo/org.woeusb.WoeUsbGui.metainfo.xml`

