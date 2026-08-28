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


