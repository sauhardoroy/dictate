"""Unit, integration, and regression tests for Feature 1: Verbatim Safe-Default Mode."""
import json
import pytest
from unittest.mock import patch, MagicMock

from punctuation.post_processor import (
    verbatim_clean,
    _is_verbatim_app,
    polish,
)


class TestVerbatimClean:
    """Test deterministic local cleanup without any network calls."""

    def test_filler_word_removal(self):
        raw = "um I think that this is uh definitely ready"
        cleaned = verbatim_clean(raw)
        assert cleaned == "I think that this is definitely ready."

    def test_multi_filler_and_hesitation_removal(self):
        raw = "erm ah we need to test this hmm right now"
        cleaned = verbatim_clean(raw)
        assert cleaned == "We need to test this right now."

    def test_immediate_word_repetition_removal(self):
        raw = "the the project will will succeed"
        cleaned = verbatim_clean(raw)
        assert cleaned == "The project will succeed."

    def test_phrase_repetition_and_false_starts(self):
        raw = "I want to I want to review the deployment script"
        cleaned = verbatim_clean(raw)
        assert cleaned == "I want to review the deployment script."

    def test_punctuation_and_capitalization(self):
        assert verbatim_clean("hello world") == "Hello world."
        assert verbatim_clean("is this working?") == "Is this working?"
        assert verbatim_clean("great job!") == "Great job!"

    def test_hotwords_casing_preserved(self, tmp_path):
        hw_path = tmp_path / "hotwords.txt"
        hw_path.write_text("PyTorch\nCUDA\nOpenAI\n", encoding="utf-8")
        raw = "we are training on pytorch with cuda"
        cleaned = verbatim_clean(raw, hotwords_file=str(hw_path))
        assert cleaned == "We are training on PyTorch with CUDA."

    def test_zero_network_calls_guaranteed(self):
        """Mock urllib to guarantee verbatim_clean never triggers an HTTP request."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = verbatim_clean("um hello the the world")
            assert not mock_urlopen.called
            assert result == "Hello the world."


class TestIsVerbatimApp:
    """Test app context classification for verbatim routing."""

    def test_category_matching(self):
        assert _is_verbatim_app(category="document_editor") is True
        assert _is_verbatim_app(category="code_agent") is True
        assert _is_verbatim_app(category="messaging_app") is False
        assert _is_verbatim_app(category="email_client") is False
        assert _is_verbatim_app(category="unknown") is False

    def test_executable_matching(self):
        assert _is_verbatim_app(app_name="winword.exe") is True
        assert _is_verbatim_app(app_name="notepad.exe") is True
        assert _is_verbatim_app(app_name="code.exe") is True
        assert _is_verbatim_app(app_name="slack.exe") is False
        assert _is_verbatim_app(app_name="chrome.exe") is False

    def test_window_title_pattern_matching(self):
        assert _is_verbatim_app(app_name="chrome.exe", window_title="Quarterly Plan - Google Docs - Google Chrome") is True
        assert _is_verbatim_app(app_name="chrome.exe", window_title="Wikipedia - Google Chrome") is False


class TestPolishModeRouting:
    """Test routing across 'auto', 'verbatim', and 'per_app' modes."""

    def test_verbatim_mode_overrides_ai_polish(self):
        settings = {
            "ai_polish": True,
            "polish_mode": "verbatim",
            "ai_polish_api_key": "sk-test",
            "ai_polish_base_url": "https://api.example.com",
            "ai_polish_model": "test-model",
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            out = polish("um this is a verbatim test", settings=settings)
            assert not mock_urlopen.called
            assert out == "This is a verbatim test."

    def test_per_app_mode_routes_document_editor_to_verbatim(self):
        settings = {
            "ai_polish": True,
            "polish_mode": "per_app",
            "ai_polish_api_key": "sk-test",
            "ai_polish_base_url": "https://api.example.com",
            "ai_polish_model": "test-model",
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            out = polish(
                "um dictating into word document",
                settings=settings,
                target_app_name="winword.exe",
                target_category="document_editor",
            )
            # Must bypass cloud polish
            assert not mock_urlopen.called
            assert out == "Dictating into word document."

    def test_auto_mode_preserves_default_behavior(self):
        settings = {
            "ai_polish": False,
            "polish_mode": "auto",
        }
        out = polish("hello world", settings=settings)
        assert out == "Hello world."
