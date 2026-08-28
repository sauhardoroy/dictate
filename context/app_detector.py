"""Application and window category detection service.

Provides fast, local, lightweight classification of the active foreground application
(e.g., 'document_editor', 'email_client', 'messaging_app', 'code_agent', 'browser', 'terminal', 'unknown').
100% on-device, zero network transmission.
"""
from dataclasses import dataclass
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set

from log import get_logger

log = get_logger(__name__)

# Standard Category Taxonomy
CATEGORIES = {
    "document_editor",
    "email_client",
    "messaging_app",
    "code_agent",
    "browser",
    "terminal",
    "unknown",
}


@dataclass(frozen=True)
class ContextInfo:
    """Immutable metadata describing the active foreground window context."""
    executable_name: str = ""
    window_title: str = ""
    category: str = "unknown"
    hwnd: int = 0

    @property
    def is_known(self) -> bool:
        return self.category != "unknown"


class AppDetector:
    """Local category detector caching and matching process names and window titles."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self.executables: Dict[str, str] = {}
        self.title_patterns: List[Dict[str, str]] = []
        self.load_config()

    @staticmethod
    def _default_config_path() -> str:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, "config", "app_categories.json")

    def load_config(self):
        """Load user-editable JSON category mapping."""
        if not os.path.isfile(self.config_path):
            log.debug("Category config not found at %s", self.config_path)
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                exes = data.get("executables", {})
                if isinstance(exes, dict):
                    self.executables = {k.strip().lower(): v.strip() for k, v in exes.items() if isinstance(k, str) and isinstance(v, str)}

                patterns = data.get("title_patterns", [])
                if isinstance(patterns, list):
                    self.title_patterns = [p for p in patterns if isinstance(p, dict) and "pattern" in p and "category" in p]

            log.info("App detector loaded %d executable mappings and %d title patterns", len(self.executables), len(self.title_patterns))
        except Exception as exc:
            log.error("Failed to load app categories from %s: %s", self.config_path, exc)

    def resolve_category(self, executable_name: str, window_title: str) -> str:
        """Resolve app category from window title patterns (e.g. web apps) or executable name."""
        # 1. Check specific window title patterns first (e.g. web apps running inside browsers)
        clean_title = window_title.strip()
        if clean_title:
            for item in self.title_patterns:
                pat = item.get("pattern", "")
                cat = item.get("category", "")
                if pat and cat in CATEGORIES:
                    try:
                        if re.search(pat, clean_title):
                            return cat
                    except Exception:
                        pass

        # 2. Check executable mapping
        clean_exe = executable_name.strip().lower()
        if clean_exe in self.executables:
            cat = self.executables[clean_exe]
            if cat in CATEGORIES:
                return cat

        return "unknown"

    def get_active_context(self, excluded_hwnds: Optional[Set[int]] = None, enabled: bool = True) -> ContextInfo:
        """Query the current active foreground window and return classified ContextInfo.

        Zero exception propagation — fails silently into ContextInfo(category='unknown') on any OS error.
        """
        if not enabled:
            return ContextInfo(category="unknown")

        excluded = excluded_hwnds or set()

        if sys.platform != "win32":
            return ContextInfo(category="unknown")

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            hwnd = user32.GetForegroundWindow()
            if not hwnd or hwnd in excluded:
                return ContextInfo(category="unknown")

            # 1. Get process executable name
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            executable_name = ""

            if pid.value:
                # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                h_proc = kernel32.OpenProcess(0x1000, False, pid.value)
                if h_proc:
                    try:
                        buf = (ctypes.c_wchar * 1024)()
                        size = wintypes.DWORD(1024)
                        if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                            full_path = buf.value
                            executable_name = os.path.basename(full_path).lower()
                    finally:
                        kernel32.CloseHandle(h_proc)

            # 2. Get window title
            window_title = ""
            title_buf = (ctypes.c_wchar * 512)()
            if user32.GetWindowTextW(hwnd, title_buf, 512):
                window_title = title_buf.value

            category = self.resolve_category(executable_name, window_title)
            return ContextInfo(
                executable_name=executable_name,
                window_title=window_title,
                category=category,
                hwnd=int(hwnd),
            )
        except Exception as exc:
            log.debug("AppDetector query failed safely: %s", exc)
            return ContextInfo(category="unknown")


# Singleton instance for quick module-level access
_DETECTOR = AppDetector()


def get_active_context(excluded_hwnds: Optional[Set[int]] = None, enabled: bool = True) -> ContextInfo:
    """Convenience module-level helper returning active window ContextInfo."""
    return _DETECTOR.get_active_context(excluded_hwnds=excluded_hwnds, enabled=enabled)


def resolve_category(executable_name: str, window_title: str) -> str:
    """Convenience helper to resolve category for arbitrary app strings."""
    return _DETECTOR.resolve_category(executable_name, window_title)
