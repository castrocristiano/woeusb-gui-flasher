"""Unit and contract tests for internationalization (i18n) and plain-text .lang catalogs."""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from woeusb_gui_flasher import i18n
from woeusb_gui_flasher.i18n import (
    available_languages,
    detect_system_languages,
    get_current_language,
    get_locales_dir,
    load_catalog,
    normalize_locale_tag,
    parse_lang_file,
    resolve_language,
    tr,
)


@pytest.fixture(autouse=True)
def reset_i18n_catalog():
    """Restores the default catalog after each test."""
    yield
    load_catalog()


def test_get_locales_dir_resolution():
    locales_dir = get_locales_dir()
    assert locales_dir.is_dir()
    assert (locales_dir / "en.lang").is_file()
    assert (locales_dir / "pt_BR.lang").is_file()


def test_available_languages(tmp_path):
    langs = available_languages()
    assert "en" in langs
    assert "pt_BR" in langs
    assert available_languages(tmp_path / "nonexistent") == []


def test_normalize_locale_tag():
    assert normalize_locale_tag("pt_BR.UTF-8") == ["pt_BR", "pt"]
    assert normalize_locale_tag("pt-BR") == ["pt_BR", "pt"]
    assert normalize_locale_tag("en_US.UTF-8@euro") == ["en_US", "en"]
    assert normalize_locale_tag("C") == ["en"]
    assert normalize_locale_tag("C.UTF-8") == ["en"]
    assert normalize_locale_tag("POSIX") == ["en"]
    assert normalize_locale_tag("") == []


def test_detect_system_languages_priority(monkeypatch):
    # 1. LANGUAGE takes highest priority and expands regional + base codes
    monkeypatch.setenv("LANGUAGE", "fr_FR:pt_BR:en")
    monkeypatch.setenv("LC_ALL", "es_ES.UTF-8")
    candidates = detect_system_languages()
    assert candidates == ["fr_FR", "fr", "pt_BR", "pt", "en"]

    # 2. LC_ALL takes priority when LANGUAGE is empty
    monkeypatch.setenv("LANGUAGE", "")
    monkeypatch.setenv("LC_ALL", "pt_BR.UTF-8")
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert detect_system_languages() == ["pt_BR", "pt"]

    # 3. LANG is used when LANGUAGE, LC_ALL, LC_MESSAGES are empty
    monkeypatch.setenv("LC_ALL", "")
    monkeypatch.setenv("LC_MESSAGES", "")
    monkeypatch.setenv("LANG", "pt_PT.UTF-8")
    assert detect_system_languages() == ["pt_PT", "pt"]

    # 4. Falls back to QLocale / system locale when all env vars are empty
    monkeypatch.setenv("LANG", "")
    with patch.object(i18n, "_collect_qt_and_system_locales", return_value=["pt_BR", "pt"]):
        assert detect_system_languages() == ["pt_BR", "pt"]

    with patch.object(i18n, "_collect_qt_and_system_locales", return_value=[]):
        assert detect_system_languages() == ["en"]


def test_resolve_language_priority_and_regional_fallback(monkeypatch):
    # 1. Exact regional match after unsupported primary in LANGUAGE
    monkeypatch.setenv("LANGUAGE", "fr_FR:pt_BR:en")
    assert resolve_language() == "pt_BR"

    # 2. Regional sibling fallback (pt_PT -> pt -> pt_BR)
    monkeypatch.setenv("LANGUAGE", "pt_PT.UTF-8")
    assert resolve_language() == "pt_BR"

    # 3. Base language match (en_GB -> en)
    monkeypatch.setenv("LANGUAGE", "en_GB.UTF-8")
    assert resolve_language() == "en"

    # 4. Unsupported locale falls back to English
    monkeypatch.setenv("LANGUAGE", "ja_JP.UTF-8")
    monkeypatch.setenv("LC_ALL", "ja_JP.UTF-8")
    monkeypatch.setenv("LC_MESSAGES", "ja_JP.UTF-8")
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    assert resolve_language() == "en"

    # 5. C / POSIX locale falls back to English
    monkeypatch.setenv("LANGUAGE", "")
    monkeypatch.setenv("LC_ALL", "C.UTF-8")
    monkeypatch.setenv("LC_MESSAGES", "")
    monkeypatch.setenv("LANG", "C")
    assert resolve_language() == "en"


def test_load_catalog_and_tr_switching():
    load_catalog("en")
    assert get_current_language() == "en"
    assert tr("ui.main.start_burn_button") == "Start Burning"
    assert tr("burn.stage.validating") == "Validating requirements and images..."

    load_catalog("pt_BR")
    assert get_current_language() == "pt_BR"
    assert tr("ui.main.start_burn_button") == "Iniciar Gravação"
    assert tr("burn.stage.validating") == "Validando requisitos e imagens..."


def test_plural_selection_one_and_other():
    load_catalog("en")
    assert tr("device.partition_count", count=1) == "1 partition"
    assert tr("device.partition_count", count=0) == "0 partitions"
    assert tr("device.partition_count", count=3) == "3 partitions"

    load_catalog("pt_BR")
    assert tr("device.partition_count", count=1) == "1 partição"
    assert tr("device.partition_count", count=2) == "2 partições"


def test_parse_lang_file_comments_escapes_and_malformed_lines(tmp_path, caplog):
    custom_lang = tmp_path / "custom.lang"
    custom_lang.write_text(
        "# Comment line\n"
        "\n"
        "valid.key = Hello\\nWorld\n"
        "malformed_line_without_equals\n"
        "= value_without_key\n"
        "INVALID KEY = Value\n"
        "spaced.key = Value with = inside\n",
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING):
        entries = parse_lang_file(custom_lang)

    assert entries["valid.key"] == "Hello\nWorld"
    assert entries["spaced.key"] == "Value with = inside"
    assert "malformed_line_without_equals" not in entries
    assert any("Malformed translation line" in rec.message for rec in caplog.records)
    assert any("Invalid translation key" in rec.message for rec in caplog.records)
    assert parse_lang_file(tmp_path / "missing.lang") == {}


def test_missing_key_and_broken_placeholder_fallback(tmp_path, caplog):
    # Create temporary locales dir with en.lang and partial/broken pt_BR.lang
    en_file = tmp_path / "en.lang"
    en_file.write_text(
        "greeting.hello = Hello {name}!\nonly.in.english = English fallback text\n",
        encoding="utf-8",
    )
    pt_file = tmp_path / "pt_BR.lang"
    pt_file.write_text(
        "greeting.hello = Olá {wrong_placeholder}!\n",
        encoding="utf-8",
    )

    load_catalog("pt_BR", locales_dir=tmp_path)

    # Missing key in pt_BR falls back to en.lang
    assert tr("only.in.english") == "English fallback text"

    # Broken placeholder in pt_BR falls back to en.lang and logs warning
    with caplog.at_level(logging.WARNING):
        res = tr("greeting.hello", name="Linux")
    assert res == "Hello Linux!"
    assert any("Placeholder formatting error" in rec.message for rec in caplog.records)

    # Unknown key in both catalogs returns key name safely
    assert tr("completely.unknown.key") == "completely.unknown.key"


def test_all_source_tr_keys_exist_in_en_and_pt_br_catalogs():
    """AST audit: verifies 100% of tr('...') keys in src/ exist in en.lang and pt_BR.lang."""
    locales_dir = get_locales_dir()
    en_entries = parse_lang_file(locales_dir / "en.lang")
    pt_entries = parse_lang_file(locales_dir / "pt_BR.lang")

    # Every key in en.lang must exist in pt_BR.lang and vice versa
    assert set(en_entries.keys()) == set(pt_entries.keys())

    # Placeholders in pt_BR.lang must match en.lang for every key
    placeholder_re = re.compile(r"\{([a-zA-Z0-9_]+)\}")
    for key, en_val in en_entries.items():
        en_vars = set(placeholder_re.findall(en_val))
        pt_vars = set(placeholder_re.findall(pt_entries[key]))
        assert en_vars == pt_vars, f"Placeholder mismatch for key '{key}': {en_vars} != {pt_vars}"

    # Scan all Python files in src/woeusb_gui_flasher for tr("...") calls
    src_dir = Path(__file__).resolve().parent.parent / "src" / "woeusb_gui_flasher"
    referenced_keys: set[str] = set()

    for py_file in src_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "tr"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                referenced_keys.add(node.args[0].value)

    assert len(referenced_keys) >= 65
    for key in referenced_keys:
        assert key in en_entries, f"Key '{key}' used in source code is missing from locales/en.lang"
        assert key in pt_entries, (
            f"Key '{key}' used in source code is missing from locales/pt_BR.lang"
        )
