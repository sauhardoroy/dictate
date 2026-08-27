"""Unit tests for the centralized model manager and restricted model registry."""
import os
import pytest
from asr.model_manager import SUPPORTED_MODELS, is_model_cached, get_model_files, ensure_model_downloaded


def test_supported_models_restricted_suite():
    # Exactly 2 NVIDIA models and 1 Alibaba model
    assert set(SUPPORTED_MODELS.keys()) == {
        "parakeet-tdt-0.6b-v3",
        "nemo-fast-conformer-80ms",
        "sense-voice-small"
    }

    # Verify providers
    assert SUPPORTED_MODELS["parakeet-tdt-0.6b-v3"]["provider"] == "NVIDIA"
    assert SUPPORTED_MODELS["nemo-fast-conformer-80ms"]["provider"] == "NVIDIA"
    assert SUPPORTED_MODELS["sense-voice-small"]["provider"] == "Alibaba"


def test_unsupported_model_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported model"):
        ensure_model_downloaded("unsupported-whisper-model")

    with pytest.raises(ValueError, match="Unknown model ID"):
        get_model_files("nonexistent-model")


def test_is_model_cached_returns_bool():
    # Should return a boolean without throwing
    res = is_model_cached("parakeet-tdt-0.6b-v3")
    assert isinstance(res, bool)
    res_sv = is_model_cached("sense-voice-small")
    assert isinstance(res_sv, bool)
    res_fake = is_model_cached("fake-model-123")
    assert res_fake is False


def test_get_model_files_for_cached_model(tmp_path, monkeypatch):
    # Mock a local model folder in tmp_path
    from asr import model_manager
    monkeypatch.setattr(model_manager, "get_models_dir", lambda: str(tmp_path))

    model_dir = tmp_path / "parakeet-tdt-0.6b-v3"
    model_dir.mkdir(parents=True)
    for f in ["encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"]:
        (model_dir / f).write_bytes(b"dummy")

    assert is_model_cached("parakeet-tdt-0.6b-v3") is True
    files = get_model_files("parakeet-tdt-0.6b-v3")
    assert len(files) == 4
    assert os.path.exists(files["encoder.int8.onnx"])
