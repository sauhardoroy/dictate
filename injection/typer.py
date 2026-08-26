"""Text injection: robust Windows clipboard set -> Ctrl+V -> optional restore."""
import ctypes
from ctypes import wintypes
import threading
import time

import pyperclip

from log import get_logger

log = get_logger(__name__)

# Win32 API constants & setup
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040
GHND = GMEM_MOVEABLE | GMEM_ZEROINIT

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL


def activate_window(hwnd: int) -> bool:
    """Safely restore foreground focus to the given HWND using Win32 API."""
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    cur_fg = user32.GetForegroundWindow()
    if cur_fg == hwnd:
        return True

    cur_thread = kernel32.GetCurrentThreadId()
    fg_thread = user32.GetWindowThreadProcessId(cur_fg, None) if cur_fg else 0
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)

    if fg_thread and fg_thread != cur_thread:
        user32.AttachThreadInput(cur_thread, fg_thread, True)
    if target_thread and target_thread != cur_thread:
        user32.AttachThreadInput(cur_thread, target_thread, True)

    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)

    if fg_thread and fg_thread != cur_thread:
        user32.AttachThreadInput(cur_thread, fg_thread, False)
    if target_thread and target_thread != cur_thread:
        user32.AttachThreadInput(cur_thread, target_thread, False)

    time.sleep(0.04)  # Allow Windows to settle focus transfer
    return True


def copy_to_clipboard(text: str, max_retries: int = 10, retry_delay: float = 0.02) -> bool:
    """Reliably copy Unicode text to the Windows clipboard with retries."""
    if text is None:
        return False
    text = str(text)

    # Method 1: Direct Win32 API with retry backoff
    for attempt in range(max_retries):
        if user32.OpenClipboard(None):
            try:
                user32.EmptyClipboard()
                encoded = text.encode("utf-16-le") + b"\x00\x00"
                h_global = kernel32.GlobalAlloc(GHND, len(encoded))
                if h_global:
                    ptr = kernel32.GlobalLock(h_global)
                    if ptr:
                        ctypes.memmove(ptr, encoded, len(encoded))
                        kernel32.GlobalUnlock(h_global)
                        user32.SetClipboardData(CF_UNICODETEXT, h_global)
                        return True
            finally:
                user32.CloseClipboard()
        time.sleep(retry_delay)
    log.debug("win32 clipboard copy failed after %d attempts, falling back", max_retries)

    # Method 2: Fallback to pyperclip
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        pass

    return False


def get_clipboard_text(max_retries: int = 5, retry_delay: float = 0.02) -> str:
    """Get Unicode text from Windows clipboard with retries."""
    for _ in range(max_retries):
        if user32.OpenClipboard(None):
            try:
                if user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                    h_global = user32.GetClipboardData(CF_UNICODETEXT)
                    if h_global:
                        ptr = kernel32.GlobalLock(h_global)
                        if ptr:
                            try:
                                val = ctypes.c_wchar_p(ptr).value
                                return val if val is not None else ""
                            finally:
                                kernel32.GlobalUnlock(h_global)
            finally:
                user32.CloseClipboard()
        time.sleep(retry_delay)

    try:
        return pyperclip.paste() or ""
    except Exception:
        return ""


# Constants for SendInput
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_ALT = 0x12
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_BACK = 0x08
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56
VK_X = 0x58
VK_Y = 0x59
VK_Z = 0x5A

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)))

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = (("ki", KEYBDINPUT),
                    ("mi", ctypes.c_byte * 28),
                    ("hi", ctypes.c_byte * 32))
    _anonymous_ = ("i",)
    _fields_ = (("type", wintypes.DWORD),
                ("i", _I))

def _send_shortcut(modifiers: list[int], vk: int):
    """Send a modifier + key combination using Win32 SendInput."""
    count = (len(modifiers) * 2) + 2
    inputs = (INPUT * count)()
    idx = 0

    # Modifiers down
    for mod in modifiers:
        inputs[idx].type = INPUT_KEYBOARD
        inputs[idx].ki.wVk = mod
        idx += 1

    # Main key down
    inputs[idx].type = INPUT_KEYBOARD
    inputs[idx].ki.wVk = vk
    idx += 1

    # Main key up
    inputs[idx].type = INPUT_KEYBOARD
    inputs[idx].ki.wVk = vk
    inputs[idx].ki.dwFlags = KEYEVENTF_KEYUP
    idx += 1

    # Modifiers up (reverse order)
    for mod in reversed(modifiers):
        inputs[idx].type = INPUT_KEYBOARD
        inputs[idx].ki.wVk = mod
        inputs[idx].ki.dwFlags = KEYEVENTF_KEYUP
        idx += 1

    user32.SendInput(count, ctypes.byref(inputs), ctypes.sizeof(INPUT))

def _send_ctrl_v():
    _send_shortcut([VK_CONTROL], VK_V)

def _send_unicode_string(text: str):
    inputs = (INPUT * (len(text) * 2))()
    for i, char in enumerate(text):
        # Key down
        inputs[i*2].type = INPUT_KEYBOARD
        inputs[i*2].ki.wVk = 0
        inputs[i*2].ki.wScan = ord(char)
        inputs[i*2].ki.dwFlags = KEYEVENTF_UNICODE
        # Key up
        inputs[i*2+1].type = INPUT_KEYBOARD
        inputs[i*2+1].ki.wVk = 0
        inputs[i*2+1].ki.wScan = ord(char)
        inputs[i*2+1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    user32.SendInput(len(inputs), ctypes.byref(inputs), ctypes.sizeof(INPUT))


def execute_action(action: str, target_hwnd: int = 0) -> bool:
    """Execute a system editing action (undo, redo, select_all, copy, cut, paste, etc.)."""
    if target_hwnd and not activate_window(target_hwnd):
        log.warning("action aborted: unable to activate target hwnd=%s", target_hwnd)
        return False

    action_map = {
        "undo": ([VK_CONTROL], VK_Z),
        "redo": ([VK_CONTROL], VK_Y),
        "select_all": ([VK_CONTROL], VK_A),
        "copy": ([VK_CONTROL], VK_C),
        "cut": ([VK_CONTROL], VK_X),
        "paste": ([VK_CONTROL], VK_V),
        "enter": ([], VK_RETURN),
        "tab": ([], VK_TAB),
        "backspace": ([], VK_BACK),
    }

    if action not in action_map:
        log.warning("unknown action: %s", action)
        return False

    mods, vk = action_map[action]
    _send_shortcut(mods, vk)
    log.info("executed voice action: %s in hwnd=%s", action, target_hwnd)
    return True


def paste_text(text: str, restore: bool = False, delay_ms: int = 150, target_hwnd: int = 0) -> bool:
    """Paste ``text`` into the captured target window.

    Returns ``True`` when an injection was sent. If a captured window cannot
    be restored, returns ``False`` rather than risking a paste into a different
    application that happened to receive foreground focus.
    """
    if not text:
        return False

    # Restore the text field the user was working in before recording. This is
    # deliberately fail-closed: protecting the destination is more important
    # than inserting a transcript somewhere unintended.
    if target_hwnd and not activate_window(target_hwnd):
        log.warning("paste aborted: unable to activate target hwnd=%s", target_hwnd)
        return False

    backup = None
    have_backup = False
    if restore:
        try:
            backup = get_clipboard_text()
            have_backup = bool(backup)
        except Exception:
            pass

    # 1. Place text on clipboard
    copied = copy_to_clipboard(text)

    # 2. Trigger paste in active window natively
    if copied:
        _send_ctrl_v()
        log.debug("pasted via Ctrl+V (%d chars)%s", len(text),
                  f" to hwnd={target_hwnd}" if target_hwnd else "")
    else:
        _send_unicode_string(text)
        log.warning("clipboard copy failed; fell back to unicode SendInput (%d chars)", len(text))

    # 3. Restore previous clipboard only if explicitly requested
    if restore and have_backup:
        threading.Timer(
            max(delay_ms, 100) / 1000.0,
            lambda: copy_to_clipboard(backup),
        ).start()

    return True

