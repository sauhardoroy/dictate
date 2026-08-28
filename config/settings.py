"""JSON-backed, validated user settings for Dictate."""
import json
import os
import sys
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "trigger_key": "ctrl+shift+p",
    "mode": "ptt",
    "engine": "parakeet",
    "model": "parakeet-tdt-0.6b-v3",
    "compute_type": "auto",
    "device": "auto",
    "cpu_threads": 0,
    "initial_prompt": "",
    "language": "en",
    "hotwords_file": "hotwords.txt",
    "hotwords_score": 2.0,
    "vad_filter": True,
    "auto_stop": True,
    "vad_silence_seconds": 1.4,
    "ai_polish": False,
    "async_polish": False,
    "ai_polish_provider": "openrouter",
    "ai_polish_api_key": "",
    "ai_polish_base_url": "https://openrouter.ai/api/v1",
    "ai_polish_model": "minimax/minimax-m3:free",
    "ai_polish_api_key_nvidia": "",
    "ai_polish_base_url_nvidia": "https://integrate.api.nvidia.com/v1",
    "ai_polish_model_nvidia": "nvidia/nemotron-3-nano-30b-a3b",
    "ai_polish_api_key_openrouter": "",
    "ai_polish_base_url_openrouter": "https://openrouter.ai/api/v1",
    "ai_polish_model_openrouter": "minimax/minimax-m3:free",
    "injection_delay_ms": 150,
    "restore_clipboard": False,
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
    "show_interim_preview": True,
    "streaming_model": "nemo-fast-conformer-80ms",
    "context_awareness_enabled": True,
    "mid_session_commands": True,
    "voice_app_launch_enabled": True,
    "app_launch_registry_file": "app_launch_registry.json",
}


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_base_dir() -> str:
    return os.path.dirname(sys.executable) if is_frozen() else PROJECT_ROOT


def settings_dir() -> str:
    if is_frozen():
        if sys.platform == "darwin":
            path = os.path.expanduser("~/Library/Application Support/Dictate")
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
            path = os.path.join(appdata, "Dictate")
        else:
            path = os.path.expanduser("~/.config/dictate")
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
    "engine": lambda value: value in {"whisper", "nemotron", "parakeet", "sherpa-onnx", "sense-voice"},
    "model": _is_nonempty_string,
    "compute_type": lambda value: value in _COMPUTE_TYPES,
    "device": lambda value: value in {"cpu", "cuda", "auto"},
    "cpu_threads": _is_cpu_threads,
    "initial_prompt": lambda value: isinstance(value, str),
    "language": lambda value: isinstance(value, str),
    "hotwords_file": lambda value: isinstance(value, str),
    "hotwords_score": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool) and 0.1 <= value <= 10.0,
    "vad_filter": _is_bool,
    "auto_stop": _is_bool,
    "vad_silence_seconds": _is_silence_seconds,
    "ai_polish": _is_bool,
    "async_polish": _is_bool,
    "ai_polish_provider": lambda value: value in {"nvidia", "openrouter", "openai", "custom"},
    "ai_polish_api_key": lambda value: isinstance(value, str),
    "ai_polish_base_url": lambda value: isinstance(value, str),
    "ai_polish_model": lambda value: isinstance(value, str),
    "ai_polish_api_key_nvidia": lambda value: isinstance(value, str),
    "ai_polish_base_url_nvidia": lambda value: isinstance(value, str),
    "ai_polish_model_nvidia": lambda value: isinstance(value, str),
    "ai_polish_api_key_openrouter": lambda value: isinstance(value, str),
    "ai_polish_base_url_openrouter": lambda value: isinstance(value, str),
    "ai_polish_model_openrouter": lambda value: isinstance(value, str),
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
    "show_interim_preview": _is_bool,
    "streaming_model": lambda v: isinstance(v, str) and bool(v.strip()),
    "context_awareness_enabled": _is_bool,
    "mid_session_commands": _is_bool,
    "voice_app_launch_enabled": _is_bool,
    "app_launch_registry_file": lambda v: isinstance(v, str) and bool(v.strip()),
}


def validated_settings(loaded: Any) -> dict:
    """Merge known, valid JSON values onto defaults; discard everything else."""
    result = dict(DEFAULTS)
    if not isinstance(loaded, dict):
        return result
    for key, value in loaded.items():
        if key in DEFAULTS and _VALIDATORS[key](value):
            result[key] = value

    # Migration: if hotwords_file points to derived .hotwords_sherpa.txt, migrate to canonical hotwords.txt
    hw = result.get("hotwords_file", "")
    if isinstance(hw, str) and (hw.endswith(".hotwords_sherpa.txt") or hw.endswith("/.hotwords_sherpa.txt") or hw.endswith(r"\.hotwords_sherpa.txt")):
        result["hotwords_file"] = "hotwords.txt"

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
    """Create/remove a launcher script in Windows Startup or macOS LaunchAgents."""
    if sys.platform == "win32":
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
    elif sys.platform == "darwin":
        plist_dir = os.path.expanduser("~/Library/LaunchAgents")
        plist_file = os.path.join(plist_dir, "com.dictate.app.plist")
        if enabled:
            os.makedirs(plist_dir, exist_ok=True)
            exe_path = sys.executable
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dictate.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""
            with open(plist_file, "w", encoding="utf-8") as f:
                f.write(plist_content)
        else:
            try:
                os.remove(plist_file)
            except FileNotFoundError:
                pass

