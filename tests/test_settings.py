import json
import sys

import pytest
from PyQt6.QtWidgets import QApplication

from config import settings as settings_module


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app



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
    assert settings["model"] == "parakeet-tdt-0.6b-v3"
    assert settings["input_device"] is None
    assert settings["auto_stop"] is True
    assert settings["language"] == "en"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "unknown_legacy_field" not in saved
    assert saved == settings.data


def test_settings_hotwords_configuration(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"hotwords_file": "custom_words.txt", "hotwords_score": 3.5}), encoding="utf-8")
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()
    assert settings["hotwords_file"] == "custom_words.txt"
    assert settings["hotwords_score"] == 3.5

    settings["hotwords_score"] = 4.0
    assert settings["hotwords_score"] == 4.0

    with pytest.raises(ValueError):
        settings["hotwords_score"] = -1.0


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


def test_settings_dialog_stop_mode(qapp):
    from ui.settings_dialog import SettingsDialog
    data = {"auto_stop": False, "mode": "toggle"}
    dlg = SettingsDialog(data)
    assert dlg.stop_mode.currentData() is False
    assert dlg.values()["auto_stop"] is False

    # Switch to auto-stop
    dlg.stop_mode.setCurrentIndex(0)
    assert dlg.stop_mode.currentData() is True
    assert dlg.values()["auto_stop"] is True


def test_cross_platform_settings_dir(monkeypatch):
    monkeypatch.setattr(settings_module, "is_frozen", lambda: True)

    monkeypatch.setattr(settings_module.sys, "platform", "darwin")
    mac_dir = settings_module.settings_dir()
    assert "Library" in mac_dir or "Application Support" in mac_dir

    monkeypatch.setattr(settings_module.sys, "platform", "win32")
    win_dir = settings_module.settings_dir()
    assert "Dictate" in win_dir


def test_cross_platform_autostart_macos(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module.sys, "platform", "darwin")
    fake_home = tmp_path / "userhome"
    fake_home.mkdir()
    monkeypatch.setattr(settings_module.os.path, "expanduser", lambda p: str(p).replace("~", str(fake_home)))

    settings_module.set_autostart(True)
    plist_file = fake_home / "Library" / "LaunchAgents" / "com.dictate.app.plist"
    assert plist_file.exists()
    assert "com.dictate.app" in plist_file.read_text(encoding="utf-8")

    settings_module.set_autostart(False)
    assert not plist_file.exists()



