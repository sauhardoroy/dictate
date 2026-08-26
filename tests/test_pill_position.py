"""Unit tests for pill position persistence and validation."""
import json
import pytest

from config import settings as settings_module


def test_settings_supports_pill_coordinates(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"pill_x": 450, "pill_y": 800}), encoding="utf-8")
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()
    assert settings["pill_x"] == 450
    assert settings["pill_y"] == 800


def test_settings_allows_none_pill_coordinates(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"pill_x": None, "pill_y": None}), encoding="utf-8")
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()
    assert settings["pill_x"] is None
    assert settings["pill_y"] is None


def test_settings_rejects_invalid_pill_coordinates(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"pill_x": "invalid", "pill_y": True}), encoding="utf-8")
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()
    assert settings["pill_x"] is None
    assert settings["pill_y"] is None
