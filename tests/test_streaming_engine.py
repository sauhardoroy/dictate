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


def test_streaming_engine_resolve_hotwords(tmp_path):
    hw_file = tmp_path / "custom_streaming_hw.txt"
    hw_file.write_text("PyTorch:2.0\nKubernetes:2.0\n", encoding="utf-8")

    engine = SherpaStreamingEngine()
    resolved = engine._resolve_hotwords_file(str(hw_file))
    assert os.path.isfile(resolved)
    with open(resolved, "r", encoding="utf-8") as f:
        content = f.read()
    assert "pytorch" in content
    assert "kubernetes" in content


def test_streaming_engine_load_with_hotwords(tmp_path):
    hw_file = tmp_path / "custom_streaming_hw.txt"
    hw_file.write_text("pytorch:2.0\nkubernetes:2.0\n", encoding="utf-8")

    engine = SherpaStreamingEngine()
    # FastConformer CTC will initialize in greedy search mode with clear logging
    ok = engine.load(model_choice="nemo-fast-conformer-80ms", hotwords_file=str(hw_file), hotwords_score=2.5)
    assert ok is True
    assert engine.is_available() is True


def test_streaming_engine_get_last_text():
    engine = SherpaStreamingEngine()
    assert engine.get_last_text() == ""
    engine._last_text = "I would like to"
    assert engine.get_last_text() == "I would like to"
    final = engine.stop_stream()
    assert final == "I would like to"
    assert engine.get_last_text() == ""


def test_pause_evaluation_uses_streaming_text_deduplication():
    from punctuation.semantic_vad import get_adaptive_silence_duration

    # Incomplete thought ends with preposition/conjunction -> requires longer pause
    streaming_text = "we should go to the"
    adaptive_sec = get_adaptive_silence_duration(streaming_text, base_silence_seconds=1.4)
    assert adaptive_sec >= 2.0

    # Complete thought -> standard pause
    complete_text = "we should go to the store."
    adaptive_sec_complete = get_adaptive_silence_duration(complete_text, base_silence_seconds=1.4)
    assert adaptive_sec_complete == 1.4


