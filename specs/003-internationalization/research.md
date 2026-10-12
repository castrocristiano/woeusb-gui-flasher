# Phase 0 Research: Internationalization (i18n)

**Feature**: `003-internationalization`  
**Date**: 2026-10-12

---

## 1. Plain-Text Translation File Format & Folder Structure

- **Decision**: Store translations in a top-level `locales/` directory as UTF-8 plain-text `.lang` files (`locales/en.lang`, `locales/pt_BR.lang`) using a line-oriented `key = value` syntax with `#` comments, `\n` line breaks, `{name}` named placeholders, and `.one` / `.other` suffixes for plurals.
- **Rationale**:
  - Directly satisfies FR-003 and SC-004: any contributor can open `locales/en.lang` in any plain-text editor, copy it to `locales/<locale>.lang`, and translate the right-hand side of each `key = value` line without installing binary compilers (`msgfmt`, `lrelease`) or learning XML/JSON escaping rules.
  - Zero third-party dependencies: parsed in $< 2\text{ ms}$ using Python's standard library.
  - Tolerant by design (FR-010): lines without `=` (other than comments/blanks) or invalid placeholder syntax log a warning and fall back to the English reference string instead of crashing the application.
- **Alternatives Considered**:
  - *GNU gettext (`.po` / `.mo`)*: Requires compiling `.po` to binary `.mo` files at build time and dealing with multi-line `msgid`/`msgstr` blocks, which adds friction for non-technical translators and complicates plain-text editing.
  - *Qt Linguist (`.ts` / `.qm`)*: XML-based source format and binary `.qm` compilation step; violates the plain-text requirement (FR-003).
  - *JSON / YAML*: Requires strict punctuation/quoting and breaks the entire file if a single comma or quote is misplaced, violating fault tolerance (FR-010).

---

## 2. System Language Detection & Priority Resolution

- **Decision**: Resolve the preferred language list at startup using standard POSIX/freedesktop environment variables first (`LANGUAGE`, `LC_ALL`, `LC_MESSAGES`, `LANG`), augmented by `QLocale.system().uiLanguages()` when a Qt application context is active, and match against available files in `locales/`.
- **Rationale**:
  - Linux desktop environments and Flatpak's locale portal pass user language preferences through `LANGUAGE` (colon-separated priority list, e.g., `pt_BR:pt:en`) and `LANG` (`pt_BR.UTF-8`), as well as Qt's `QLocale.system().uiLanguages()`.
  - Checking `LANGUAGE` → `LC_ALL` → `LC_MESSAGES` → `LANG` → `QLocale.system().uiLanguages()` honors the exact priority order configured in the user's system (FR-006) while remaining deterministic in headless tests via environment variable overrides.
  - Matching algorithm for each candidate tag (normalized to `<lang>_<REGION>` and `<lang>`):
    1. Exact match (`locales/<lang>_<REGION>.lang`, e.g., `pt_BR.lang`).
    2. Base language match (`locales/<lang>.lang`, e.g., `pt.lang`).
    3. Regional sibling match for the same base language if no generic `<lang>.lang` exists (e.g., `pt_PT` → `pt_BR.lang`).
    4. Fallback to `locales/en.lang` (FR-004).
- **Alternatives Considered**:
  - *`locale.getdefaultlocale()` only*: Deprecated in Python 3.13+ and ignores the multi-language priority list in `LANGUAGE`.
  - *Manual language selector in UI*: Explicitly excluded by FR-006 ("MUST select the language from the system language preferences... MUST NOT require manual language configuration").

---

## 3. Per-Message Fallback & Safe Placeholder Interpolation

- **Decision**: Load `locales/en.lang` as the base dictionary in memory, overlay the resolved target locale dictionary on top, and format placeholders safely so missing or mistyped placeholders in a community translation fall back to the English template rather than raising `KeyError` or `ValueError`.
- **Rationale**:
  - Guarantees FR-004, FR-005, FR-008, and FR-010:
    - Missing key in target locale → automatically served from `en.lang`.
    - Broken `{placeholder}` in target locale → logs a warning and formats the `en.lang` string with the same `**kwargs`, ensuring dynamic values (device paths, sizes, speeds, percentages) are always shown accurately.
    - Plural selection (`count` parameter): checks `<key>.one` when `count == 1` and `<key>.other` otherwise, falling back to `<key>`.

---

## 4. Flathub & Freedesktop Packaging Compliance

- **Decision**:
  1. Resolve `locales/` via dual-path lookup: repository/package relative path (`Path(__file__).resolve().parent.parent.parent / "locales"`) first, then Flatpak installation path (`/app/share/woeusb-gui/locales`).
  2. Localize `assets/org.woeusb.WoeUsbGui.desktop` using standard freedesktop `Key[locale]=Value` entries (`Comment[pt_BR]`, `Keywords[pt_BR]`).
  3. Localize `assets/org.woeusb.WoeUsbGui.metainfo.xml` using standard AppStream `xml:lang="pt_BR"` attributes on `<summary>`, `<description>` elements, and `<screenshot><caption>`.
  4. Document the manual manifest step in `docs/FLATHUB.md` without modifying `org.woeusb.WoeUsbGui.yml` via AI, strictly honoring Flathub's Generative AI policy (Section 6 of `docs/FLATHUB.md`).
- **Rationale**:
  - Ensures 100% compatibility with `desktop-file-validate` and `appstreamcli validate --no-net --pedantic` (SC-006) while respecting Flathub's rule that the Flatpak manifest must be maintained by hand.

