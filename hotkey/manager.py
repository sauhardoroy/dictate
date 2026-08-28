"""Global hotkey registration natively via Win32 GetAsyncKeyState on Windows and pynput on macOS.

Supports modifier combos like 'ctrl+shift+p', 'ctrl+alt+[', 'alt+f9', or plain keys like 'f9'.
"""
import sys
import threading
import time

user32 = None
if sys.platform == "win32":
    try:
        import ctypes
        user32 = ctypes.windll.user32
    except Exception:
        user32 = None

# Map common keys and names to Virtual-Key codes
NAME_TO_VK = {
    # Function keys F1 - F24
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "f13": 0x7C, "f14": 0x7D, "f15": 0x7E, "f16": 0x7F,
    "f17": 0x80, "f18": 0x81, "f19": 0x82, "f20": 0x83,
    "f21": 0x84, "f22": 0x85, "f23": 0x86, "f24": 0x87,
    # Standard control & navigation keys
    "esc": 0x1B, "escape": 0x1B, "enter": 0x0D, "return": 0x0D, "space": 0x20,
    "tab": 0x09, "backspace": 0x08, "capslock": 0x14, "caps_lock": 0x14,
    "insert": 0x2D, "delete": 0x2E, "del": 0x2E,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "page_up": 0x21, "pgup": 0x21,
    "pagedown": 0x22, "page_down": 0x22, "pgdn": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "printscreen": 0x2C, "prtscn": 0x2C, "pause": 0x13, "scrolllock": 0x91,
    # Modifiers
    "shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12, "option": 0x12,
    "win": 0x5B, "windows": 0x5B, "meta": 0x5B, "super": 0x5B, "cmd": 0x5B, "command": 0x5B,
    # Brackets, punctuation and OEM symbols
    "[": 0xDB, "{": 0xDB, "left bracket": 0xDB, "left_bracket": 0xDB,
    "bracketleft": 0xDB, "braceleft": 0xDB, "open bracket": 0xDB, "open_bracket": 0xDB,
    "]": 0xDD, "}": 0xDD, "right bracket": 0xDD, "right_bracket": 0xDD,
    "bracketright": 0xDD, "braceright": 0xDD, "close bracket": 0xDD, "close_bracket": 0xDD,
    "\\": 0xDC, "|": 0xDC, "backslash": 0xDC, "bar": 0xDC,
    ";": 0xBA, ":": 0xBA, "semicolon": 0xBA, "colon": 0xBA,
    "'": 0xDE, '"': 0xDE, "quote": 0xDE, "singlequote": 0xDE, "apostrophe": 0xDE, "doublequote": 0xDE,
    ",": 0xBC, "<": 0xBC, "comma": 0xBC, "less": 0xBC,
    ".": 0xBE, ">": 0xBE, "period": 0xBE, "dot": 0xBE, "greater": 0xBE,
    "/": 0xBF, "?": 0xBF, "slash": 0xBF, "forwardslash": 0xBF, "question": 0xBF,
    "-": 0xBD, "_": 0xBD, "minus": 0xBD, "dash": 0xBD, "hyphen": 0xBD, "underscore": 0xBD,
    "=": 0xBB, "+": 0xBB, "equal": 0xBB, "equals": 0xBB, "plus": 0xBB,
    "`": 0xC0, "~": 0xC0, "backtick": 0xC0, "grave": 0xC0, "tilde": 0xC0,
    # Numpad
    "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63, "numpad4": 0x64,
    "numpad5": 0x65, "numpad6": 0x66, "numpad7": 0x67, "numpad8": 0x68, "numpad9": 0x69,
    "numlock": 0x90,
}

VK_TO_NAME = {v: k for k, v in NAME_TO_VK.items()}

# Modifier VK codes
MODIFIER_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C}  # shift, ctrl, alt, win
MODIFIER_NAMES = {"shift", "ctrl", "control", "alt", "option", "win", "windows", "meta", "super", "cmd", "command"}


def get_vk(key_str: str) -> int:
    """Resolve a single key name to a virtual-key code."""
    key_str = key_str.lower().strip()
    if key_str in NAME_TO_VK:
        return NAME_TO_VK[key_str]
    if len(key_str) == 1:
        if key_str.isalnum():
            return ord(key_str.upper())
        if user32:
            try:
                res = user32.VkKeyScanW(ord(key_str))
                if res != -1 and (res & 0xFF) != 0:
                    return res & 0xFF
            except Exception:
                pass
    return 0


def get_name(vk: int) -> str:
    """Get human-readable name for a virtual-key code."""
    if vk in VK_TO_NAME:
        return VK_TO_NAME[vk]
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    return ""


def is_modifier(vk: int) -> bool:
    """Return True if the VK code is a modifier (Ctrl, Shift, Alt, Win)."""
    return vk in MODIFIER_VKS


def parse_combo(combo_str: str) -> tuple[list[int], int]:
    """Parse a combo string like 'ctrl+shift+p' or 'ctrl+alt+[' into (modifier_vks, main_vk).

    Returns ([modifier_vk, ...], main_vk). If no modifiers, the list is empty.
    """
    parts = [p.strip().lower() for p in combo_str.split("+")]
    if not parts:
        return [], 0

    modifier_vks = []
    main_vk = 0

    for part in parts:
        vk = get_vk(part)
        if part in MODIFIER_NAMES:
            modifier_vks.append(vk)
        else:
            main_vk = vk

    return modifier_vks, main_vk


def build_combo_name(modifier_names: list[str], key_name: str) -> str:
    """Build a human-readable combo string like 'ctrl+shift+p'."""
    # Canonical order: ctrl, alt, shift, win, then the key
    order = {"ctrl": 0, "control": 0, "alt": 1, "option": 1, "shift": 2, "win": 3, "windows": 3, "meta": 3, "cmd": 3, "command": 3}
    sorted_mods = sorted(modifier_names, key=lambda m: order.get(m, 99))
    parts = sorted_mods + [key_name]
    return "+".join(parts)


def _is_key_down(vk: int) -> bool:
    if not user32:
        return False
    if vk in (0x5B, 0x5C):
        return bool((user32.GetAsyncKeyState(0x5B) & 0x8000) or (user32.GetAsyncKeyState(0x5C) & 0x8000))
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


class HotkeyManager:
    def __init__(self, key, mode, on_press, on_release=None):
        self.key = key
        self.mode = mode  # "ptt" | "toggle" | "cancel"
        self.on_press = on_press
        self.on_release = on_release
        self._running = False
        self._thread = None
        self._is_down = False
        self._mac_listener = None

        self._modifier_vks, self._main_vk = parse_combo(key)

    def register(self):
        self.unregister()
        # Re-parse in case key was changed after construction
        self._modifier_vks, self._main_vk = parse_combo(self.key)
        if not self._main_vk:
            raise RuntimeError(f"Unsupported hotkey: {self.key}")

        self._running = True

        if sys.platform == "win32" and user32 is not None:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        else:
            self._start_mac_listener()

    def _loop(self):
        while self._running:
            # Check: all modifiers held AND main key pressed
            main_down = _is_key_down(self._main_vk)
            mods_down = all(_is_key_down(vk) for vk in self._modifier_vks) if self._modifier_vks else True

            combo_active = main_down and mods_down

            if combo_active and not self._is_down:
                self._is_down = True
                if self.on_press:
                    self.on_press()
            elif not combo_active and self._is_down:
                self._is_down = False
                if self.mode == "ptt" and self.on_release:
                    self.on_release()
            time.sleep(0.02)  # 20ms poll rate is highly responsive, ~0% CPU

    def _start_mac_listener(self):
        try:
            from pynput import keyboard

            self._current_keys = set()

            def _normalize_key(k) -> str:
                if k is None:
                    return ""
                try:
                    if isinstance(k, keyboard.Key):
                        name = k.name.lower()
                        if name.startswith("ctrl"):
                            return "ctrl"
                        if name.startswith("shift"):
                            return "shift"
                        if name.startswith("alt"):
                            return "alt"
                        if name.startswith("cmd"):
                            return "cmd"
                        return name
                    if hasattr(k, "char") and k.char:
                        return k.char.lower()
                    if hasattr(k, "vk") and k.vk:
                        name = get_name(k.vk)
                        if name:
                            return name.lower()
                except Exception:
                    pass
                return str(k).lower().replace("key.", "")

            # Parse required modifiers and main key
            parts = [p.strip().lower() for p in self.key.split("+")]
            req_mods = set()
            req_main = ""
            for p in parts:
                if p in MODIFIER_NAMES:
                    # Normalize modifier names to canonical ('ctrl', 'alt', 'shift', 'cmd')
                    if p in ("control", "ctrl"):
                        req_mods.add("ctrl")
                    elif p in ("option", "alt"):
                        req_mods.add("alt")
                    elif p == "shift":
                        req_mods.add("shift")
                    elif p in ("win", "windows", "meta", "super", "cmd", "command"):
                        req_mods.add("cmd")
                else:
                    req_main = p

            def _is_combo_active():
                if req_mods and not req_mods.issubset(self._current_keys):
                    return False
                if req_main and req_main not in self._current_keys:
                    return False
                return True

            def _on_press(k):
                norm = _normalize_key(k)
                if norm:
                    self._current_keys.add(norm)
                if _is_combo_active() and not self._is_down:
                    self._is_down = True
                    if self.on_press:
                        self.on_press()

            def _on_release(k):
                norm = _normalize_key(k)
                if norm:
                    self._current_keys.discard(norm)
                if not _is_combo_active() and self._is_down:
                    self._is_down = False
                    if self.mode == "ptt" and self.on_release:
                        self.on_release()

            self._mac_listener = keyboard.Listener(
                on_press=_on_press,
                on_release=_on_release,
            )
            self._mac_listener.start()
        except Exception:
            # Fallback mock/noop for non-macOS test environments
            pass

    def unregister(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.1)
            self._thread = None
        if self._mac_listener:
            try:
                self._mac_listener.stop()
            except Exception:
                pass
            self._mac_listener = None
        self._is_down = False
        if hasattr(self, "_current_keys"):
            self._current_keys.clear()


