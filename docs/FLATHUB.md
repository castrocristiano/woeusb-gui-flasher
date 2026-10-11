# Flathub Packaging & Quality Guidelines

This document details the Flatpak packaging architecture, sandboxing model, and Flathub Quality Guidelines compliance for **WoeUSB-GUI** (`org.woeusb.WoeUsbGui`).

---

## 1. Application Identity & Metadata

- **Application ID**: `org.woeusb.WoeUsbGui`
- **Component Type**: `desktop-application`
- **Metadata License**: `CC0-1.0` (Permissive as required by AppStream and Flathub)
- **Project License**: `GPL-3.0-or-later` (Valid SPDX identifier)
- **Runtime**: `org.kde.Platform` (Branch: `6.6` or later, providing Qt 6 and PySide6 support)
- **SDK**: `org.kde.Sdk`
- **Desktop Entry**: `/app/share/applications/org.woeusb.WoeUsbGui.desktop`
- **Icon**: `/app/share/icons/hicolor/scalable/apps/org.woeusb.WoeUsbGui.svg`
- **MetaInfo**: `/app/share/metainfo/org.woeusb.WoeUsbGui.metainfo.xml`

---

## 2. Sandbox Permissions & Security Rationale

Flathub reviewers review every permission requested under `finish-args`. Below is the technical justification for each entitlement:

| Permission | Scope | Technical Justification |
| :--- | :--- | :--- |
| `--system-talk-name=org.freedesktop.UDisks2` | D-Bus (System Bus) | Allows the unprivileged Flatpak application to communicate with the host's UDisks2 daemon to safely enumerate removable USB drives, query block device topology, unmount, format (FAT32/NTFS), and mount target partitions without needing root/sudo privileges or device-node access. |
| `--filesystem=/run/media:rw` | Host Filesystem | Mount points created by UDisks2 on modern Linux distributions (Arch, Fedora, Ubuntu, Debian, BigLinux, Manjaro) are placed under `/run/media/$USER/<LABEL>`. Read/write access is required to copy extracted Windows installation files to the mounted target USB drive. |
| `--filesystem=host:ro` | Host Filesystem | Allows the user to browse and select Windows `.iso` disk images stored anywhere on their system (e.g., `~/Downloads`, secondary drives, or network shares). |
| `--share=ipc` | IPC | Required for X11 shared memory extension and performant GUI communication. |
| `--socket=wayland` | Display | Native Wayland window display on modern Wayland desktop sessions (GNOME, KDE Plasma, Sway). |
| `--socket=fallback-x11` | Display | Fallback display support for X11 desktop sessions. |
| `--device=dri` | GPU | Hardware acceleration for Qt 6 / PySide6 rendering. |
| `--talk-name=org.freedesktop.Flatpak` | D-Bus (Session Bus) | Interacts with Flatpak portal for sandboxed desktop integration. |

> [!NOTE]
> The application intentionally **does not** request `--device=all`, `--filesystem=host:rw`, or privileged device node access (`/dev/*`). All disk writes are performed through standard filesystem mount points or managed through UDisks2.

---

## 3. Flathub Quality Guidelines Checklist

WoeUSB-GUI satisfies the requirements set forth in the [Flathub Quality Guidelines](https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/):

- [x] **AppStream Specification 1.0 Compliance**:
  - File located in standard path: `/app/share/metainfo/org.woeusb.WoeUsbGui.metainfo.xml`.
  - Exactly matching `<id>` and `<launchable>` tags.
  - Required URLs included: `<url type="homepage">`, `<url type="bugtracker">`, `<url type="vcs-browser">`, `<url type="help">`.
  - Structured `<description>` containing explanatory paragraphs and bullet points.
  - Concise summary (<= 35 characters ideal, no ending period).
- [x] **Branding Colors**:
  - Defines `<branding>` with `#0078d4` (light) and `#106ebe` (dark) brand colors for Flathub banner curation.
- [x] **Visual Assets**:
  - Valid scalable vector SVG icon at 128x128 / scalable canvas.
  - Screenshots specified with `<screenshots>`, including direct raw source URLs and descriptive captions.
- [x] **Release Notes**:
  - Includes structured `<releases>` with semantic version, ISO-8601 release date, and detailed release highlights.
- [x] **OARS Content Rating**:
  - Includes `<content_rating type="oars-1.1" />`.
- [x] **Developer Identity**:
  - Includes `<developer id="...">` with maintainer name.
- [x] **Desktop Entry Standards**:
  - Strictly follows FreeDesktop.org Desktop Entry Specification.
  - Verified with zero warnings via `desktop-file-validate`.
  - Single main category (`Utility;`) plus valid subcategories (`Archiving;Qt;`).

---

## 4. Local Build & Validation

### 4.1 Prerequisites

Ensure Flatpak development tools are installed on your system:

```bash
# Arch Linux / Manjaro
sudo pacman -S flatpak flatpak-builder appstream

# Fedora
sudo dnf install flatpak flatpak-builder appstream

# Ubuntu / Debian
sudo apt install flatpak flatpak-builder appstream
```

Install the KDE 6.6 Platform and SDK runtimes:

```bash
flatpak install flathub org.kde.Platform//6.6 org.kde.Sdk//6.6
```

### 4.2 Building and Installing Locally

Compile and install the application locally into your user Flatpak repository:

```bash
flatpak-builder --force-clean --user --install build-dir org.woeusb.WoeUsbGui.yml
```

Run the installed Flatpak application:

```bash
flatpak run org.woeusb.WoeUsbGui
```

### 4.3 Metadata Validation

Validate the desktop entry and AppStream metadata:

```bash
# Validate Desktop entry
desktop-file-validate assets/org.woeusb.WoeUsbGui.desktop

# Validate AppStream MetaInfo (pedantic mode)
appstreamcli validate --no-net --pedantic assets/org.woeusb.WoeUsbGui.metainfo.xml
```

Both tools must complete with exit code `0` and no fatal errors.

---

## 5. Submitting to Flathub

When submitting WoeUSB-GUI to Flathub:

1. **Fork the Flathub Repository**:
   Fork [flathub/flathub](https://github.com/flathub/flathub) on GitHub.

2. **Create a Dedicated Branch**:
   ```bash
   git checkout -b add-org.woeusb.WoeUsbGui
   ```

3. **Add Manifest & Sources**:
   - Place `org.woeusb.WoeUsbGui.yml` in the repository root.
   - Ensure the module sources point to a permanent release tag/archive and include accurate `sha256` checksums.

5. **Verify with flatpak-builder-lint**:
   ```bash
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest org.woeusb.WoeUsbGui.yml
   ```

6. **Open Pull Request (Human Maintainer Only)**:
   - Open a pull request against `flathub/flathub:new-pr`.
   - Provide the permissions rationale and AI disclosure (see Section 6 below).

---

## 6. Flathub Generative AI Policy Compliance

Flathub enforces a strict [Generative AI Policy](https://docs.flathub.org/docs/for-app-authors/requirements/) to protect code quality, security, and repository integrity. It is essential to comply with all aspects of this policy to avoid submission rejection or maintainer account suspension:

### 6.1 Policy Rules Summary

1. **Mandatory Disclosure**:
   - Any AI-generated code, documentation, or packaging material in the upstream repository must be explicitly disclosed.
   - The disclosure must clearly identify the affected components and the approximate extent of AI usage.
   - Undisclosed or misrepresented AI usage is grounds for immediate rejection and potential permanent bans.

2. **Strict Manifest Ban**:
   - Flathub manifests **must not** contain AI-generated or AI-assisted content. Disclosure does *not* exempt manifests from this rule.
   - The Flatpak manifest (`org.woeusb.WoeUsbGui.yml`) must be reviewed, verified, tested, and curated by human developers.

3. **Strict Ban on AI in Submission & Review Interactions**:
   - AI tools, agents, or bots are strictly **prohibited** from:
     - Opening or automating pull requests on Flathub repositories.
     - Generating commit messages, PR descriptions, or PR updates on Flathub.
     - Generating review comments, responses, or discussion replies to Flathub maintainers.
     - Requesting "AI-agent reviews" on pull requests.
   - **All interactions on the Flathub pull request must be performed directly and manually by the human maintainer.**

### 6.2 Required Flathub PR Disclosure Template

When opening the pull request on `flathub/flathub`, include an explicit disclosure in the PR description:

```markdown
### Generative AI Disclosure
In compliance with Flathub's Generative AI policy:
- **Upstream Application Code & Documentation**: The codebase was developed with the assistance of Generative AI (used for code scaffolding, refactoring, and test authoring under human architectural direction, safety verification, and review).
- **Flatpak Manifest**: The manifest (`org.woeusb.WoeUsbGui.yml`) has been independently reviewed, tested locally with `flatpak-builder`, and curated directly by the human maintainer.
- **Pull Request & Communications**: This submission, commit messages, and all ongoing discussion/review responses are conducted manually and directly by the human maintainer without automated AI agents.
```

