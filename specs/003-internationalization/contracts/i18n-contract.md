# Contract: Internationalization (`i18n.py`) & Plain-Text Locale Files

**Feature**: `003-internationalization`  
**Module**: `src/woeusb_gui_flasher/i18n.py`  
**Translation Directory**: `locales/`

---

## 1. Plain-Text File Format Contract (`locales/<locale>.lang`)

1. **Location & Naming**:
   - Reference file: `locales/en.lang` (mandatory, complete key set).
   - Additional translations: `locales/<lang>.lang` or `locales/<lang>_<REGION>.lang` (e.g., `locales/pt_BR.lang`).
   - Encoding: UTF-8 with `\n` line endings.

2. **Syntax Rules**:
   - Blank lines and lines whose first non-whitespace character is `#` are comments and ignored.
   - Each message entry occupies a single line in the format:
     ```ini
     namespace.section.key = Translated text with {named_placeholder} and \n line breaks
     ```
   - Whitespace immediately around `=` is stripped; leading/trailing quotes are not required.
   - Escape sequence `\n` in values is decoded into a literal newline character (`U+000A`).
   - Plural variants use `.one` (when `count == 1`) and `.other` (when `count != 1`) suffixes:
     ```ini
     device.partition_count.one = {count} partition
     device.partition_count.other = {count} partitions
     ```
   - Malformed lines (no `=` separator or empty key) MUST NOT raise an exception; `i18n` logs a `WARNING` and ignores the offending line.

---

## 2. Public Python API Contract (`woeusb_gui_flasher.i18n`)

```python
from pathlib import Path
from typing import Any

DEFAULT_LANGUAGE: str = "en"


def get_locales_dir() -> Path:
    """Returns the resolved path to the 'locales/' directory (repo root or /app/share/woeusb-gui/locales)."""


def available_languages(locales_dir: Path | None = None) -> list[str]:
    """Returns sorted list of locale codes discovered in locales_dir (e.g. ['en', 'pt_BR'])."""


def detect_system_languages() -> list[str]:
    """Returns ordered list of normalized locale candidates from LANGUAGE, LC_ALL, LC_MESSAGES, LANG, and QLocale."""


def resolve_language(
    preferred: list[str] | None = None,
    locales_dir: Path | None = None,
) -> str:
    """Resolves the best matching available language code according to priority and regional fallback rules."""


def load_catalog(
    language: str | None = None,
    locales_dir: Path | None = None,
) -> str:
    """Loads English fallback catalog + resolved target catalog into active state and returns active language code."""


def get_current_language() -> str:
    """Returns the currently active language code (initializes from system locale on first call)."""


def tr(key: str, count: int | None = None, **kwargs: Any) -> str:
    """
    Translates `key` into the active language with per-key English fallback and named placeholder interpolation.
    - If `count` is provided, resolves `<key>.one` (when count == 1) or `<key>.other` (otherwise) before `<key>`.
    - If a translated template fails `.format(**kwargs)` due to invalid placeholder syntax, logs a warning and
      formats the English fallback template instead.
    - Never raises KeyError or ValueError for missing keys or malformed translations.
    """
```

---

## 3. Key Namespace Convention

| Prefix | Scope | Source Module(s) |
| :--- | :--- | :--- |
| `app.cli.*` | CLI description and `--help` arguments | `main.py` |
| `ui.main.*` | MainWindow title, action buttons, dialogs, status alerts | `ui/main_window.py` |
| `ui.iso.*` | ISO selector card labels, file dialog title & filters, details | `ui/components.py` |
| `ui.drive.*` | Drive selector card labels, refresh button, 64 GB safety checkbox & tooltip | `ui/components.py` |
| `ui.options.*` | Filesystem options card labels and descriptions | `ui/components.py` |
| `ui.progress.*` | Progress card initial status and labels | `ui/components.py` |
| `ui.log.*` | Log console drawer toggle button and copy button | `ui/components.py` |
| `burn.stage.*` | Stage titles and status updates | `burn_engine.py` |
| `burn.progress.*` | Real-time percentage, transferred bytes, write speed, and ETA strings | `burn_engine.py` |
| `burn.log.*` | Execution log messages emitted to the log drawer and logger | `burn_engine.py` |
| `burn.error.*` | Localized user-facing error messages raised during burn operations | `burn_engine.py` |
| `disk.collision.*` | Same-disk collision warning message | `disk_manager.py` |
| `model.validation.*` | Configuration validation error messages | `models.py` |

