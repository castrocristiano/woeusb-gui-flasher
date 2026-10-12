# Translation & Contributor Guide (`locales/*.lang`)

WoeUSB-GUI Flasher uses human-readable, plain-text `.lang` files in the top-level `locales/` directory for all user-visible interface labels, dialogs, warnings, progress messages, and diagnostic logs.

 No special binary compilers (`msgfmt` or `lrelease`) are required: you can add or edit a translation using any standard text editor.

---

## 1. File Location & Naming Convention

All translation files live in `locales/`:

```text
locales/
├── en.lang       # Default & complete reference language (English)
└── pt_BR.lang    # Brazilian Portuguese translation
```

- Use standard POSIX/BCP-47 locale codes (`<lang>.lang` or `<lang>_<REGION>.lang`), such as `es.lang`, `fr.lang`, `de.lang`, or `pt_BR.lang`.
- All files **must** be saved with **UTF-8** encoding.

---

## 2. `.lang` File Syntax

Each `.lang` file follows a simple `key = value` format:

1. **Comments & Blank Lines**: Lines starting with `#` or `;` and empty lines are ignored.
2. **Key-Value Pairs**: Written as `section.subsection.name = Translated text` (splits on the first `=` sign).
3. **Named Placeholders**: Variables inside curly braces (e.g., `{device_path}`, `{iso_size}`, `{percent}`) are dynamically replaced at runtime. **Do not translate or rename the identifier inside `{...}`.**
4. **Line Breaks**: Literal `\n` sequences inside values are converted to actual newline characters when displayed.
5. **Inline HTML**: Basic Qt rich-text tags (such as `<b>...</b>` and `<br>`) are preserved in dialogs and headers.
6. **Plural Forms**: Keys that depend on a numeric count use `.one` (singular, `count == 1`) and `.other` (plural, `count != 1`) suffixes:
   ```ini
   device.partition_count.one = {count} partition
   device.partition_count.other = {count} partitions
   ```

---

## 3. System Language Priority & Fallback Rules

At startup, WoeUSB-GUI Flasher automatically detects the operating system language using the following priority order:

1. `LANGUAGE` (colon-separated priority list, e.g., `pt_BR:pt:en`)
2. `LC_ALL`
3. `LC_MESSAGES`
4. `LANG`
5. `QLocale.system().uiLanguages()`

### Resolution & Fallback Chain
- **Exact match**: e.g., `pt_BR` matches `locales/pt_BR.lang`.
- **Language-only / regional sibling match**: e.g., `pt_PT` or `pt` matches `locales/pt.lang` if present, or falls back to `locales/pt_BR.lang`.
- **Default English fallback (`locales/en.lang`)**:
  - If the system language is unsupported, unset, or set to `C` / `POSIX`, the application loads `locales/en.lang`.
  - If a specific key is missing in the active language file, or if a translated string has a broken `{placeholder}`, WoeUSB-GUI Flasher automatically falls back to the English string from `locales/en.lang` without crashing.

---

## 4. How to Add a New Language

1. Copy `locales/en.lang` to `locales/<your_locale>.lang` (for example, `locales/es.lang`):
   ```bash
   cp locales/en.lang locales/es.lang
   ```
2. Translate the text to the right of `=` for each key while keeping all `{placeholder}` names unchanged.
3. Test your translation locally by overriding `LANG` or `LANGUAGE`:
   ```bash
   LANGUAGE=es uv run woeusb-gui
   ```
4. Run the test suite to verify catalog integrity and placeholder syntax:
   ```bash
   uv run pytest tests/test_i18n.py
   ```

