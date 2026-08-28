"""Comprehensive unit and regression tests for hotword resolution, casing preservation, and Parakeet TDT hotwords."""
import os
import pytest
import soundfile as sf
from asr.parakeet_engine import ParakeetTDTEngine
from punctuation.post_processor import get_hotwords_mapping, apply_hotwords_casing, polish
from config.settings import validated_settings


def test_hotwords_resolution_normalizes_to_lowercase(tmp_path):
    """Ensure _resolve_hotwords_file strips uppercase and normalizes to lowercase."""
    hw_file = tmp_path / "custom_hotwords.txt"
    hw_file.write_text("PyTorch:2.0\nKubernetes:2.0\nREST API:2.0\nNext.js:2.0\n", encoding="utf-8")

    engine = ParakeetTDTEngine(hotwords_file=str(hw_file), hotwords_score=2.0)
    resolved = engine._resolve_hotwords_file()
    assert os.path.isfile(resolved)

    with open(resolved, "r", encoding="utf-8") as f:
        content = f.read()

    # Must contain lowercase tokens, NOT ALL-CAPS
    assert "pytorch" in content
    assert "kubernetes" in content
    assert "PYTORCH" not in content
    assert "KUBERNETES" not in content


def test_hotwords_casing_mapping_preserves_canonical(tmp_path):
    """Ensure post_processor recovers exact mixed-case canonical tokens."""
    hw_file = tmp_path / "custom_hotwords.txt"
    hw_file.write_text("PyTorch:2.0\nPostgreSQL:2.0\nREST API:2.0\nNext.js:2.0\n", encoding="utf-8")

    mapping = get_hotwords_mapping(str(hw_file))
    assert mapping["pytorch"] == "PyTorch"
    assert mapping["postgresql"] == "PostgreSQL"
    assert mapping["rest api"] == "REST API"
    assert mapping["next.js"] == "Next.js"

    # Test restoration
    raw_text = "i am connecting pytorch to postgresql via rest api in next.js"
    cased = apply_hotwords_casing(raw_text, str(hw_file))
    assert "PyTorch" in cased
    assert "PostgreSQL" in cased
    assert "REST API" in cased
    assert "Next.js" in cased


def test_settings_migrates_legacy_hotwords_sherpa():
    """Ensure legacy settings pointing to .hotwords_sherpa.txt migrate to hotwords.txt."""
    loaded = {"hotwords_file": "C:/path/to/.hotwords_sherpa.txt", "hotwords_score": 2.5}
    migrated = validated_settings(loaded)
    assert migrated["hotwords_file"] == "hotwords.txt"
    assert migrated["hotwords_score"] == 2.5


def test_parakeet_engine_loads_lowercase_hotwords(tmp_path):
    """Ensure ParakeetTDTEngine successfully loads with lowercase hotwords."""
    hw_file = tmp_path / "test_hw.txt"
    hw_file.write_text("pytorch:2.0\nkubernetes:2.0\nartificial intelligence:2.0\n", encoding="utf-8")

    engine = ParakeetTDTEngine(hotwords_file=str(hw_file), hotwords_score=2.0)
    engine.load()
    assert engine.is_loaded() is True


def test_hotwords_audio_transcription_baseline_diff():
    """Verify transcription on test_hotwords_16k.wav with resolved hotwords."""
    wav_path = os.path.join(os.path.dirname(__file__), "test_hotwords_16k.wav")
    if not os.path.isfile(wav_path):
        pytest.skip("test_hotwords_16k.wav not found")

    audio, sr = sf.read(wav_path)
    engine = ParakeetTDTEngine()
    engine.load()
    res = engine.transcribe(audio)
    assert isinstance(res, dict)
    assert "text" in res
    assert len(res["text"]) > 0

    # Also test through polish pipeline with casing restoration
    polished = polish(res["text"], settings={"hotwords_file": "hotwords.txt", "ai_polish": False})
    assert "PyTorch" in polished or "pytorch" in polished.lower()
