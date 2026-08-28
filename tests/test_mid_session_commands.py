"""Unit and regression tests for Feature 2: Mid-Session Voice Commands ('continue' / 'let's start again')."""
import numpy as np
import pytest

from audio.capture import Recorder
from punctuation.voice_commands import (
    detect_mid_session_command,
    split_on_restart_command,
    strip_continue_command,
    RESTART_COMMANDS,
    CONTINUE_COMMANDS,
)


class TestMidSessionCommandDetection:
    """Test strict whole-segment matching for mid-session voice commands."""

    @pytest.mark.parametrize("phrase", [
        "let's start again",
        "Let's start again.",
        "lets start again",
        "start over",
        "Start over!",
        "scratch that, start again",
        "scratch that start again",
        "  Start over  ",
        "I made a mistake, start over",
        "I was saying something wrong, let's start again.",
    ])
    def test_isolated_restart_commands(self, phrase):
        assert detect_mid_session_command(phrase) == "restart"

    @pytest.mark.parametrize("phrase", [
        "continue",
        "Continue.",
        "keep going",
        "Keep going!",
        "let me continue",
        "  continue  ",
        "give me a second, continue",
        "let me think for a moment, keep going",
    ])
    def test_isolated_continue_commands(self, phrase):
        assert detect_mid_session_command(phrase) == "continue"

    @pytest.mark.parametrize("phrase", [
        "let's continue with the next part of the plan",
        "continue, I wanted to also mention something else",
        "we should start over tomorrow",
        "please scratch that start again now",
        "the team decided to continue",
        "I will start over the server",
        "continue to the finish line",
        "hello world",
        "",
        "   ",
    ])
    def test_embedded_commands_do_not_match(self, phrase):
        """Strict isolation constraint: words appearing mid-sentence as real content must NOT trigger."""
        assert detect_mid_session_command(phrase) is None


class TestSplitOnRestartCommand:
    """Test splitting and discarding speech prior to restart commands."""

    def test_pure_restart_returns_empty_remainder(self):
        has_restart, rem = split_on_restart_command("start over")
        assert has_restart is True
        assert rem == ""

        has_restart, rem = split_on_restart_command("let's start again.")
        assert has_restart is True
        assert rem == ""

    def test_speech_followed_by_restart_discards_earlier_speech(self):
        raw = "We need to cancel the meeting tomorrow and reschedule it start over"
        has_restart, rem = split_on_restart_command(raw)
        assert has_restart is True
        assert rem == ""

    def test_speech_with_restart_and_subsequent_speech(self):
        raw = "We need to cancel the meeting start over the project is on track for release."
        has_restart, rem = split_on_restart_command(raw)
        assert has_restart is True
        assert rem == "the project is on track for release."

    def test_no_restart_phrase_returns_original(self):
        raw = "The project is on track for release."
        has_restart, rem = split_on_restart_command(raw)
        assert has_restart is False
        assert rem == raw


class TestStripContinueCommand:
    """Test removal of trailing continue commands from final transcripts."""

    def test_strip_trailing_continue(self):
        assert strip_continue_command("We need to deploy today continue") == "We need to deploy today"
        assert strip_continue_command("We need to deploy today continue.") == "We need to deploy today"
        assert strip_continue_command("We need to deploy today keep going") == "We need to deploy today"
        assert strip_continue_command("continue") == ""
        assert strip_continue_command("continue.") == ""

    def test_strip_mid_sentence_continue_command(self):
        raw = "I have three main points to discuss today, continue first is scalability, second is latency, and third is reliability."
        assert strip_continue_command(raw) == "I have three main points to discuss today, first is scalability, second is latency, and third is reliability."

        raw2 = "I need to think for a second keep going the answer is forty two"
        assert strip_continue_command(raw2) == "I need to think for a second the answer is forty two"

    def test_preserve_natural_speech_continue(self):
        assert strip_continue_command("The team decided to continue the rollout") == "The team decided to continue the rollout"
        assert strip_continue_command("We will continue tomorrow") == "We will continue tomorrow"
        assert strip_continue_command("Can you continue the presentation") == "Can you continue the presentation"


class TestRecorderResetBuffer:
    """Test Recorder buffer reset for restart commands."""

    def test_recorder_reset_buffer_and_silence_timer(self):
        recorder = Recorder(use_vad=False)
        # Simulate some audio written to buffer
        dummy_chunk = np.ones(16000, dtype=np.float32) * 0.1
        recorder._ensure_buffer_capacity(16000)
        with recorder._buf_lock:
            recorder._buffer[:16000] = dummy_chunk
            recorder._write_pos = 16000
        recorder.frames.append(dummy_chunk)
        recorder.silence_frames = 15
        recorder.has_spoken = True

        assert recorder.duration() == 1.0

        # Execute reset_buffer
        recorder.reset_buffer()

        assert recorder._write_pos == 0
        assert len(recorder.frames) == 0
        assert recorder.silence_frames == 0
        assert recorder.has_spoken is False
        assert recorder.duration() == 0.0

    def test_recorder_reset_silence_timer(self):
        recorder = Recorder(use_vad=False)
        recorder.silence_frames = 20
        recorder._eval_triggered_for_pause = True

        recorder.reset_silence_timer()

        assert recorder.silence_frames == 0
        assert recorder._eval_triggered_for_pause is False
