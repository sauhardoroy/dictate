"""Unit tests for voice commands: inline formatting and action commands."""
import pytest

from punctuation.voice_commands import (
    apply_voice_formatting,
    get_action_command,
    ACTION_COMMANDS,
)
from punctuation.post_processor import polish


class TestActionCommands:
    @pytest.mark.parametrize("phrase, expected_action", [
        ("delete that", "undo"),
        ("delete that.", "undo"),
        ("scratch that", "undo"),
        ("undo that", "undo"),
        ("undo", "undo"),
        ("redo that", "redo"),
        ("select all", "select_all"),
        ("select all.", "select_all"),
        ("copy that", "copy"),
        ("cut that", "cut"),
        ("paste that", "paste"),
        ("press enter", "enter"),
        ("hit enter", "enter"),
    ])
    def test_detects_action_commands(self, phrase, expected_action):
        assert get_action_command(phrase) == expected_action

    @pytest.mark.parametrize("phrase", [
        "delete that word from the sentence",
        "please copy that document",
        "undo is a useful feature",
        "hello world",
    ])
    def test_non_action_commands_return_none(self, phrase):
        assert get_action_command(phrase) is None


class TestVoiceFormatting:
    @pytest.mark.parametrize("input_text, expected_output", [
        ("hello world new line how are you", "Hello world\nHow are you"),
        ("first line next line second line", "First line\nSecond line"),
        ("paragraph one new paragraph paragraph two", "Paragraph one\n\nParagraph two"),
        ("hello comma world period", "Hello, world."),
        ("is this working question mark", "Is this working?"),
        ("wow exclamation mark", "Wow!"),
        ("note colon check this semicolon next", "Note: check this; next"),
        ("well hyphen known word", "Well-known word"),
        ("open quote important close quote", '"important"'),
        ("open paren optional close paren", "(optional)"),
        ("send to john at sign example dot com", "Send to john@example.com"),
        ("use hashtag trending", "Use #trending"),
        ("price is dollar sign 50", "Price is $50"),
        ("discount is 20 percent sign", "Discount is 20%"),
    ])
    def test_voice_formatting_replacements(self, input_text, expected_output):
        result = apply_voice_formatting(input_text)
        assert result == expected_output

    def test_polish_with_voice_commands_enabled(self):
        result = polish("this is a test period new line start second line exclamation mark", settings={"voice_commands": True})
        assert result == "This is a test.\nStart second line!"

    def test_polish_with_voice_commands_disabled(self):
        result = polish("this is a test period", settings={"voice_commands": False})
        assert result == "This is a test period."
