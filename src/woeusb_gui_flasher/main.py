"""Application entry point and QApplication initialization."""

from __future__ import annotations

import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    """Configures application-wide logging format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    """Main CLI/GUI launcher entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WoeUSB GUI Flasher — Universal Windows USB creation tool for Linux."
    )
    parser.add_argument(
        "--version",
        action="version",
        version="WoeUSB-GUI 0.1.0",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logs",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Initialize Qt Application
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from woeusb_gui_flasher.ui.main_window import MainWindow

    # Enable High DPI scaling
    QApplication.setApplicationName("WoeUSB-GUI")
    QApplication.setOrganizationName("WoeUSB")
    QApplication.setApplicationDisplayName("WoeUSB-GUI")

    app = QApplication(sys.argv)

    # Set application icon if available
    from pathlib import Path

    icon_path = (
        Path(__file__).resolve().parent.parent.parent / "assets" / "org.woeusb.WoeUsbGui.svg"
    )
    if not icon_path.is_file():
        # Fallback for installed Flatpak location
        icon_path = Path("/app/share/icons/hicolor/scalable/apps/org.woeusb.WoeUsbGui.svg")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
