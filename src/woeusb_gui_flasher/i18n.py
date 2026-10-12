"""Internationalization (i18n) catalog loader, system locale resolver, and translator."""

from __future__ import annotations

import locale
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE: str = "en"
FLATPAK_LOCALES_DIR: Path = Path("/app/share/woeusb-gui/locales")
KEY_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
LOCALE_ENV_VARS: tuple[str, ...] = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")
POSIX_DEFAULT_LOCALES: frozenset[str] = frozenset({"c", "posix"})


@dataclass
class TranslationCatalog:
    """Loaded translation messages for an active locale with English fallback."""

    locale_code: str = DEFAULT_LANGUAGE
    messages: dict[str, str] = field(default_factory=dict)
    fallback_messages: dict[str, str] = field(default_factory=dict)
    source_path: Path | None = None


_active_catalog: TranslationCatalog | None = None


def get_locales_dir() -> Path:
    """Resolves the path to the 'locales/' directory (repository root or Flatpak /app)."""
    repo_locales = Path(__file__).resolve().parent.parent.parent / "locales"
    if repo_locales.is_dir():
        return repo_locales
    if FLATPAK_LOCALES_DIR.is_dir():
        return FLATPAK_LOCALES_DIR
    return repo_locales


def parse_lang_file(file_path: Path) -> dict[str, str]:
    """Parses a plain-text UTF-8 .lang catalog file into a key-value dictionary."""
    entries: dict[str, str] = {}
    if not file_path.is_file():
        logger.warning("Translation file not found: %s", file_path)
        return entries

    try:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Could not read translation file %s: %s", file_path, exc)
        return entries

    for line_num, raw_line in enumerate(raw_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in raw_line:
            logger.warning(
                "Malformed translation line %d in %s (missing '='): %s",
                line_num,
                file_path.name,
                stripped,
            )
            continue

        key_part, _, value_part = raw_line.partition("=")
        key = key_part.strip()
        if not key or not KEY_PATTERN.match(key):
            logger.warning(
                "Invalid translation key on line %d in %s: '%s'",
                line_num,
                file_path.name,
                key,
            )
            continue

        value = value_part.strip().replace("\\n", "\n")
        entries[key] = value

    return entries


def available_languages(locales_dir: Path | None = None) -> list[str]:
    """Returns a sorted list of locale codes discovered in locales_dir."""
    target_dir = locales_dir if locales_dir is not None else get_locales_dir()
    if not target_dir.is_dir():
        return []
    return sorted(p.stem for p in target_dir.glob("*.lang") if p.is_file())


def normalize_locale_tag(raw_tag: str) -> list[str]:
    """Normalizes a raw locale string into ordered candidate codes (regional then base)."""
    cleaned = raw_tag.strip()
    if not cleaned:
        return []

    cleaned = cleaned.split(".")[0].split("@")[0].replace("-", "_")
    if cleaned.lower() in POSIX_DEFAULT_LOCALES:
        return [DEFAULT_LANGUAGE]

    parts = [p for p in cleaned.split("_") if p]
    if not parts:
        return []

    lang = parts[0].lower()
    if len(parts) >= 2:
        region = parts[1].upper()
        regional = f"{lang}_{region}"
        return [regional, lang]
    return [lang]


def _append_unique(target: list[str], candidates: list[str]) -> None:
    for item in candidates:
        if item and item not in target:
            target.append(item)


def _collect_env_locales() -> list[str]:
    candidates: list[str] = []
    for var_name in LOCALE_ENV_VARS:
        raw_val = os.environ.get(var_name, "").strip()
        if not raw_val:
            continue
        for token in raw_val.split(":"):
            _append_unique(candidates, normalize_locale_tag(token))
        if candidates:
            return candidates
    return candidates


def _collect_qt_and_system_locales() -> list[str]:
    candidates: list[str] = []
    try:
        from PySide6.QtCore import QLocale

        for ui_lang in QLocale.system().uiLanguages():
            _append_unique(candidates, normalize_locale_tag(ui_lang))
    except (ImportError, AttributeError, RuntimeError) as exc:
        logger.debug("QLocale language detection skipped: %s", exc)

    try:
        sys_loc, _ = locale.getlocale()
        if sys_loc:
            _append_unique(candidates, normalize_locale_tag(sys_loc))
    except (ValueError, TypeError) as exc:
        logger.debug("locale.getlocale() skipped: %s", exc)

    return candidates


def detect_system_languages() -> list[str]:
    """Detects preferred languages ordered by system priority."""
    env_candidates = _collect_env_locales()
    if env_candidates:
        return env_candidates

    sys_candidates = _collect_qt_and_system_locales()
    if sys_candidates:
        return sys_candidates

    return [DEFAULT_LANGUAGE]


def _match_candidate(candidate: str, available: list[str]) -> str | None:
    lower_map = {code.lower(): code for code in available}
    if candidate.lower() in lower_map:
        return lower_map[candidate.lower()]

    if "_" not in candidate:
        prefix = f"{candidate.lower()}_"
        for code in available:
            if code.lower().startswith(prefix):
                return code
    return None


def resolve_language(
    preferred: list[str] | None = None,
    locales_dir: Path | None = None,
) -> str:
    """Resolves the best matching available language code according to priority."""
    available = available_languages(locales_dir)
    if not available:
        return DEFAULT_LANGUAGE

    raw_list = preferred if preferred is not None else detect_system_languages()
    expanded: list[str] = []
    for item in raw_list:
        _append_unique(expanded, normalize_locale_tag(item))

    for candidate in expanded:
        matched = _match_candidate(candidate, available)
        if matched:
            return matched

    return DEFAULT_LANGUAGE


def load_catalog(
    language: str | None = None,
    locales_dir: Path | None = None,
) -> str:
    """Loads English fallback catalog and target language catalog into active state."""
    global _active_catalog
    target_dir = locales_dir if locales_dir is not None else get_locales_dir()
    preferred = [language] if language else None
    resolved_lang = resolve_language(preferred=preferred, locales_dir=target_dir)

    en_path = target_dir / f"{DEFAULT_LANGUAGE}.lang"
    fallback_msgs = parse_lang_file(en_path) if en_path.is_file() else {}

    if resolved_lang == DEFAULT_LANGUAGE:
        target_msgs = dict(fallback_msgs)
        source_path = en_path if en_path.is_file() else None
    else:
        target_path = target_dir / f"{resolved_lang}.lang"
        target_msgs = parse_lang_file(target_path) if target_path.is_file() else {}
        source_path = target_path if target_path.is_file() else None

    _active_catalog = TranslationCatalog(
        locale_code=resolved_lang,
        messages=target_msgs,
        fallback_messages=fallback_msgs,
        source_path=source_path,
    )
    return resolved_lang


def get_current_language() -> str:
    """Returns the currently active language code, initializing from system locale if needed."""
    if _active_catalog is None:
        return load_catalog()
    return _active_catalog.locale_code


def _resolve_template(catalog: TranslationCatalog, key: str, count: int | None) -> tuple[str, str]:
    lookup_key = key
    if count is not None:
        suffix = "one" if count == 1 else "other"
        plural_key = f"{key}.{suffix}"
        if plural_key in catalog.messages or plural_key in catalog.fallback_messages:
            lookup_key = plural_key

    fallback_tpl = catalog.fallback_messages.get(
        lookup_key,
        catalog.fallback_messages.get(key, key),
    )
    primary_tpl = catalog.messages.get(lookup_key, fallback_tpl)
    return primary_tpl, fallback_tpl


def tr(key: str, count: int | None = None, **kwargs: Any) -> str:
    """Translates `key` into the active language with English fallback and safe interpolation."""
    if _active_catalog is None:
        load_catalog()
    assert _active_catalog is not None

    format_args = dict(kwargs)
    if count is not None:
        format_args.setdefault("count", count)

    primary_tpl, fallback_tpl = _resolve_template(_active_catalog, key, count)
    if not format_args:
        return primary_tpl

    try:
        return primary_tpl.format(**format_args)
    except (KeyError, ValueError, IndexError) as exc:
        logger.warning(
            "Placeholder formatting error for key '%s' in locale '%s': %s",
            key,
            _active_catalog.locale_code,
            exc,
        )
        try:
            return fallback_tpl.format(**format_args)
        except (KeyError, ValueError, IndexError):
            return fallback_tpl
