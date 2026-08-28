"""Automated privacy guardrail and cloud payload containment tests.

Ensures that no window titles, process names, clipboard contents, screenshots,
or textbox buffers are ever transmitted to cloud AI Polish endpoints.
"""
import json
import urllib.request
import pytest
from unittest.mock import patch, MagicMock

from config import settings as settings_module
from punctuation.post_processor import _llm_polish


def test_settings_context_awareness_enabled_validation(tmp_path, monkeypatch):
    """Verify context_awareness_enabled setting exists, defaults to True, and validates correctly."""
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "settings_path", lambda: str(path))

    settings = settings_module.Settings()
    assert settings["context_awareness_enabled"] is True

    settings["context_awareness_enabled"] = False
    assert settings["context_awareness_enabled"] is False

    with pytest.raises(ValueError):
        settings["context_awareness_enabled"] = "invalid_string"


def test_cloud_polish_payload_never_contains_system_or_window_metadata():
    """Verify the JSON payload sent to the LLM polish endpoint strictly isolates transcript data

    and contains zero window titles, process names, clipboard strings, or environment metadata.
    """
    captured_payloads = []

    def fake_urlopen(req, timeout=None):
        if hasattr(req, "data") and req.data:
            payload = json.loads(req.data.decode("utf-8"))
            captured_payloads.append(payload)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": "Hello world, this is a clean dictation."
                }
            }]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        return mock_response

    mock_settings = {
        "ai_polish_api_key": "sk-test-fake-key",
        "ai_polish_base_url": "https://api.example.com/v1",
        "ai_polish_model": "test-model",
    }

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = _llm_polish(
            text="hello world this is a clean dictation",
            settings=mock_settings,
        )

    assert len(captured_payloads) == 1
    payload = captured_payloads[0]

    # Verify standard OpenAI-compatible structure
    assert "model" in payload
    assert "messages" in payload
    assert payload["model"] == "test-model"

    # Verify forbidden metadata keys are completely absent from top-level payload
    forbidden_keys = {
        "window_title", "window", "process_name", "process", "app", "target_app",
        "clipboard", "screenshot", "screen", "ocr", "buffer", "device_id",
        "username", "hostname", "context", "metadata"
    }
    found_forbidden = forbidden_keys.intersection(payload.keys())
    assert not found_forbidden, f"Payload contained forbidden metadata keys: {found_forbidden}"

    # Verify message contents only contain role and content strings
    messages = payload["messages"]
    for msg in messages:
        assert set(msg.keys()) == {"role", "content"}
        assert msg["role"] in {"system", "user"}
        
        # User message must encapsulate raw transcript in XML tags
        if msg["role"] == "user":
            assert "<raw_transcript>" in msg["content"]
            assert "</raw_transcript>" in msg["content"]
            assert "hello world this is a clean dictation" in msg["content"]


def test_codebase_zero_screenshot_or_ocr_imports():
    """Verify that core dictation pipeline modules do not import screenshot or optical recognition APIs."""
    import inspect
    from injection import typer
    from punctuation import post_processor, voice_commands

    typer_source = inspect.getsource(typer)
    post_source = inspect.getsource(post_processor)
    voice_source = inspect.getsource(voice_commands)

    for src in (typer_source, post_source, voice_source):
        # Hard boundary: No screen capture or OCR libraries
        assert "ImageGrab" not in src
        assert "pytesseract" not in src
        assert "easyocr" not in src
        assert "mss" not in src
        assert "desktop_capture" not in src
