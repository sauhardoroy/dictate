"""Unit tests for the Sherpa-ONNX streaming engine."""
import os
import numpy as np
import pytest

from asr.streaming_sherpa import SherpaStreamingEngine, get_models_dir, MODEL_DIR_NAME


def test_streaming_engine_load_and_availability():
    engine = SherpaStreamingEngine()
    ok = engine.load()
    assert ok is True
    assert engine.is_available() is True


def test_streaming_engine_stream_lifecycle():
    engine = SherpaStreamingEngine()
    assert engine.load() is True

    engine.start_stream()
    assert engine.stream is not None

    # Feed 10 zero chunks (silence)
    silence_chunk = np.zeros(1024, dtype=np.float32)
    for _ in range(10):
        res = engine.accept_chunk(silence_chunk)
        # Silence shouldn't crash and returns string or None
        assert res is None or isinstance(res, str)

    final_text = engine.stop_stream()
    assert isinstance(final_text, str)
    assert engine.stream is None


def test_streaming_engine_fallback_when_uninitialized():
    engine = SherpaStreamingEngine()
    # Before load(), methods shouldn't crash
    assert engine.is_available() is False
    engine.start_stream()
    assert engine.accept_chunk(np.zeros(512, dtype=np.float32)) is None
    assert engine.stop_stream() == ""


def test_streaming_engine_paraformer_load():
    engine = SherpaStreamingEngine()
    ok = engine.load(model_choice="paraformer-zh-en")
    assert ok is True
    assert engine.is_available() is True
    engine.start_stream()
    assert engine.stream is not None
    silence = np.zeros(1024, dtype=np.float32)
    res = engine.accept_chunk(silence)
    assert res is None or isinstance(res, str)
    final = engine.stop_stream()
    assert isinstance(final, str)
