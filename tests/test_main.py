"""Tests for the application entry point (logging setup and main launcher)."""

from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from woeusb_gui_flasher import main as main_module


def test_setup_logging_levels():
    with patch.object(logging, "basicConfig") as basic:
        main_module.setup_logging(verbose=True)
        assert basic.call_args.kwargs["level"] == logging.DEBUG
        main_module.setup_logging(verbose=False)
        assert basic.call_args.kwargs["level"] == logging.INFO


def test_main_version_flag_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["woeusb-gui", "--version"])
    with pytest.raises(SystemExit) as exc:
        main_module.main()
    assert exc.value.code == 0
    assert "WoeUSB-GUI" in capsys.readouterr().out


def test_main_launches_window(monkeypatch, qapp):
    monkeypatch.setattr(sys, "argv", ["woeusb-gui", "-v"])
    fake_app = MagicMock()
    fake_app.exec.return_value = 7
    fake_window = MagicMock()

    with (
        patch("PySide6.QtWidgets.QApplication", return_value=fake_app) as app_cls,
        patch("woeusb_gui_flasher.ui.main_window.MainWindow", return_value=fake_window),
        patch.object(main_module, "setup_logging") as setup,
    ):
        app_cls.setApplicationName = MagicMock()
        app_cls.setOrganizationName = MagicMock()
        app_cls.setApplicationDisplayName = MagicMock()
        result = main_module.main()

    setup.assert_called_once_with(True)
    fake_window.show.assert_called_once()
    assert result == 7

