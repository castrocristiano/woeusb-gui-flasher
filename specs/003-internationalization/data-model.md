# Phase 1 Data Model: Internationalization (i18n)

**Feature**: `003-internationalization`  
**Date**: 2026-10-12

---

## Entities

### 1. `TranslationCatalog`

Represents the loaded collection of translation messages for a specific locale alongside the English reference catalog.

| Field | Type | Description |
| :--- | :--- | :--- |
| `locale_code` | `str` | Active resolved locale identifier (e.g., `"en"`, `"pt_BR"`). |
| `messages` | `dict[str, str]` | Mapping of message keys to localized template strings for `locale_code`. |
| `fallback_messages` | `dict[str, str]` | Mapping of message keys to reference English (`"en"`) template strings. |
| `source_path` | `Path | None` | File path of the loaded `.lang` file for `locale_code`. |

**Validation & Invariants**:
- `fallback_messages` MUST always be populated from `locales/en.lang` when present.
- Keys MUST match `^[a-z0-9_]+(\.[a-z0-9_]+)*$` (dot-separated namespaces such as `ui.main.title`, `burn.log.start`, `model.error.ineligible_device`).
- Malformed lines in `.lang` files (missing `=`, empty key, or invalid UTF-8 sequences) MUST be logged via `logger.warning` and skipped without aborting catalog loading.

---

### 2. `MessageKey` (Plain-Text `.lang` Entry)

Represents an individual translatable entry inside `locales/<locale>.lang`.

| Attribute | Format | Example |
| :--- | :--- | :--- |
| `key` | Dot-separated identifier | `burn.progress.copying` |
| `template` | UTF-8 text with optional `{name}` placeholders and `\n` escapes | `Copying files: {percent}% ({transferred} / {total})` |
| `plural_one` | Optional `<key>.one` entry (`count == 1`) | `burn.files_copied.one = {count} file copied` |
| `plural_other` | Optional `<key>.other` entry (`count != 1`) | `burn.files_copied.other = {count} files copied` |

---

### 3. `LanguagePreferenceList`

Ordered sequence of normalized locale identifiers extracted from the operating system environment.

| Source Priority | Source | Example Input | Normalized Candidates |
| :--- | :--- | :--- | :--- |
| 1 | `LANGUAGE` env var | `"fr_FR:pt_BR:en"` | `["fr_FR", "fr", "pt_BR", "pt", "en"]` |
| 2 | `LC_ALL` env var | `"pt_BR.UTF-8"` | `["pt_BR", "pt"]` |
| 3 | `LC_MESSAGES` env var | `"pt_PT.UTF-8"` | `["pt_PT", "pt"]` |
| 4 | `LANG` env var | `"en_US.UTF-8"` | `["en_US", "en"]` |
| 5 | `QLocale.system().uiLanguages()` | `["pt-BR", "en-US"]` | `["pt_BR", "pt", "en_US", "en"]` |

**Resolution State Transitions**:
1. Collect raw tags in priority order (ignoring `"C"` and `"POSIX"`, which map to `"en"`).
2. Expand each regional tag `<lang>_<REGION>` into `[<lang>_<REGION>, <lang>]`.
3. Match the first candidate with an existing `locales/<code>.lang` file (or regional sibling `<lang>_*.lang` when matching base `<lang>`).
4. If no match is found, select `"en"`.

