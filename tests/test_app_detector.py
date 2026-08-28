"""Unit and performance tests for Feature 3: App-Category Detection Foundation."""
import time
import pytest
from unittest.mock import patch, MagicMock

from context.app_detector import (
    AppDetector,
    ContextInfo,
    get_active_context,
    resolve_category,
    CATEGORIES,
)


@pytest.fixture
def detector(tmp_path):
    # Use default detector
    return AppDetector()


class TestAppCategoryResolution:
    """Test category resolution against default taxonomy."""

    @pytest.mark.parametrize("exe,title,expected_category", [
        # Document Editors
        ("winword.exe", "Report.docx", "document_editor"),
        ("notepad.exe", "notes.txt - Notepad", "document_editor"),
        ("writer.exe", "Document - LibreOffice Writer", "document_editor"),
        ("acrobat.exe", "Manual.pdf - Adobe Acrobat", "document_editor"),
        ("obsidian.exe", "Notes - Obsidian", "document_editor"),
        ("chrome.exe", "Quarterly Plan - Google Docs - Google Chrome", "document_editor"),

        # Email Clients
        ("outlook.exe", "Inbox - Outlook", "email_client"),
        ("thunderbird.exe", "Inbox - Mozilla Thunderbird", "email_client"),
        ("chrome.exe", "Inbox (12) - user@gmail.com - Gmail - Google Chrome", "email_client"),

        # Messaging Apps
        ("slack.exe", "general - Acme Corp Slack", "messaging_app"),
        ("discord.exe", "#dev - Discord", "messaging_app"),
        ("telegram.exe", "Telegram", "messaging_app"),
        ("whatsapp.exe", "WhatsApp", "messaging_app"),
        ("msedge.exe", "WhatsApp Web - Microsoft Edge", "messaging_app"),

        # Code Agents / IDEs
        ("code.exe", "app.py - Dictate - Visual Studio Code", "code_agent"),
        ("cursor.exe", "settings.py - Cursor", "code_agent"),
        ("windsurf.exe", "main.py - Windsurf", "code_agent"),
        ("pycharm64.exe", "dictate – app.py [dictate]", "code_agent"),

        # Terminals
        ("windowsterminal.exe", "PowerShell", "terminal"),
        ("powershell.exe", "Administrator: Windows PowerShell", "terminal"),
        ("cmd.exe", "Command Prompt", "terminal"),
        ("alacritty.exe", "Alacritty", "terminal"),

        # Browsers
        ("chrome.exe", "Wikipedia, the free encyclopedia - Google Chrome", "browser"),
        ("firefox.exe", "Mozilla Firefox", "browser"),
        ("msedge.exe", "Microsoft Edge", "browser"),
        ("brave.exe", "Brave Browser", "browser"),

        # Unrecognized / Unknown
        ("random_game.exe", "Game Window", "unknown"),
        ("unknown_tool.exe", "", "unknown"),
        ("", "", "unknown"),
    ])
    def test_category_resolution(self, detector, exe, title, expected_category):
        cat = detector.resolve_category(exe, title)
        assert cat == expected_category
        assert cat in CATEGORIES


class TestContextInfoAndSafety:
    """Test ContextInfo dataclass, disable toggle, and safe error handling."""

    def test_context_awareness_disabled_returns_unknown(self):
        ctx = get_active_context(enabled=False)
        assert isinstance(ctx, ContextInfo)
        assert ctx.category == "unknown"
        assert ctx.is_known is False

    def test_excluded_hwnd_returns_unknown(self):
        with patch("sys.platform", "win32"), \
             patch("ctypes.windll.user32.GetForegroundWindow", return_value=99999):
            ctx = get_active_context(excluded_hwnds={99999}, enabled=True)
            assert ctx.category == "unknown"

    def test_exception_in_os_query_fails_safely(self):
        with patch("sys.platform", "win32"), \
             patch("ctypes.windll.user32.GetForegroundWindow", side_effect=RuntimeError("OS fault")):
            ctx = get_active_context(enabled=True)
            assert ctx.category == "unknown"


class TestDetectorLatency:
    """Ensure category resolution runs in <10ms for instant session startup."""

    def test_resolution_speed_under_10ms(self, detector):
        start = time.perf_counter()
        for _ in range(100):
            detector.resolve_category("code.exe", "app.py - Visual Studio Code")
        elapsed = (time.perf_counter() - start) / 100
        assert elapsed < 0.010, f"Category resolution exceeded 10ms target: {elapsed*1000:.2f}ms"
