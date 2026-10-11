# Contributing to WoeUSB-GUI

Thank you for your interest in contributing to **WoeUSB-GUI**! This project welcomes bug reports, feature suggestions, localization, and pull requests.

---

## Code of Conduct & Development Principles

- **Safety First**: Disk operations must NEVER touch non-removable or system storage devices. Every code change dealing with device discovery or disk actions must maintain strict filters protecting user data.
- **Flathub & Sandbox Compatibility**: Any new feature or external dependency must function correctly within the Flatpak unprivileged sandbox.
- **Multi-threaded Architecture**: Keep GUI responsive at all times. Long-running tasks (ISO extraction, WIM splitting, formatting) must run in `BurnWorker` (`QThread`), communicating strictly via Qt signals.

---

## Getting Started

### Local Development Setup

1. **Prerequisites**:
   - Python 3.11+
   - `uv` (recommended) or `pip`
   - `p7zip` (`7z`), `wimlib`, `udisks2`, `dosfstools`

2. **Clone and Install**:
   ```bash
   git clone https://github.com/castrocristiano/woeusb-gui-flasher.git
   cd woeusb-gui-flasher
   uv sync
   ```

3. **Running the Application**:
   ```bash
   uv run woeusb-gui
   # or using the launcher script:
   ./run.sh
   ```

---

## Running Tests & Quality Checks

Run the automated test suite before opening a pull request:

```bash
# Run pytest in offscreen mode
uv run pytest

# Check code formatting with ruff
uv run ruff check .
```

Verify AppStream and Desktop metadata:

```bash
# Validate Desktop entry
desktop-file-validate assets/org.woeusb.WoeUsbGui.desktop

# Validate AppStream MetaInfo
appstreamcli validate --no-net --pedantic assets/org.woeusb.WoeUsbGui.metainfo.xml
```

---

## Submitting Pull Requests

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes and commit with descriptive messages.
3. Ensure all tests and validation checks pass.
4. Push to your fork and submit a Pull Request with a clear description of the problem and solution.

---

## Generative AI Contribution Policy

In alignment with [Flathub's Generative AI Policy](https://docs.flathub.org/docs/for-app-authors/requirements/):

- **Disclosure**: If you used Generative AI to assist in writing code, tests, or documentation, disclose this in your pull request description along with the components affected.
- **Human Verification**: All AI-assisted contributions must be verified, audited, and tested by you before submission. Automated unchecked AI code will be rejected.
- **Packaging Manifests**: Flatpak manifests (`org.woeusb.WoeUsbGui.yml`) must not contain AI-generated content. All manifest changes must be authored, tested, and validated by human contributors.

