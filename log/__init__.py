"""Logging setup for Dictate.

Single configured ``logging.Logger`` used across the app. Writes to a
rotating file plus a console handler when running from source (dev).

File location:
- frozen build : %APPDATA%\\Dictate\\dictate.log
- from source  : <project>\\dictate.log
"""
import logging
import logging.handlers
import os
import sys

from config.settings import settings_dir

_LOG_NAME = "dictate"
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s %(message)s"
_MSG_FORMAT = "%(message)s"

_configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a child logger of the app-wide ``dictate`` logger."""
    return logging.getLogger(f"{_LOG_NAME}.{name}")


def setup_logging(debug: bool = False, console: bool = False) -> logging.Logger:
    """Configure handlers once and return the root ``dictate`` logger.

    Idempotent across relaunches. ``debug`` enables DEBUG level messages
    and verbose formatting; ``console`` also prints to stderr (dev mode).
    """
    global _configured
    root = logging.getLogger(_LOG_NAME)
    if _configured:
        root.setLevel(logging.DEBUG if debug else logging.INFO)
        return root

    root.setLevel(logging.DEBUG if debug else logging.INFO)
    root.propagate = False

    try:
        log_dir = settings_dir()
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "dictate.log")
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(fh)
    except Exception as exc:  # pragma: no cover - filesystem edge case
        print(f"[logging] file handler failed: {exc}", file=sys.stderr)

    if console or debug:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter(_MSG_FORMAT))
        root.addHandler(ch)

    _configured = True
    root.debug("logging initialised (debug=%s)", debug)
    return root