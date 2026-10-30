# Flathub Packaging Guide

Packaging architecture, sandbox permissions, Flathub policy compliance and the remaining open items for **WoeUSB-GUI** (`org.woeusb.WoeUsbGui`).

> [!IMPORTANT]
> **Status: not yet submitted.** Section 7 lists the items that must be resolved before opening the Flathub pull request.

---

## 1. Application Identity

| Field | Value |
| :--- | :--- |
| Application ID | `org.woeusb.WoeUsbGui` |
| Component type | `desktop-application` |
| Project license | `GPL-3.0-or-later` |
| Metadata license | `CC0-1.0` |
| Runtime / SDK | `org.kde.Platform` / `org.kde.Sdk`, branch `6.6` |
| Command | `woeusb-gui` |
| Desktop entry | `/app/share/applications/org.woeusb.WoeUsbGui.desktop` |
| Icon | `/app/share/icons/hicolor/scalable/apps/org.woeusb.WoeUsbGui.svg` |
| MetaInfo | `/app/share/metainfo/org.woeusb.WoeUsbGui.metainfo.xml` |

---

## 2. Manifest Modules

`org.woeusb.WoeUsbGui.yml` builds four modules:

| Module | Source | Purpose |
| :--- | :--- | :--- |
| `wimlib` 1.14.5 | wimlib.net tarball (autotools, `--without-fuse --without-ntfs-3g`) | `wimlib-imagex split` for `install.wim` > 4 GB |
| `p7zip` 17.05 | GitHub release tarball | `7z` for user-space ISO extraction |
| `python3-pyside6` | `shiboken6` + `PySide6_Essentials` 6.6.3 wheels from PyPI (`manylinux_2_28_x86_64`) | Qt 6 bindings — the KDE runtime ships Qt but not PySide6 |
| `woeusb-gui` | local `type: dir` | Installs the Python package, desktop entry, icon and MetaInfo |

---

## 3. Sandbox Permissions

Every `finish-args` entry is reviewed by Flathub. Current state and justification:

| Permission | Status | Justification |
| :--- | :--- | :--- |
| `--system-talk-name=org.freedesktop.UDisks2` | Required | Enumerate removable drives and format / mount / unmount them through the host UDisks2 daemon, without root or raw `/dev` access. |
| `--filesystem=/run/media:rw` | Required | UDisks2 mounts the target under `/run/media/$USER/<LABEL>`; the extracted Windows files are written there. |
| `--filesystem=host:ro` | Required (see 7.2) | Read the ISO from any location **and** resolve which physical block device holds it, for the same-disk collision check (`/proc/self/mountinfo` + `st_dev` of the real path). A portal-provided path would hide the original device. |
| `--socket=wayland` | Required | Native Wayland display. |
| `--socket=fallback-x11` | Required | X11 fallback only when Wayland is unavailable. |
| `--share=ipc` | Required | X11 shared memory. |
| `--device=dri` | Required | GPU-accelerated Qt rendering. |
| `--talk-name=org.freedesktop.Flatpak` | **Remove** (see 7.1) | Not used: the code never calls `flatpak-spawn --host`. This permission allows running commands on the host (sandbox escape) and Flathub will reject it without a strong reason. |

> [!NOTE]
> The application does **not** request `--device=all`, `--filesystem=host` (read-write), `--filesystem=home`, or network access.

---

## 4. AppStream & Desktop Entry

Implemented in `assets/`:

- `<id>` and `<launchable>` match the app ID; `<developer id>` present.
- URLs: `homepage`, `bugtracker`, `vcs-browser`, `help`.
- `<branding>` with light (`#0078d4`) and dark (`#106ebe`) primary colors.
- One screenshot with caption (`assets/screenshots/main-window.png`, referenced via `raw.githubusercontent.com/.../main/...`).
- `<releases>` with `0.1.0` (2026-10-10).
- `<content_rating type="oars-1.1"/>`, `<supports>` pointing + keyboard.
- Desktop entry: `Categories=Utility;Archiving;Qt;` (single main category).

Validation:

```bash
desktop-file-validate assets/org.woeusb.WoeUsbGui.desktop
appstreamcli validate --no-net --pedantic assets/org.woeusb.WoeUsbGui.metainfo.xml
```

Current result: both pass. The only pedantic note is `cid-contains-uppercase-letter` (allowed). Without `--no-net`, the screenshot URL returns 404 until the file exists on the `main` branch (see 7.4).

---

## 5. Local Build & Lint

```bash
flatpak install flathub org.kde.Platform//6.6 org.kde.Sdk//6.6 org.flatpak.Builder

flatpak-builder --force-clean --user --install build-dir org.woeusb.WoeUsbGui.yml
flatpak run org.woeusb.WoeUsbGui

# Flathub linter (manifest and build output)
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest org.woeusb.WoeUsbGui.yml
flatpak run --command=flatpak-builder-lint org.flatpak.Builder builddir build-dir
```

If `rofiles-fuse` is unavailable (containers), add `--disable-rofiles-fuse` to `flatpak-builder`.

---

## 6. Flathub Generative AI Policy Compliance

This project uses Generative AI for code, tests and documentation. Flathub's [requirements](https://docs.flathub.org/docs/for-app-authors/requirements) include a Generative AI policy whose violation leads to rejection and, if repeated, a permanent ban.

### 6.1 Rules

1. **Disclosure is mandatory.** AI-generated code, documentation or packaging in the app must be disclosed, naming the affected parts and the approximate extent. AI used only for research/debugging, with nothing generated shipped, needs no disclosure.
2. **The Flathub manifest must not be AI-generated or AI-assisted.** Disclosure does *not* exempt it.
3. **No AI in the submission process.** AI tools/agents must not open or automate the Flathub PR, write commit messages, PR descriptions, review comments or replies, and you must not request AI-agent reviews.
4. Reviewers may reject a submission based on the extent of generated material, quality or maintainability concerns, even if it was disclosed.

### 6.2 What this means for this repository

| Item | Situation | Action |
| :--- | :--- | :--- |
| Application code, tests | AI-assisted | Disclosed in README. Maintainer must be able to explain and maintain the code. |
| README, CONTRIBUTING, this file, AppStream text | AI-assisted | Disclosed in README. |
| `org.woeusb.WoeUsbGui.yml` (this repo) | Its authorship must be confirmed by the maintainer | The manifest sent to `flathub/flathub` must be **written by hand** by the maintainer. Do not ask an AI assistant to create or edit it. |
| CI auto-PR / release bot | Acts only on this repository | Must never target `flathub/flathub`. |
| Flathub PR, commits, replies | — | Written manually by the maintainer. |

### 6.3 Disclosure for the Flathub PR description

> [!CAUTION]
> Because PR descriptions must not be AI-generated, **do not paste text written by an assistant** (including any template from this repository) into the Flathub PR. Write the disclosure yourself, covering at least:
> - which parts of the upstream app were AI-assisted (code, tests, docs, metadata) and roughly how much;
> - that the Flathub manifest was written by you without AI;
> - that the PR and all communication are done by you.

---

## 7. Open Items Before Flathub Submission

### 7.1 Remove `--talk-name=org.freedesktop.Flatpak`
Unused by the code and a sandbox escape. Remove it from the manifest (by hand, per 6.1).

### 7.2 Prepare the `--filesystem=host:ro` justification
Flathub prefers the file chooser portal. Be ready to explain in the PR that the same-disk collision check needs the real host path/device of the ISO; alternatively, evaluate narrowing it (e.g. `xdg-download:ro` + portal) and accepting a weaker check for portal paths.

### 7.3 Replace the `type: dir` source
Flathub builds from published sources. The `woeusb-gui` module must use a `git` source pinned to a tag + commit, or an `archive` of a GitHub release with `sha256`.

### 7.4 Publish the screenshot on `main`
The MetaInfo screenshot URL points to the `main` branch. Merge to `main` (or pin the URL to a tag) so `appstreamcli validate` passes with network checks, as Flathub's linter does.

### 7.5 Architectures
The bundled PySide6 wheels are `x86_64` only. Either add `aarch64` wheels (with `only-arches`) or restrict the app to x86_64 with a `flathub.json` containing `{"only-arches": ["x86_64"]}`.

### 7.6 Runtime version
Check that `org.kde.Platform//6.6` is not end-of-life at submission time; if it is, move to the current KDE 6.x branch and matching PySide6 wheels.

### 7.7 App ID ownership
Flathub requires control over the domain behind the app ID. `org.woeusb` implies ownership of `woeusb.org`. If that domain is not yours, switch to `io.github.castrocristiano.WoeUsbGui` (rename the ID in the manifest, desktop file, icon, MetaInfo and docs).

### 7.8 Verification and lint
Run `flatpak-builder-lint` on the manifest and build dir (Section 5) and fix all errors before opening the PR.

### 7.9 Install `locales/` in `org.woeusb.WoeUsbGui.yml` (manual step)
Per Section 6.1, `org.woeusb.WoeUsbGui.yml` must be edited by hand without AI assistance. Before building or submitting to Flathub, add the following line manually to `build-commands` under the `woeusb-gui` module in `org.woeusb.WoeUsbGui.yml` so the plain-text `.lang` files are installed to `/app/share/woeusb-gui/locales/`:

```yaml
- install -Dm644 locales/*.lang -t /app/share/woeusb-gui/locales/
```

---

## 8. Submission Steps (manual)

1. Fork [flathub/flathub](https://github.com/flathub/flathub) and branch from `new-pr`.
2. Add your hand-written `org.woeusb.WoeUsbGui.yml` (and `flathub.json` if needed).
3. Run `flatpak-builder-lint` locally.
4. Open the PR against `new-pr`, with your own description, permission justifications (Section 3) and AI disclosure (Section 6.3).
5. Answer reviewers yourself.
