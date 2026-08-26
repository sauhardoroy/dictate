import pytest
from punctuation.semantic_vad import is_incomplete_thought, get_adaptive_silence_duration

def test_incomplete_thought_conjunctions():
    assert is_incomplete_thought("I went to the store and") is True
    assert is_incomplete_thought("We should do this because") is True
    assert is_incomplete_thought("I would like to go but") is True
    assert is_incomplete_thought("Let me know if") is True

def test_incomplete_thought_prepositions_and_articles():
    assert is_incomplete_thought("He walked into the") is True
    assert is_incomplete_thought("Send this email to") is True
    assert is_incomplete_thought("Looking for an") is True
    assert is_incomplete_thought("Speaking about") is True

def test_incomplete_thought_auxiliary_verbs_and_fillers():
    assert is_incomplete_thought("She was trying to") is True
    assert is_incomplete_thought("I was thinking that") is True
    assert is_incomplete_thought("It is more") is True
    assert is_incomplete_thought("You know") is True

def test_complete_thoughts():
    assert is_incomplete_thought("I finished the presentation.") is False
    assert is_incomplete_thought("Let us deploy the application") is False
    assert is_incomplete_thought("Thank you very much") is False
    assert is_incomplete_thought("Good morning") is False

def test_adaptive_silence_duration():
    # Incomplete thought yields extended silence
    dur_incomplete = get_adaptive_silence_duration("I wanted to", base_silence_seconds=1.4)
    assert dur_incomplete >= 2.5

    # Complete thought maintains base silence
    dur_complete = get_adaptive_silence_duration("I finished it.", base_silence_seconds=1.4)
    assert dur_complete == 1.4
