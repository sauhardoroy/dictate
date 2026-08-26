"""Unit tests for transcript history management, storage, search, and export."""
import os
import tempfile
import pytest

from history.manager import HistoryManager, TranscriptRecord


@pytest.fixture
def temp_history_file(tmp_path):
    return str(tmp_path / "test_history.json")


def test_add_and_retrieve_entry(temp_history_file):
    mgr = HistoryManager(file_path=temp_history_file)
    rec = mgr.add_entry(
        text="Hello world, this is a test.",
        raw_text="hello world this is a test",
        duration_s=2.5,
        target_app="notepad.exe",
        window_title="Untitled - Notepad",
    )

    assert rec is not None
    assert rec.text == "Hello world, this is a test."
    assert rec.word_count == 6
    assert rec.char_count == 28
    assert rec.target_app == "notepad.exe"
    assert rec.duration_s == 2.5

    # Check get_last
    last = mgr.get_last()
    assert last is not None
    assert last.id == rec.id
    assert last.text == rec.text

    # Check persistence
    mgr2 = HistoryManager(file_path=temp_history_file)
    assert len(mgr2.get_all()) == 1
    assert mgr2.get_last().text == rec.text


def test_max_entries_fifo_capping(temp_history_file):
    mgr = HistoryManager(file_path=temp_history_file, max_entries=3)
    for i in range(5):
        mgr.add_entry(f"Message {i}")

    all_entries = mgr.get_all()
    assert len(all_entries) == 3
    # Newest first
    assert all_entries[0].text == "Message 4"
    assert all_entries[1].text == "Message 3"
    assert all_entries[2].text == "Message 2"


def test_search_history(temp_history_file):
    mgr = HistoryManager(file_path=temp_history_file)
    mgr.add_entry("Drafting an urgent email to Alice", target_app="outlook.exe")
    mgr.add_entry("Writing code in Python", target_app="code.exe", window_title="app.py - VS Code")
    mgr.add_entry("Meeting notes with Bob", target_app="teams.exe")

    # Search in text
    results = mgr.search("urgent")
    assert len(results) == 1
    assert results[0].target_app == "outlook.exe"

    # Search in app
    results = mgr.search("code.exe")
    assert len(results) == 1
    assert results[0].text == "Writing code in Python"

    # Search in window title
    results = mgr.search("VS Code")
    assert len(results) == 1

    # Case-insensitive
    results = mgr.search("ALICE")
    assert len(results) == 1


def test_delete_and_clear_history(temp_history_file):
    mgr = HistoryManager(file_path=temp_history_file)
    rec1 = mgr.add_entry("First message")
    rec2 = mgr.add_entry("Second message")

    assert len(mgr.get_all()) == 2

    # Delete single entry
    assert mgr.delete_entry(rec1.id) is True
    assert len(mgr.get_all()) == 1
    assert mgr.get_last().id == rec2.id

    # Clear all
    mgr.clear()
    assert len(mgr.get_all()) == 0
    assert mgr.get_last() is None


def test_export_markdown_and_text(temp_history_file):
    mgr = HistoryManager(file_path=temp_history_file)
    mgr.add_entry("First paragraph of notes", target_app="notepad.exe")
    mgr.add_entry("Second paragraph of notes", target_app="word.exe")

    md = mgr.export_markdown()
    assert "# Dictate — Transcript History" in md
    assert "First paragraph of notes" in md
    assert "Second paragraph of notes" in md
    assert "`notepad.exe`" in md

    txt = mgr.export_text()
    assert "First paragraph of notes" in txt
    assert "Second paragraph of notes" in txt


def test_empty_and_disabled_history(temp_history_file):
    mgr = HistoryManager(file_path=temp_history_file, enabled=False)
    rec = mgr.add_entry("Should not be saved")
    assert rec is None
    assert len(mgr.get_all()) == 0
    assert mgr.get_last() is None

    mgr_enabled = HistoryManager(file_path=temp_history_file, enabled=True)
    assert mgr_enabled.add_entry("   ") is None
    assert mgr_enabled.add_entry("") is None
