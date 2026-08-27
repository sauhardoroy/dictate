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
