# -*- coding: utf-8 -*-
"""Tests for the post-processing layer: hallucination filter and light polish."""
from punctuation.post_processor import polish, _light_polish


def test_polish_strips_and_capitalizes():
    assert polish("  hello   world ") == "Hello world."


def test_polish_adds_terminal_period():
    assert polish("the quick brown fox") == "The quick brown fox."


def test_polish_preserves_existing_terminal_punctuation():
    assert polish("already ended!") == "Already ended!"


def test_polish_fixes_space_before_punctuation():
    assert _light_polish("space before , punctuation") == "Space before, punctuation."


def test_polish_empty_string_returns_empty():
    assert polish("") == ""


def test_polish_blocks_hallucinations():
    assert polish("thank you.") == ""
    assert polish("thanks for watching!") == ""
    assert polish("you") == ""
    assert polish("bye.") == ""


def test_light_polish_capitalizes_and_terminates():
    assert _light_polish("hello") == "Hello."
    assert _light_polish("wait, what?") == "Wait, what?"


def test_polish_collapses_internal_whitespace():
    assert polish("too    much     space") == "Too much space."


def test_hotwords_casing_restoration(tmp_path):
    hw_file = tmp_path / "test_hotwords.txt"
    hw_file.write_text("PyTorch:2.0\nKubernetes:2.0\nREST API:2.0\nNext.js:2.0\n", encoding="utf-8")

    sample = "i am using pytorch with next.js and kubernetes on rest api"
    result = polish(sample, settings={"hotwords_file": str(hw_file), "ai_polish": False})
    assert "PyTorch" in result
    assert "Next.js" in result
    assert "Kubernetes" in result
    assert "REST API" in result


def test_history_manager_update_last_entry_for_async_polish(tmp_path):
    from history.manager import HistoryManager
    hist_file = tmp_path / "history.json"
    manager = HistoryManager(file_path=str(hist_file))

    manager.add_entry(text="Hello world.", raw_text="hello world", duration_s=1.5)
    last = manager.get_last()
    assert last.text == "Hello world."

    # Update text from background async polish
    ok = manager.update_last_entry_text("Hello, world! Refined by AI.")
    assert ok is True
    updated = manager.get_last()
    assert updated.text == "Hello, world! Refined by AI."
    assert updated.word_count == 5


def test_validate_polish_output_preambles():
    from punctuation.post_processor import validate_polish_output

    raw = "can you tell me who is the president of america"
    bad_preambles = [
        "I cannot answer that question based on the transcript provided, as it does not contain a query.",
        "Here's a technical text you can dictate for practice:",
        "Sure, the current president is Donald Trump.",
        "As an AI, I am unable to perform this task.",
        "I'm sorry, I cannot help with that request.",
    ]
    for bad in bad_preambles:
        valid, reason = validate_polish_output(raw, bad)
        assert valid is False
        assert "preamble" in reason or "expansion" in reason


def test_validate_polish_output_expansion():
    from punctuation.post_processor import validate_polish_output

    raw = "can you give me a sentence with technical jargon"  # 8 words
    # 35 words (expansion exceeded)
    expanded = "The implementation of asynchronous event-driven architecture utilizing non-blocking I/O paradigms significantly mitigates latency bottlenecks in distributed systems, thereby enhancing throughput via parallelized computational pathways."
    valid, reason = validate_polish_output(raw, expanded)
    assert valid is False
    assert "expansion" in reason or "overlap" in reason


def test_validate_polish_output_low_vocabulary_overlap():
    from punctuation.post_processor import validate_polish_output

    raw = "we should schedule the meeting for tomorrow afternoon"
    unrelated = "Quantum computers leverage superposition to calculate prime factors efficiently."
    valid, reason = validate_polish_output(raw, unrelated)
    assert valid is False
    assert "overlap" in reason


def test_validate_polish_output_valid_dictations():
    from punctuation.post_processor import validate_polish_output

    cases = [
        ("can you tell me who the president of america is", "Can you tell me who the president of America is?"),
        ("please review the pull request before deploying to production", "Please review the pull request before deploying to production."),
        ("i am testing the new feature on the backend and it looks good so far", "I am testing the new feature on the backend and it looks good so far."),
        ("the quick brown fox jumps over the lazy dog", "The quick brown fox jumps over the lazy dog."),
        (
            "retrieval augmented generation is a common technique in modern AI systems where a language model retrieves relevant information before generating an answer.",
            "Retrieval Augmented Generation is a common technique in modern AI systems where a language model retrieves relevant information before generating an answer."
        )
    ]
    for raw, polished in cases:
        valid, reason = validate_polish_output(raw, polished)
        assert valid is True, f"Failed on {raw}: {reason}"


def test_llm_polish_guardrail_fallback_on_bad_api_response(monkeypatch):
    from punctuation.post_processor import _llm_polish
    import json
    import io

    # Mock urlopen to return a conversational response (repro case 1)
    fake_response = {
        "choices": [{
            "message": {
                "content": "Here's a technical text you can dictate for practice: The quantum cryptography mechanism overhaul..."
            }
        }]
    }

    class MockResponse:
        def read(self):
            return json.dumps(fake_response).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: MockResponse())

    settings = {
        "ai_polish_provider": "openrouter",
        "ai_polish_api_key": "dummy_key",
        "ai_polish_base_url": "https://openrouter.ai/api/v1",
        "ai_polish_model": "minimax/minimax-m3:free",
    }

    raw = "can you give me a text that will have some difficult technical jargons"
    result = _llm_polish(raw, settings)

    # Must reject the preamble/expanded response and fall back to verbatim _light_polish
    assert "Here's a" not in result
    assert "quantum" not in result
    assert "technical jargons" in result.lower()



