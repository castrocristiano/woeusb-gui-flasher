"""Pytest fixtures for WoeUSB GUI Flasher tests."""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication instance across all test modules."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["woeusb-gui-test", "-platform", "offscreen"])
    return app


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Clean exit to prevent PySide6 C++ destructor segfault at interpreter shutdown."""
    import atexit

    atexit.register(os._exit, int(exitstatus))
