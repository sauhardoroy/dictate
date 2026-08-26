"""Dictate — local voice typing widget. Run: python main.py"""
import argparse
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from app import DictateApp
from log import get_logger, setup_logging

log = get_logger(__name__)


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Keep unexpected failures bounded and diagnosable in the rotating log."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log.critical("unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


def main() -> int:
    parser = argparse.ArgumentParser(description="Dictate — local voice typing widget")
    parser.add_argument("--smoke", action="store_true",
                        help="build the UI then exit (used by tests)")
    parser.add_argument("--debug", action="store_true",
                        help="enable DEBUG level logging")
    parser.add_argument("--console", action="store_true",
                        help="also log to the console (stderr)")
    args = parser.parse_args()

    setup_logging(debug=args.debug, console=args.console)
    sys.excepthook = log_unhandled_exception

    app = QApplication(sys.argv)
    app.setApplicationName("Dictate")
    app.setQuitOnLastWindowClosed(False)

    dictate = DictateApp(load_model=not args.smoke)

    if args.smoke:
        QTimer.singleShot(1200, app.quit)
        code = app.exec()
        dictate.hotkeys.unregister()
        return code

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
