"""Unit tests for the live interim transcript preview overlay and settings."""
import sys
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication
import pytest

from config import settings as settings_module
from ui.preview_overlay import PreviewOverlay


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_settings_supports_show_interim_preview(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()
    assert settings["show_interim_preview"] is True

    settings["show_interim_preview"] = False
    assert settings["show_interim_preview"] is False


def test_settings_rejects_invalid_show_interim_preview(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()
    with pytest.raises(ValueError):
        settings["show_interim_preview"] = "not-a-bool"


def test_preview_overlay_creation(qapp):
    overlay = PreviewOverlay(dark=True)
    assert overlay._display_words == []
    assert overlay._is_showing is False
    assert overlay.width() == PreviewOverlay.OVERLAY_WIDTH
    assert overlay.height() == PreviewOverlay.OVERLAY_HEIGHT


def test_preview_overlay_set_text_and_clear(qapp):
    overlay = PreviewOverlay(dark=True)
    
    # Setting empty / whitespace string should be ignored
    overlay.set_text("   ")
    assert overlay._display_words == []
    assert overlay._is_showing is False

    # Setting valid text directly extracts the last 4 words
    overlay.set_text("Hello world this is a test")
    assert len(overlay._display_words) == PreviewOverlay.MAX_VISIBLE_WORDS
    assert overlay._display_words == ["this", "is", "a", "test"]
    assert overlay._is_showing is True

    # Clearing text resets everything
    overlay.clear()
    assert overlay._display_words == []


def test_preview_overlay_reposition(qapp):
    overlay = PreviewOverlay(dark=True)
    pill_rect = QRect(500, 400, 120, 60)

    overlay.reposition(pill_rect)

    # Position should be horizontally centered relative to pill
    expected_x = 500 + (120 - PreviewOverlay.OVERLAY_WIDTH) // 2
    expected_y = 400 + 60 + 8  # 8px below pill

    assert overlay._target_pos == (expected_x, expected_y)


def test_preview_overlay_painting(qapp):
    from PyQt6.QtGui import QPixmap

    overlay = PreviewOverlay(dark=True)
    overlay.set_text("Testing real-time rendering preview")
    overlay._opacity = 1.0

    pix = QPixmap(PreviewOverlay.OVERLAY_WIDTH, PreviewOverlay.OVERLAY_HEIGHT)
    overlay.render(pix)

    # Test light mode rendering as well
    overlay.set_dark_mode(False)
    overlay.render(pix)

