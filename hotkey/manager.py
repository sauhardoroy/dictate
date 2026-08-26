"""Global hotkey registration natively via Win32 GetAsyncKeyState.

Supports modifier combos like 'ctrl+shift+p', 'alt+f9', or plain keys like 'f9'.
"""
import ctypes
import threading
import time

user32 = ctypes.windll.user32

# Map common keys to Virtual-Key codes
NAME_TO_VK = {
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "esc": 0x1B, "escape": 0x1B, "enter": 0x0D, "space": 0x20,
    "tab": 0x09, "backspace": 0x08, "shift": 0x10, "ctrl": 0x11, "alt": 0x12
}

VK_TO_NAME = {v: k for k, v in NAME_TO_VK.items()}

# Modifier VK codes
MODIFIER_VKS = {0x10, 0x11, 0x12}  # shift, ctrl, alt
MODIFIER_NAMES = {"shift", "ctrl", "alt"}


def get_vk(key_str: str) -> int:
    """Resolve a single key name to a virtual-key code."""
    key_str = key_str.lower().strip()
    if key_str in NAME_TO_VK:
        return NAME_TO_VK[key_str]
    if len(key_str) == 1:
        # A-Z, 0-9 map directly to ascii
        return ord(key_str.upper())
    return 0


def get_name(vk: int) -> str:
    """Get human-readable name for a virtual-key code."""
    if vk in VK_TO_NAME:
        return VK_TO_NAME[vk]
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    return ""


def is_modifier(vk: int) -> bool:
    """Return True if the VK code is a modifier (Ctrl, Shift, Alt)."""
    return vk in MODIFIER_VKS


def parse_combo(combo_str: str) -> tuple[list[int], int]:
    """Parse a combo string like 'ctrl+shift+p' into (modifier_vks, main_vk).

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
    # Canonical order: ctrl, shift, alt, then the key
    order = {"ctrl": 0, "shift": 1, "alt": 2}
    sorted_mods = sorted(modifier_names, key=lambda m: order.get(m, 99))
    parts = sorted_mods + [key_name]
    return "+".join(parts)


def _is_key_down(vk: int) -> bool:
    return (user32.GetAsyncKeyState(vk) & 0x8000) != 0


class HotkeyManager:
    def __init__(self, key, mode, on_press, on_release=None):
        self.key = key
        self.mode = mode  # "ptt" | "toggle" | "cancel"
        self.on_press = on_press
        self.on_release = on_release
        self._running = False
        self._thread = None
        self._is_down = False

        self._modifier_vks, self._main_vk = parse_combo(key)

    def register(self):
        self.unregister()
        # Re-parse in case key was changed after construction
        self._modifier_vks, self._main_vk = parse_combo(self.key)
        if not self._main_vk:
            raise RuntimeError(f"Unsupported hotkey: {self.key}")
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

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

    def unregister(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.1)
            self._thread = None
        self._is_down = False
