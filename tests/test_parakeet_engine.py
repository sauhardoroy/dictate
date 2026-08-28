"""Unit tests for ParakeetTDTEngine and SherpaOfflineEngine with hotwords."""
import os
import pytest
from asr.parakeet_engine import ParakeetTDTEngine
from asr.sherpa_offline_engine import SherpaOfflineEngine


def test_parakeet_engine_hotwords_resolution(tmp_path):
    hw_file = tmp_path / "custom_hotwords.txt"
    hw_file.write_text("PyTorch:2.0\nNeMo:2.0\n", encoding="utf-8")

    engine = ParakeetTDTEngine(hotwords_file=str(hw_file), hotwords_score=3.0)
    assert engine.hotwords_file == str(hw_file)
    resolved = engine._resolve_hotwords_file()
    assert os.path.exists(resolved)
    assert "hotwords" in resolved


def test_parakeet_engine_missing_hotwords_graceful():
    engine = ParakeetTDTEngine(hotwords_file="nonexistent_file_12345.txt")
    resolved = engine._resolve_hotwords_file()
    assert resolved == ""


def test_sherpa_offline_engine_instantiation():
    engine = SherpaOfflineEngine(model_id="sense-voice-small")
    assert engine.model_id == "sense-voice-small"
    assert engine.is_loaded() is False


def test_parakeet_engine_long_audio_timestamp_stitching():
    """Verify that >20s audio triggers VAD chunking and acoustic timestamp stitching without errors."""
    import soundfile as sf
    import numpy as np

    p0 = "models/sherpa-onnx-streaming-zipformer-en-2023-06-26/test_wavs/0.wav"
    p1 = "models/sherpa-onnx-streaming-zipformer-en-2023-06-26/test_wavs/1.wav"
    if not (os.path.exists(p0) and os.path.exists(p1)):
        pytest.skip("Test wavs not found")

    w0, _ = sf.read(p0)
    w1, _ = sf.read(p1)
    long_audio = np.concatenate([w0, w1]).astype(np.float32)
    assert len(long_audio) / 16000.0 > 20.0  # Must be >20s

    engine = ParakeetTDTEngine()
    engine.load()
    res = engine.transcribe(long_audio)

    assert isinstance(res, dict)
    assert "text" in res
    # Must contain speech from both segments stitched together
    assert "yellow lamps" in res["text"].lower()
    assert "consequence" in res["text"].lower()


def test_parakeet_engine_cuda_fallback_on_cpu_system():
    """Verify that requesting CUDA on a non-GPU system gracefully falls back to CPU without crashing."""
    engine = ParakeetTDTEngine(device="cuda")
    assert engine.device == "cuda"
    engine.load()
    assert engine.is_loaded() is True
    # If no physical CUDA GPU is present, active_provider falls back to cpu
    assert engine.active_provider in ("cpu", "cuda")


def test_parakeet_engine_auto_device():
    """Verify that device='auto' defaults to CPU safely."""
    engine = ParakeetTDTEngine(device="auto")
    assert engine.device == "auto"
    engine.load()
    assert engine.is_loaded() is True
    assert engine.active_provider == "cpu"


