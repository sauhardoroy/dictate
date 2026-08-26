import logging

from log import get_logger, setup_logging


def test_setup_logging_is_idempotent_and_returns_named_logger(tmp_path, monkeypatch):
    monkeypatch.setattr("log.settings_dir", lambda: str(tmp_path))

    root = setup_logging(debug=True, console=False)
    child = get_logger("test")

    assert root.name == "dictate"
    assert child.name == "dictate.test"
    assert root.level == logging.DEBUG

    # A second call must not duplicate handlers or fail.
    assert setup_logging(debug=False) is root
    assert len(root.handlers) >= 1
    assert (tmp_path / "dictate.log").exists()
