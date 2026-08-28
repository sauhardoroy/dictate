"""Unit and regression tests for Feature 2: Mid-Session Voice Commands ('continue' / 'let's start again')."""
import numpy as np
import pytest

from audio.capture import Recorder
from punctuation.voice_commands import (
    detect_mid_session_command,
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


class TestStripContinueCommand:
    """Test removal of trailing continue commands from final transcripts."""

    def test_strip_trailing_continue(self):
        assert strip_continue_command("We need to deploy today continue") == "We need to deploy today"
        assert strip_continue_command("We need to deploy today continue.") == "We need to deploy today"
        assert strip_continue_command("We need to deploy today keep going") == "We need to deploy today"
        assert strip_continue_command("continue") == ""
        assert strip_continue_command("continue.") == ""

    def test_preserve_mid_sentence_continue(self):
        assert strip_continue_command("Let us continue our discussion") == "Let us continue our discussion"
        assert strip_continue_command("Continue to provide updates") == "Continue to provide updates"


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
