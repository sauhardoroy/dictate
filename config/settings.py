"""JSON-backed, validated user settings for Dictate."""
import json
import os
import sys
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "trigger_key": "ctrl+shift+p",
    "mode": "ptt",
    "engine": "whisper",
    "model": "small.en",
    "compute_type": "auto",
    "device": "auto",
    "cpu_threads": 0,
    "initial_prompt": "",
    "language": "en",
    "vad_filter": True,
    "auto_stop": True,
    "vad_silence_seconds": 1.4,
    "ai_polish": False,
    "ai_polish_api_key": "",
    "ai_polish_base_url": "https://integrate.api.nvidia.com/v1",
    "ai_polish_model": "nvidia/nemotron-3-nano-30b-a3b",
    "injection_delay_ms": 150,
    "restore_clipboard": True,
    "input_device": None,
    "show_pill": True,
    "nemotron_binary": "",
    "autostart": False,
    "onboarding_completed": False,
    "voice_commands": True,
    "pill_x": None,
    "pill_y": None,
    "enable_history": True,
    "max_history_entries": 100,
}


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_base_dir() -> str:
    return os.path.dirname(sys.executable) if is_frozen() else PROJECT_ROOT


def settings_dir() -> str:
    if is_frozen():
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(appdata, "Dictate")
        os.makedirs(path, exist_ok=True)
        return path
    return PROJECT_ROOT


def settings_path() -> str:
    return os.path.join(settings_dir(), "settings.json")


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_input_device(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0)


def _is_delay(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 5_000


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_optional_coordinate(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


def _is_cpu_threads(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 64


def _is_silence_seconds(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.2 <= value <= 5.0


_COMPUTE_TYPES = {
    "default", "auto", "int8", "int8_float32", "int8_float16",
    "int8_bfloat16", "int16", "float16", "bfloat16", "float32",
}

_VALIDATORS = {
    "trigger_key": _is_nonempty_string,
    "mode": lambda value: value in {"ptt", "toggle"},
    "engine": lambda value: value in {"whisper", "nemotron"},
    "model": _is_nonempty_string,
    "compute_type": lambda value: value in _COMPUTE_TYPES,
    "device": lambda value: value in {"cpu", "cuda", "auto"},
    "cpu_threads": _is_cpu_threads,
    "initial_prompt": lambda value: isinstance(value, str),
    "language": lambda value: isinstance(value, str),
    "vad_filter": _is_bool,
    "auto_stop": _is_bool,
    "vad_silence_seconds": _is_silence_seconds,
    "ai_polish": _is_bool,
    "ai_polish_api_key": lambda value: isinstance(value, str),
    "ai_polish_base_url": lambda value: isinstance(value, str),
    "ai_polish_model": lambda value: isinstance(value, str),
    "injection_delay_ms": _is_delay,
    "restore_clipboard": _is_bool,
    "input_device": _is_input_device,
    "show_pill": _is_bool,
    "nemotron_binary": lambda value: isinstance(value, str),
    "autostart": _is_bool,
    "onboarding_completed": _is_bool,
    "voice_commands": _is_bool,
    "pill_x": _is_optional_coordinate,
    "pill_y": _is_optional_coordinate,
    "enable_history": _is_bool,
    "max_history_entries": lambda v: isinstance(v, int) and not isinstance(v, bool) and 10 <= v <= 10_000,
}


def validated_settings(loaded: Any) -> dict:
    """Merge known, valid JSON values onto defaults; discard everything else."""
    result = dict(DEFAULTS)
    if not isinstance(loaded, dict):
        return result
    for key, value in loaded.items():
        if key in DEFAULTS and _VALIDATORS[key](value):
            result[key] = value
    return result


class Settings:
    def __init__(self):
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(settings_path(), "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            loaded = {}

        self.data = validated_settings(loaded)
        # Migrate old/invalid config immediately, so future launches are stable.
        if loaded != self.data:
            self.save()

    def save(self):
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __setitem__(self, key, value):
        if key not in DEFAULTS:
            raise KeyError(f"Unknown Dictate setting: {key}")
        if not _VALIDATORS[key](value):
            raise ValueError(f"Invalid value for Dictate setting {key!r}: {value!r}")
        self.data[key] = value
        self.save()


def set_autostart(enabled: bool):
    """Create/remove a launcher script in the user's Startup folder."""
    startup_dir = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
    )
    bat = os.path.join(startup_dir, "Dictate.bat")
    if enabled:
        os.makedirs(startup_dir, exist_ok=True)
        if is_frozen():
            exe_path = sys.executable
            exe_dir = os.path.dirname(exe_path)
            content = "@echo off\r\n" f'cd /d "{exe_dir}"\r\n' f'start "" "{exe_path}"\r\n'
        else:
            main_py = os.path.join(PROJECT_ROOT, "main.py")
            content = "@echo off\r\n" f'cd /d "{PROJECT_ROOT}"\r\n' f'start "" "{sys.executable}" "{main_py}"\r\n'
        with open(bat, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        try:
            os.remove(bat)
        except FileNotFoundError:
            pass
