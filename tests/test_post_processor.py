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
