# Quickstart & Validation Guide: Internationalization (i18n)

**Feature**: `003-internationalization`  
**Spec**: [spec.md](spec.md) | **Contract**: [contracts/i18n-contract.md](contracts/i18n-contract.md)

---

## 1. Running the Application in Different System Languages

### Brazilian Portuguese (`pt_BR`)
```bash
LANGUAGE=pt_BR LANG=pt_BR.UTF-8 uv run woeusb-gui
```
**Expected**: Window title, cards, buttons, confirmation dialogs, progress messages, and log drawer entries appear in Brazilian Portuguese.

### English Default / Unsupported Language Fallback (`ja_JP` → `en`)
```bash
LANGUAGE=ja_JP LANG=ja_JP.UTF-8 uv run woeusb-gui
```
**Expected**: Since `locales/ja_JP.lang` is not present, the application automatically falls back to `locales/en.lang` (English) with zero raw keys or blank strings.

### Priority List Resolution (`fr_FR:pt_BR:en`)
```bash
LANGUAGE=fr_FR:pt_BR:en uv run woeusb-gui
```
**Expected**: `fr_FR` is skipped (not available) and `pt_BR` is selected as the next highest-priority system language.

---

## 2. Adding a New Language (Plain-Text Workflow)

1. Copy the reference file:
   ```bash
   cp locales/en.lang locales/es.lang
   ```
2. Edit `locales/es.lang` in any plain-text editor, translating the text after `=` while keeping `{placeholder}` names intact.
3. Launch with `LANGUAGE=es uv run woeusb-gui` — no code changes or compilation required.

---

## 3. Automated Test & Flathub Metadata Validation

```bash
# Run unit & i18n completeness tests (verifies all tr() keys exist in locales/en.lang)
QT_QPA_PLATFORM=offscreen uv run pytest tests/ --cov=src --cov-fail-under=75

# Validate localized Desktop and AppStream metadata for Flathub compliance
desktop-file-validate assets/org.woeusb.WoeUsbGui.desktop
appstreamcli validate --no-net --pedantic assets/org.woeusb.WoeUsbGui.metainfo.xml
```

