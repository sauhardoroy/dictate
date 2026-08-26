import json

import pytest

from config import settings as settings_module


def test_load_replaces_invalid_values_and_preserves_valid_values(tmp_path, monkeypatch):
    """Corrupt/obsolete user config must never reach the app state machine."""
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({
        "trigger_key": "", "mode": "bad", "model": 7,
        "input_device": "not-a-device", "auto_stop": "yes",
        "unknown_legacy_field": "ignore-me", "language": "en",
    }), encoding="utf-8")
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()

    assert settings["trigger_key"] == "ctrl+shift+p"
    assert settings["mode"] == "ptt"
    assert settings["model"] == "small.en"
    assert settings["input_device"] is None
    assert settings["auto_stop"] is True
    assert settings["language"] == "en"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "unknown_legacy_field" not in saved
    assert saved == settings.data


@pytest.mark.parametrize("value, expected", [(None, None), (0, 0), (12, 12)])
def test_input_device_accepts_only_none_or_non_negative_int(value, expected, tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"input_device": value}), encoding="utf-8")
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    assert settings_module.Settings()["input_device"] == expected


def test_setitem_rejects_unknown_settings_key(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))
    settings = settings_module.Settings()

    with pytest.raises(KeyError):
        settings["surprise"] = "value"


def test_load_recovers_from_malformed_json(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text("{ not JSON", encoding="utf-8")
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()

    assert settings.data == settings_module.DEFAULTS
    assert json.loads(path.read_text(encoding="utf-8")) == settings_module.DEFAULTS
