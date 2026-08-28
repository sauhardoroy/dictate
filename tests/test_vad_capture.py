"""Unit tests for standalone StreamingVAD, get_speech_timestamps, and decoupled Recorder."""
import numpy as np
import pytest
from audio.capture import StreamingVAD, get_speech_timestamps, Recorder


def test_streaming_vad_speech_detection():
    vad = StreamingVAD()
    silence = np.zeros(512, dtype="float32")
    prob_silence = vad.process_chunk(silence)
    assert 0.0 <= prob_silence <= 0.2

    # Simulated speech vowel phoneme with natural formants (150Hz + 800Hz + 2200Hz)
    t = np.linspace(0, 512 / 16000, 512, endpoint=False)
    speech = (0.4 * np.sin(2 * np.pi * 150 * t) + 0.3 * np.sin(2 * np.pi * 800 * t) + 0.2 * np.sin(2 * np.pi * 2200 * t)).astype("float32")
    prob_speech = vad.process_chunk(speech)
    assert prob_speech > prob_silence


def test_get_speech_timestamps_chunking():
    # Construct 1 second silence, 1 second speech, 1 second silence
    t = np.linspace(0, 1.0, 16000, endpoint=False)
    speech_segment = (0.4 * np.sin(2 * np.pi * 150 * t) + 0.3 * np.sin(2 * np.pi * 800 * t)).astype("float32")
    audio = np.concatenate([np.zeros(16000, dtype="float32"), speech_segment, np.zeros(16000, dtype="float32")])

    timestamps = get_speech_timestamps(audio, min_silence_duration_ms=300, sampling_rate=16000)
    assert len(timestamps) >= 1
    ts = timestamps[0]
    assert ts["start"] < 24000
    assert ts["end"] > 16000


def test_recorder_snapshot_and_duration():
    rec = Recorder(use_vad=False)
    assert len(rec.snapshot()) == 0
    assert rec.duration() == 0.0

    # Simulate chunk ingestion
    dummy_chunk = np.zeros((1024, 1), dtype="float32")
    rec.frames.append(dummy_chunk)
    rec.frames.append(dummy_chunk)

    snapshot = rec.snapshot()
    assert len(snapshot) == 2048
    assert rec.duration() == 2048 / 16000.0


def test_recorder_preallocated_buffer_and_expansion():
    rec = Recorder(use_vad=False)
    rec._running = True

    # Simulate callback ingestion directly via _cb
    chunk1 = np.ones((1024, 1), dtype=np.float32) * 0.5
    rec._cb(chunk1, 1024, None, None)
    rec._cb(chunk1, 1024, None, None)

    assert rec._write_pos == 2048
    snap = rec.snapshot()
    assert len(snap) == 2048
    assert np.allclose(snap, 0.5)
    assert rec.duration() == 2048 / 16000.0
    assert rec.speech_seconds(thresh=0.1) == 2048 / 16000.0

    # Test buffer dynamic capacity expansion
    large_chunk = np.ones((rec.INITIAL_CAPACITY_SAMPLES, 1), dtype=np.float32) * 0.25
    rec._cb(large_chunk, rec.INITIAL_CAPACITY_SAMPLES, None, None)
    assert rec._write_pos == 2048 + rec.INITIAL_CAPACITY_SAMPLES
    assert len(rec._buffer) > rec.INITIAL_CAPACITY_SAMPLES

