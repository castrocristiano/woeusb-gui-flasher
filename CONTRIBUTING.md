# Contributing to WoeUSB-GUI

Bug reports, feature ideas, translations and pull requests are welcome.

---

## Development Principles

- **Safety first**: disk operations must never reach non-removable or system disks. Changes to device discovery or disk actions must keep the safety filters (≥ 2 GB, removable only, system mounts hidden, large-drive filter, same-disk collision check) intact and tested.
- **Sandbox compatible**: features and dependencies must work inside the unprivileged Flatpak sandbox with the permissions listed in [docs/FLATHUB.md](docs/FLATHUB.md). Adding a `finish-args` permission needs a written justification.
- **Responsive UI**: long tasks (formatting, extraction, WIM splitting) run in `BurnWorker` (`QThread`) and talk to the UI only through Qt signals.

---

## Setup

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), and `p7zip`, `wimlib`, `udisks2`, `dosfstools`.

```bash
git clone https://github.com/castrocristiano/woeusb-gui-flasher.git
cd woeusb-gui-flasher
uv sync
uv run woeusb-gui   # or ./run.sh
```

---

## Checks (same as CI)

```bash
uv run ruff check .
uv run ruff format --check .
QT_QPA_PLATFORM=offscreen uv run pytest -v --cov=src --cov-report=xml:coverage.xml

desktop-file-validate assets/org.woeusb.WoeUsbGui.desktop
appstreamcli validate --no-net --pedantic assets/org.woeusb.WoeUsbGui.metainfo.xml
```

Optional SonarQube analysis: see the *SonarQube* section of the [README](README.md#sonarqube-optional-local).

---

## Workflow

### Branches
- `feature/<name>` (or `phase/<name>`) → PR into `develop`.
- CI on `develop` opens/updates the `develop → main` PR automatically.
- A merge into `main` creates a GitHub Release from the version in `pyproject.toml`.

### Specifications
New features follow Spec-Driven Development (spec-kit): each feature has a folder under `specs/NNN-name/` with `spec.md`, `plan.md`, `tasks.md`, contracts and a quickstart. Existing specs:
- `001-woeusb-gui` — core application
- `002-device-safety-filters` — large-drive filter and same-disk collision check

### Pull requests
1. Branch from `develop`.
2. Keep commits focused and descriptive.
3. Make sure all checks above pass.
4. Describe the problem, the solution and how you tested it.

---

## Generative AI Policy

This project is meant for Flathub, whose [requirements](https://docs.flathub.org/docs/for-app-authors/requirements) include a Generative AI policy:

- **Disclose** AI assistance in your PR description, naming the affected files and the extent.
- **Review and test** everything you submit; you must be able to explain it. Unreviewed generated code will be rejected.
- **Do not use AI to write or edit the Flatpak manifest** (`org.woeusb.WoeUsbGui.yml`). Manifest changes must be authored by a human.
- Never use AI tools or bots to interact with `flathub/flathub` (PRs, commits, comments, replies).
