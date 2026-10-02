"""Application entry point."""

import sys

from PyQt6.QtWidgets import QApplication

from sldgridy import __version__
from sldgridy.ui.main_window import APP_NAME, MainWindow


def create_application(argv: list[str]) -> QApplication:
    app = QApplication(argv)
    app.setOrganizationName("sldgridy")
    app.setApplicationName("sldgridy")
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("sldgridy")
    return app


def main(argv: list[str] | None = None) -> int:
    app = create_application(sys.argv if argv is None else argv)
    window = MainWindow()
    window.show()
    return app.exec()
