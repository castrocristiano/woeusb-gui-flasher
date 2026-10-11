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


def pytest_sessionfinish(session, exitstatus):
    """Clean exit to prevent PySide6 ABI shutdown crash on Python 3.14."""
    import os

    os._exit(exitstatus)
