"""Sanitize transcribed text before injection into potentially dangerous targets.

When Dictate pastes into a terminal (cmd, PowerShell, Windows Terminal, etc.),
a trailing newline would auto-execute whatever was pasted. Whisper can also
hallucinate command-like strings. This module detects terminal targets and
applies safety measures:

- Strips trailing newlines/carriage returns (prevents accidental execution)
- Detects dangerous command patterns and logs a warning
- Optionally blocks injection entirely for high-risk patterns
"""
import os
import re
import sys

from log import get_logger

log = get_logger(__name__)

user32 = None
kernel32 = None
psapi = None

if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
    except Exception as exc:
        log.warning("Win32 API bindings could not be initialized in sanitizer: %s", exc)

# Terminal process names (lowercase). If the target window belongs to one of
# these, we strip trailing newlines and check for dangerous patterns.
TERMINAL_PROCESSES = frozenset({
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "windowsterminal.exe",
    "wt.exe",
    "conhost.exe",
    "mintty.exe",         # Git Bash
    "bash.exe",
    "wsl.exe",
    "ubuntu.exe",
    "alacritty.exe",
    "alacritty",
    "hyper.exe",
    "hyper",
    "terminus.exe",
    "tabby.exe",
    "tabby",
    "putty.exe",
    "kitty.exe",
    "kitty",
    "mobaxterm.exe",
    "securecrt.exe",
    "xterm.exe",
    "terminal",           # macOS Terminal
    "iterm2",             # macOS iTerm2
    "iterm",
    "wezterm-gui",
    "wezterm",
    "warp",
})


# Patterns that are dangerous if pasted into a shell and executed.
# These are checked case-insensitively against the full text.
_DANGEROUS_PATTERNS = [
    # File system destruction
    re.compile(r"\brm\s+(-\w+\s+)*(/|~|\.\.)", re.IGNORECASE),
    re.compile(r"\bdel\s+/[sfq]", re.IGNORECASE),
    re.compile(r"\brmdir\s+/s", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
    re.compile(r"\brd\s+/s", re.IGNORECASE),

    # Privilege escalation / system modification
    re.compile(r"\bnet\s+user\b", re.IGNORECASE),
    re.compile(r"\breg\s+(add|delete)\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+\d{3,4}\s+/", re.IGNORECASE),
    re.compile(r"\bchown\s+.*\s+/", re.IGNORECASE),

    # Download and execute
    re.compile(r"\bcurl\b.*\|\s*(bash|sh|powershell|pwsh)", re.IGNORECASE),
    re.compile(r"\bwget\b.*\|\s*(bash|sh|powershell|pwsh)", re.IGNORECASE),
    re.compile(r"Invoke-WebRequest.*\|\s*Invoke-Expression", re.IGNORECASE),
    re.compile(r"\biex\b.*\bNew-Object\b", re.IGNORECASE),
    re.compile(r"IEX\s*\(", re.IGNORECASE),

    # Disk / partition
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=.*/dev/", re.IGNORECASE),

    # Shutdown / reboot
    re.compile(r"\bshutdown\s+[/-]", re.IGNORECASE),

    # Fork bomb patterns
    re.compile(r":\(\)\{.*\};\s*:", re.IGNORECASE),
]


def _get_process_name(hwnd: int) -> str:
    """Get the executable name of the process that owns the given window handle."""
    if not hwnd:
        return ""
    try:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            buf = (ctypes.c_wchar * 260)()
            size = wintypes.DWORD(260)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return os.path.basename(buf.value).lower()
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        pass
    return ""


def is_terminal(hwnd: int) -> bool:
    """Return True if the window handle belongs to a known terminal process."""
    name = _get_process_name(hwnd)
    return name in TERMINAL_PROCESSES


def check_dangerous_patterns(text: str) -> list[str]:
    """Return a list of human-readable warnings for any dangerous patterns found."""
    warnings = []
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(text):
            warnings.append(f"Matched dangerous pattern: {pattern.pattern!r}")
    return warnings


def sanitize(text: str, target_hwnd: int = 0) -> tuple[str, list[str]]:
    """Sanitize text before injection.

    Returns:
        (sanitized_text, warnings) — warnings is a list of human-readable
        messages describing what was changed and why. Empty list means the
        text was safe.
    """
    if not text:
        return text, []

    warnings = []
    result = text
    terminal = is_terminal(target_hwnd)

    if terminal:
        # Strip trailing newlines / carriage returns — in a terminal these
        # would auto-execute whatever was pasted.
        stripped = result.rstrip("\n\r")
        if stripped != result:
            warnings.append("Stripped trailing newlines (prevents auto-execution in terminal)")
            result = stripped

        # Replace interior newlines with spaces — multi-line paste in a
        # terminal executes each line sequentially.
        if "\n" in result or "\r" in result:
            result = re.sub(r"[\r\n]+", " ", result)
            warnings.append("Replaced interior newlines with spaces (terminal target)")

    # Check for dangerous command patterns regardless of target
    danger_warnings = check_dangerous_patterns(result)
    if danger_warnings:
        log.warning(
            "Potentially dangerous text detected (target_hwnd=%s, terminal=%s): %s",
            target_hwnd, terminal, "; ".join(danger_warnings)
        )
        warnings.extend(danger_warnings)

    return result, warnings
