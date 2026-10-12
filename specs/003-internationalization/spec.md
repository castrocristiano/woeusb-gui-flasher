# Feature Specification: Internationalization (i18n)

**Feature Branch**: `003-internationalization`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "o sistema deve ser internacionalizado. as strings de logs, textos de ui, etc devem ser separadas em uma pasta separada em arquivo de texto puro, fácil de traduzir, respeite as regras do flathub, o padrão é inglês, caso não houver tradução para o idioma do sistema. o idioma deve ter prioridade do sistema"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - App follows the system language (Priority: P1)

A user whose desktop is set to a supported language (e.g. Brazilian Portuguese) launches the application and sees every visible text (window titles, buttons, labels, dialogs, warnings, stage names, progress text, log drawer messages) in that language without any manual configuration.

**Why this priority**: This is the core value of the feature; without automatic language selection from the system, translation has no user benefit.

**Independent Test**: Launch the app with the system language set to a language that has a translation and verify all visible texts appear in that language.

**Acceptance Scenarios**:

1. **Given** the system language is `pt_BR` and a `pt_BR` translation exists, **When** the user opens the app, **Then** all UI texts and log messages are displayed in Portuguese.
2. **Given** the system lists several preferred languages (e.g. `fr`, `pt_BR`, `en`), **When** the app starts, **Then** the first preferred language that has a translation is used.
3. **Given** the system language is a regional variant (e.g. `pt_PT`) and only the base language (`pt`) is available, **When** the app starts, **Then** the base language translation is used.

---

### User Story 2 - English fallback (Priority: P1)

A user whose system language has no available translation (e.g. Japanese) uses the app in English, and no raw message keys, blanks or errors are ever displayed.

**Why this priority**: Guarantees the app is always usable, regardless of locale.

**Independent Test**: Launch the app with an unsupported language and verify every text is shown in English.

**Acceptance Scenarios**:

1. **Given** the system language is `ja` and no `ja` translation exists, **When** the app starts, **Then** all texts are shown in English.
2. **Given** a translation exists but is missing one message, **When** that message is displayed, **Then** the English text for that message is shown instead of a key or empty text.

---

### User Story 3 - Translators add a language using plain text files (Priority: P2)

A community translator adds a new language by copying the English plain-text translation file(s) from a dedicated translations folder, translating the values, and submitting them, without editing application code or using specialized tooling.

**Why this priority**: Enables community growth and keeps translation effort low.

**Independent Test**: Add a new translation text file for a new language, start the app with that system language and verify the texts appear translated, with no code changes.

**Acceptance Scenarios**:

1. **Given** a new plain-text translation file is placed in the translations folder with the language code in its name, **When** the system language matches, **Then** the app uses it automatically.
2. **Given** a translation file contains a malformed line, **When** the app starts, **Then** the app still starts, ignores the malformed entry, falls back to English for it and records a warning.

---

### User Story 4 - Translations are packaged and published per Flathub rules (Priority: P3)

Maintainers publish the app on Flathub with translations included, with store metadata (name, summary, description, launcher entry) also translatable, so that the Flathub listing and the installed app follow Flathub requirements.

**Why this priority**: Required for distribution, but does not change runtime behavior for users.

**Independent Test**: Build the Flatpak, install it, verify translation files are present in the package and that desktop and metadata entries show localized text.

**Acceptance Scenarios**:

1. **Given** the Flatpak package is built, **When** it is installed, **Then** all translation files are available to the app inside the sandbox.
2. **Given** the system language has a translation, **When** the user views the app launcher entry and store listing, **Then** name, summary and description are shown in that language where translated.

---

### Edge Cases

- Message containing dynamic values (device name, sizes, percentages, speeds, time) must keep the values correct in every language, including different word order.
- Plural-sensitive messages (e.g. "1 file" / "5 files") must be correct in each language.
- A translation file with encoding or formatting problems must not crash the app.
- Language environment unset or set to `C`/`POSIX`: English is used.
- Language changes while the app is running: takes effect on next launch.
- Very long translated strings must not make UI elements unusable or truncated.
- Technical diagnostic output from external tools is shown as received and is not translated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display all user-facing texts (windows, buttons, labels, dialogs, confirmations, warnings, errors, stage names, progress and speed texts) using translatable messages instead of hardcoded text.
- **FR-002**: System MUST display messages written by the app to the log drawer and log output in the selected language.
- **FR-003**: System MUST store all translatable messages in a dedicated folder, separate from application code, in plain-text files that can be edited with any text editor.
- **FR-004**: System MUST use English as the default and reference language and as the fallback when no translation exists for the system language.
- **FR-005**: System MUST fall back to English on a per-message basis when a translation lacks a specific message.
- **FR-006**: System MUST select the language from the system language preferences, honoring the priority order defined by the system, and MUST NOT require manual language configuration.
- **FR-007**: System MUST match regional variants to the base language when an exact regional translation is unavailable.
- **FR-008**: System MUST support messages with named placeholders for dynamic values, allowing translators to reorder them.
- **FR-009**: System MUST support correct plural forms per language.
- **FR-010**: System MUST remain fully functional if a translation file is missing, malformed or partially invalid, and MUST report the problem in the log.
- **FR-011**: System MUST allow adding a new language by only adding a translation file, without code changes.
- **FR-012**: System MUST package translation files within the Flatpak so they work inside the sandbox, and MUST follow Flathub requirements, including translatable launcher entry and application metadata.
- **FR-013**: System MUST NOT translate or alter external tool output, device identifiers, file paths or technical identifiers.
- **FR-014**: Project MUST provide a translation guide describing file format, naming and how to add/test a language, and an automated check that every message key used by the app exists in the English reference file.

### Key Entities

- **Message**: A translatable text identified by a unique key, with English text, optional named placeholders and optional plural variants.
- **Translation File**: Plain-text file for one language/locale containing messages keyed by identifier.
- **Language Preference List**: Ordered list of languages from the system, used to pick the best available translation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of user-visible texts and app-generated log messages come from translation files (no hardcoded visible text remains), verified by an automated check.
- **SC-002**: With the system language set to a supported language, 100% of visible texts appear in that language on first launch with zero configuration steps.
- **SC-003**: With an unsupported system language, 100% of texts appear in English and no message keys or blank texts are visible.
- **SC-004**: A contributor can add a new language by only adding one plain-text file, with zero code changes, in under 30 minutes for the full message set.
- **SC-005**: Switching language has no noticeable impact on startup time (startup remains within 10% of the current baseline).
- **SC-006**: The Flatpak build passes Flathub validation for metadata and launcher entries with translations included.

## Assumptions

- English is the reference language; Brazilian Portuguese (`pt_BR`) is provided as the first additional translation.
- The language is determined at startup; changing it requires restarting the app.
- Messages written to the log drawer by the app are translated; raw output from external tools is shown unchanged.
- Right-to-left language layout support is out of scope for this version.
- Translation files live in a dedicated folder at the project root, are included in the Flatpak, and use a simple line-based key/value text format that is easy to edit and review.
