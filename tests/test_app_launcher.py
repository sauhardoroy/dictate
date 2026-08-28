"""Unit and regression tests for Feature 5: Open Apps via Voice."""
import json
import os
import subprocess
import pytest
from unittest.mock import patch, MagicMock

from context.app_launcher import (
    load_app_registry,
    match_app_launch_command,
    launch_registered_app,
)


@pytest.fixture
def mock_registry():
    return {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
    }


class TestAppRegistryLoading:
    """Test registry loading, validation, and error resilience."""

    def test_load_valid_registry(self, tmp_path):
        reg_file = tmp_path / "apps.json"
        reg_file.write_text(json.dumps({
            "Notepad": "notepad.exe",
            "Calc": "calc.exe"
        }), encoding="utf-8")

        loaded = load_app_registry(str(reg_file))
        assert loaded == {"notepad": "notepad.exe", "calc": "calc.exe"}

    def test_load_missing_registry_returns_empty(self, tmp_path):
        loaded = load_app_registry(str(tmp_path / "nonexistent.json"))
        assert loaded == {}

    def test_load_corrupted_json_returns_empty(self, tmp_path):
        reg_file = tmp_path / "corrupted.json"
        reg_file.write_text("{invalid json", encoding="utf-8")
        loaded = load_app_registry(str(reg_file))
        assert loaded == {}


class TestMatchAppLaunchCommand:
    """Test strict prefix and alias matching against speech transcripts."""

    @pytest.mark.parametrize("phrase,expected_alias,expected_exe", [
        ("open notepad", "notepad", "notepad.exe"),
        ("Open notepad.", "notepad", "notepad.exe"),
        ("OPEN NOTEPAD!", "notepad", "notepad.exe"),
        ("please open calculator", "calculator", "calc.exe"),
        ("Please open calc.", "calc", "calc.exe"),
        ("launch paint", "paint", "mspaint.exe"),
        ("Launch paint.", "paint", "mspaint.exe"),
        ("start explorer", "explorer", "explorer.exe"),
        ("please launch file explorer", "file explorer", "explorer.exe"),
        ("open task manager", "task manager", "taskmgr.exe"),
    ])
    def test_valid_app_launch_commands(self, mock_registry, phrase, expected_alias, expected_exe):
        result = match_app_launch_command(phrase, mock_registry)
        assert result is not None
        alias, exe = result
        assert alias == expected_alias
        assert exe == expected_exe

    @pytest.mark.parametrize("phrase", [
        "open the door and let the dog out",
        "open the file on page three",
        "open a new browser tab",
        "please open the window",
        "launch a new marketing campaign",
        "start the engine of the car",
        "can you open notepad for me",  # Mid-sentence, not allowed prefix
        "open something_unregistered",
        "open",
        "please open",
        "hello world",
        "",
        "   ",
    ])
    def test_ordinary_speech_and_unregistered_apps_do_not_match(self, mock_registry, phrase):
        """Ordinary dictated content starting with 'open' must pass through unaffected."""
        assert match_app_launch_command(phrase, mock_registry) is None


class TestLaunchRegisteredApp:
    """Test secure detached process execution."""

    def test_launch_registered_app_success(self):
        with patch("subprocess.Popen") as mock_popen:
            ok = launch_registered_app("calc.exe")
            assert ok is True
            assert mock_popen.called

    def test_launch_empty_path_returns_false(self):
        assert launch_registered_app("") is False

    def test_launch_exception_handled_gracefully(self):
        with patch("subprocess.Popen", side_effect=OSError("Permission denied")):
            ok = launch_registered_app("calc.exe")
            assert ok is False
