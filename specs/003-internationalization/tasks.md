# Tasks: Internationalization (i18n)

**Input**: Design documents from `/specs/003-internationalization/`

**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (required for user stories), [research.md](research.md), [data-model.md](data-model.md), [contracts/i18n-contract.md](contracts/i18n-contract.md)

**Tests**: Included as required by FR-014, SC-001, SC-006, and the project's $\ge 75\%$ SonarQube coverage Quality Gate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Exact file paths are included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the dedicated plain-text translations folder and packaging configuration

- [X] T001 Create top-level `locales/` directory and initial `locales/en.lang` placeholder at `locales/en.lang`
- [X] T002 Configure package data inclusion for `locales/*.lang` in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core `i18n` translation loader and reference English catalog that MUST be complete before user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement `TranslationCatalog`, `.lang` UTF-8 key-value parser (keys matching `^[a-z0-9_]+(\.[a-z0-9_]+)*$`, `#` comments, `\n` escapes), `get_locales_dir()`, and `tr()` in `src/woeusb_gui_flasher/i18n.py`
- [X] T004 Populate complete English reference catalog (`app.cli.*`, `ui.main.*`, `ui.iso.*`, `ui.drive.*`, `ui.options.*`, `ui.progress.*`, `ui.log.*`, `burn.stage.*`, `burn.progress.*`, `burn.log.*`, `burn.error.*`, `disk.collision.*`, `model.validation.*`) in `locales/en.lang`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - App follows the system language (Priority: P1) 🎯 MVP

**Goal**: Automatically detect the system's preferred language list on startup and display all UI texts, dialogs, stages, progress indicators, and app-generated log messages in that language.

**Independent Test**: Launch the app (or run headless UI/worker tests) with `LANGUAGE=pt_BR` or `LANG=pt_BR.UTF-8` and verify all visible UI labels, dialogs, progress strings, and log drawer messages render in Brazilian Portuguese.

### Implementation for User Story 1

- [X] T005 [US1] Implement `detect_system_languages()`, `available_languages()`, `resolve_language()`, and `load_catalog()` honoring priority order (`LANGUAGE` → `LC_ALL` → `LC_MESSAGES` → `LANG` → `QLocale.system().uiLanguages()`) and regional-to-base matching in `src/woeusb_gui_flasher/i18n.py`
- [X] T006 [P] [US1] Create complete Brazilian Portuguese translation catalog matching all keys in `locales/pt_BR.lang`
- [X] T007 [P] [US1] Internationalize validation error messages using `tr()` in `src/woeusb_gui_flasher/models.py`
- [X] T008 [P] [US1] Internationalize same-disk collision message using `tr()` in `src/woeusb_gui_flasher/disk_manager.py`
- [X] T009 [P] [US1] Internationalize stage titles, progress/speed/ETA strings, log messages, and user-facing runtime errors using `tr()` while keeping raw external tool output untranslated in `src/woeusb_gui_flasher/burn_engine.py`
- [X] T010 [P] [US1] Internationalize `IsoSelectorCard`, `DriveSelectorCard`, `OptionsCard`, `ProgressCard`, and `LogConsoleDrawer` texts and tooltips using `tr()` in `src/woeusb_gui_flasher/ui/components.py`
- [X] T011 [P] [US1] Internationalize `MainWindow` title, buttons, confirmation dialogs, and status alerts using `tr()` in `src/woeusb_gui_flasher/ui/main_window.py`
- [X] T012 [US1] Initialize system locale catalog on startup and internationalize CLI help strings in `src/woeusb_gui_flasher/main.py`
- [X] T013 [US1] Add unit and integration tests for system language priority detection (`LANGUAGE`, `LANG`, regional fallback `pt_PT` → `pt`/`pt_BR`) and UI/worker localization in `tests/test_i18n.py`

**Checkpoint**: User Story 1 is fully functional and testable independently

---

## Phase 4: User Story 2 - English fallback (Priority: P1)

**Goal**: Ensure users on unsupported locales (`ja_JP`, `C`, `POSIX`) or with partially translated catalogs always see English text, with zero raw keys, blank strings, or formatting crashes.

**Independent Test**: Set `LANGUAGE=ja_JP` (unsupported) or load a partial catalog missing keys/placeholders and verify every `tr()` call returns valid English text with interpolated dynamic values.

### Implementation for User Story 2

- [X] T014 [US2] Harden `tr()` and `load_catalog()` in `src/woeusb_gui_flasher/i18n.py` so `C`/`POSIX`/unset locales resolve to `"en"`, missing keys fall back per-message to `fallback_messages` from `locales/en.lang`, and invalid `{placeholder}` syntax in a translation logs a warning and formats the English template
- [X] T015 [US2] Add unit tests for unsupported locale fallback, `C`/`POSIX` handling, per-key fallback, and broken-placeholder fallback in `tests/test_i18n.py`

**Checkpoint**: User Stories 1 and 2 work independently with guaranteed English fallback

---

## Phase 5: User Story 3 - Translators add a language using plain text files (Priority: P2)

**Goal**: Allow community translators to add a new language by dropping a single `<locale>.lang` plain-text file into `locales/`, supporting plural forms (`.one` / `.other`), fault tolerance for malformed lines, and automated key-completeness verification.

**Independent Test**: Place a temporary `es.lang` (including a malformed line and plural entries) in a test `locales/` directory, select `LANGUAGE=es`, and verify valid entries render in Spanish, the malformed line logs a warning and falls back to English, and plural forms resolve accurately.

### Implementation for User Story 3

- [X] T016 [US3] Implement plural form resolution (`count=1` → `<key>.one`, `count!=1` → `<key>.other`) and malformed-line fault tolerance with `logger.warning` in `src/woeusb_gui_flasher/i18n.py`
- [X] T017 [P] [US3] Create translator documentation covering file format, naming conventions, `{placeholder}` reordering, `.one`/`.other` plurals, and verification commands in `docs/TRANSLATIONS.md`
- [X] T018 [US3] Add automated AST/regex audit test in `tests/test_i18n.py` verifying 100% of `tr("...")` keys used in `src/woeusb_gui_flasher/` exist in `locales/en.lang` and `locales/pt_BR.lang`, plus tests for plural forms and malformed `.lang` files

**Checkpoint**: User Story 3 is complete and verified by automated catalog completeness checks

---

## Phase 6: User Story 4 - Translations are packaged and published per Flathub rules (Priority: P3)

**Goal**: Ensure translations work inside the Flatpak sandbox (`/app/share/woeusb-gui/locales`) and localize the freedesktop `.desktop` launcher and AppStream `.metainfo.xml` metadata according to Flathub rules.

**Independent Test**: Validate `assets/org.woeusb.WoeUsbGui.desktop` and `assets/org.woeusb.WoeUsbGui.metainfo.xml` and run `tests/test_flatpak_contract.py` to confirm localized metadata and sandbox path resolution.

### Implementation for User Story 4

- [X] T019 [P] [US4] Add localized `Comment[pt_BR]` and `Keywords[pt_BR]` entries to `assets/org.woeusb.WoeUsbGui.desktop`
- [X] T020 [P] [US4] Add localized `xml:lang="pt_BR"` elements (`<summary>`, `<description>`, `<screenshot><caption>`) to `assets/org.woeusb.WoeUsbGui.metainfo.xml`
- [X] T021 [P] [US4] Document the manual Flatpak manifest installation instruction (`cp -r locales /app/share/woeusb-gui/locales`) in `docs/FLATHUB.md` (without AI-editing `org.woeusb.WoeUsbGui.yml`)
- [X] T022 [US4] Extend Flatpak and metadata contract tests in `tests/test_flatpak_contract.py` and `tests/test_i18n.py` to verify `/app/share/woeusb-gui/locales` fallback resolution and localized `.desktop` / `.metainfo.xml` entries

**Checkpoint**: All 4 user stories are independently functional and Flathub-compliant

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Ensure existing test suite compatibility across locales, code formatting, and SonarQube Quality Gate ($\ge 75\%$ coverage, 0 issues)

- [X] T023 Update existing unit/UI tests in `tests/` (including `tests/conftest.py` fixture if needed) so all existing and new tests pass deterministically regardless of the host's `LANG`/`LANGUAGE` environment
- [X] T024 Run `uv run ruff check .` and `uv run ruff format --check .` to ensure zero lint or formatting issues across all modified and new files
- [X] T025 Execute `./sonar_check.sh` to validate $\ge 75\%$ test coverage and 0 SonarQube issues against the remote quality gate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — starts immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) — BLOCKS all user stories.
- **User Stories (Phase 3–6)**:
  - **US1 (P1)** and **US2 (P1)** depend on Phase 2.
  - **US3 (P2)** depends on Phase 2 (and audits keys wired in US1).
  - **US4 (P3)** depends on Phase 2 and can run in parallel with US1–US3 for `assets/` and `docs/FLATHUB.md`.
- **Polish (Phase 7)**: Depends on Phases 3–6 completion.

### Parallel Opportunities

- Within **US1 (Phase 3)**: Tasks `T006`, `T007`, `T008`, `T009`, `T010`, and `T011` touch completely separate files (`locales/pt_BR.lang`, `models.py`, `disk_manager.py`, `burn_engine.py`, `ui/components.py`, `ui/main_window.py`) and can be executed in parallel once `T005` is in place.
- Within **US4 (Phase 6)**: Tasks `T019`, `T020`, and `T021` touch independent files (`assets/org.woeusb.WoeUsbGui.desktop`, `assets/org.woeusb.WoeUsbGui.metainfo.xml`, `docs/FLATHUB.md`) and can run in parallel.

---

## Parallel Example: User Story 1

```bash
# After T005 (i18n resolution functions in src/woeusb_gui_flasher/i18n.py):
Task T006: "Create complete Brazilian Portuguese translation catalog in locales/pt_BR.lang"
Task T007: "Internationalize validation error messages in src/woeusb_gui_flasher/models.py"
Task T008: "Internationalize same-disk collision message in src/woeusb_gui_flasher/disk_manager.py"
Task T009: "Internationalize stage titles, progress, and logs in src/woeusb_gui_flasher/burn_engine.py"
Task T010: "Internationalize UI cards and log drawer in src/woeusb_gui_flasher/ui/components.py"
Task T011: "Internationalize MainWindow dialogs and buttons in src/woeusb_gui_flasher/ui/main_window.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup (`T001`–`T002`)
2. Complete Phase 2: Foundational (`T003`–`T004`)
3. Complete Phase 3 & Phase 4: User Story 1 & User Story 2 (`T005`–`T015`)
4. **STOP and VALIDATE**: Verify automatic system language selection (`pt_BR`) and English fallback (`en`) across all UI and log strings

### Incremental Delivery

1. Setup + Foundational → Core `i18n` engine and `locales/en.lang` ready
2. Add US1 + US2 → Full runtime localization (`en` + `pt_BR`) with fallback
3. Add US3 → Plural support, malformed-file resilience, `docs/TRANSLATIONS.md`, and 100% key parity audit test
4. Add US4 + Polish → Flathub `.desktop` & `.metainfo.xml` localization, Ruff formatting, and SonarQube Quality Gate validation

