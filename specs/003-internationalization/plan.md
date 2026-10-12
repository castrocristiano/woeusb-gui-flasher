# Implementation Plan: Internationalization (i18n)

**Branch**: `feature/003-internationalization` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-internationalization/spec.md`

---

## Summary

Internationalize the entire **WoeUSB-GUI Flasher** application so that all user-visible UI labels, dialogs, warnings, progress/speed indicators, and application-generated log messages are separated into human-editable plain-text catalog files inside a dedicated `locales/` folder (`locales/en.lang` as the reference default and `locales/pt_BR.lang` as the Brazilian Portuguese translation). At startup, the system resolves the active language strictly from the operating system's language priority order (`LANGUAGE`, `LC_ALL`, `LC_MESSAGES`, `LANG`, and `QLocale.system().uiLanguages()`), matches regional variants to base languages, falls back to English both globally and per-key when a translation is missing or malformed, and localizes freedesktop `.desktop` and AppStream `.metainfo.xml` files in full compliance with Flathub policies.

---

## Technical Context

**Language/Version**: Python 3.11+ (compatible with Flatpak KDE/Freedesktop runtime and Python 3.12/3.14)  
**Primary Dependencies**: PySide6 (Qt 6.6+), Python Standard Library (`locale`, `os`, `pathlib`, `re`, `logging`)  
**Storage**: UTF-8 plain-text key-value catalog files in `locales/<locale>.lang` (`locales/en.lang`, `locales/pt_BR.lang`)  
**Testing**: `pytest` + `pytest-cov` (`QT_QPA_PLATFORM=offscreen`, $\ge 75\%$ test coverage enforced by SonarQube Quality Gate)  
**Target Platform**: Universal Linux Desktop via Flatpak (`org.woeusb.WoeUsbGui`)  
**Project Type**: Desktop GUI Application (PySide6 / Flatpak)  
**Performance Goals**: Catalog loading and locale resolution $< 5\text{ ms}$ at startup (within SC-005 $< 10\%$ startup impact); O(1) dictionary lookup per `tr()` call  
**Constraints**: Plain-text translation files editable without specialized compilation tools; resilient fallback to English on missing/malformed entries; strict compliance with Flathub Generative AI policy (`org.woeusb.WoeUsbGui.yml` must never be edited by AI)  
**Scale/Scope**: ~85 translatable message keys across `ui/main_window.py`, `ui/components.py`, `burn_engine.py`, `disk_manager.py`, `models.py`, and `main.py`, plus `.desktop` and `.metainfo.xml` metadata and contributor documentation (`docs/TRANSLATIONS.md`)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio Constitucional | Status | Avaliação Pré e Pós-Design |
| :--- | :--- | :--- |
| **I. Safety & Non-Destructive Protection (NON-NEGOTIABLE)** | **PASS** | Nenhuma lógica de filtragem de dispositivos ou validação destrutiva é enfraquecida; os diálogos de confirmação e alertas de colisão de disco preservam todos os dados críticos (`{device_path}`, `{size}`, `{label}`) via interpolação segura com fallback garantido para inglês. |
| **II. Universal Linux Execution via Flatpak** | **PASS** | O carregador `get_locales_dir()` resolve `locales/` tanto na árvore local/pacote Python quanto em `/app/share/woeusb-gui/locales` dentro do sandbox Flatpak. Metadados `.desktop` e `.metainfo.xml` seguem o padrão Freedesktop/Flathub. |
| **III. Responsive & Asynchronous Architecture** | **PASS** | O catálogo de tradução é carregado uma única vez em memória ($< 5\text{ ms}$) e consultado em $O(1)$ de forma thread-safe pelo `BurnWorker` (`QThread`) e pela thread principal da GUI. |
| **IV. Observability & User Feedback** | **PASS** | Todas as mensagens de estágio, progresso percentual, velocidade de escrita, ETA e logs do aplicativo na gaveta de logs são internacionalizadas no idioma do sistema, mantendo intacta a saída bruta de ferramentas externas (`7z`, `wimlib-imagex`, `udisksctl`). |
| **V. Native Linux Desktop Integration** | **PASS** | Respeita a lista de prioridade de idiomas do ambiente gráfico Linux (`LANGUAGE`, `LANG`, `QLocale.system().uiLanguages()`) e fornece lançador `.desktop` e AppStream `.metainfo.xml` traduzidos. |

---

## Project Structure

### Documentation (this feature)

```text
specs/003-internationalization/
├── spec.md              # Feature specification
├── checklists/
│   └── requirements.md  # Specification quality checklist
├── plan.md              # This implementation plan (/speckit-plan)
├── research.md          # Phase 0 architectural decisions (/speckit-plan)
├── data-model.md        # Phase 1 entities & resolution rules (/speckit-plan)
├── quickstart.md        # Phase 1 validation & translator quickstart (/speckit-plan)
├── contracts/
│   └── i18n-contract.md # Phase 1 file format & Python API contract (/speckit-plan)
└── tasks.md             # Phase 2 actionable task list (/speckit-tasks)
```

### Source Code (repository root)

```text
locales/
├── en.lang              # Reference English catalog (default & fallback)
└── pt_BR.lang           # Brazilian Portuguese catalog

src/woeusb_gui_flasher/
├── i18n.py              # Locale detection, .lang parser, fallback & tr() interpolation
├── main.py              # Initializes system locale catalog at startup; localized CLI help
├── models.py            # Localized validation error messages via tr()
├── disk_manager.py      # Localized same-disk collision message via tr()
├── burn_engine.py       # Localized stages, progress/speed/ETA strings, logs & errors via tr()
└── ui/
    ├── components.py    # Localized cards, buttons, file dialog, safety filter & log drawer
    └── main_window.py   # Localized window title, action buttons, confirmation & alert dialogs

assets/
├── org.woeusb.WoeUsbGui.desktop      # Localized Comment[pt_BR] & Keywords[pt_BR]
└── org.woeusb.WoeUsbGui.metainfo.xml # Localized xml:lang="pt_BR" summary, description & caption

docs/
├── TRANSLATIONS.md      # Translator guide: file format, placeholders, plurals & testing
└── FLATHUB.md           # Manual manifest note for installing locales/ into /app/share/woeusb-gui/locales

tests/
└── test_i18n.py         # Unit & contract tests: locale priority, regional fallback, plurals,
                         # malformed line resilience, placeholder fallback, and 100% key parity
```

**Structure Decision**: Single-package desktop application structure with a top-level `locales/` directory for plain-text `.lang` files (configured in `pyproject.toml` so both editable installs and packaged builds access `locales/`), paired with a dedicated `src/woeusb_gui_flasher/i18n.py` module.

---

## Complexity Tracking

*No Constitution Check violations. Zero external dependencies added.*
