"""Unit tests for the ASR Model Benchmark & Playground Web Application."""
import pytest
import numpy as np
from fastapi.testclient import TestClient

from benchmark_web.models_registry import AVAILABLE_MODELS, is_model_downloaded, get_all_models_status
from benchmark_web.server import app
from benchmark_web.engine_pool import EnginePool


def test_models_registry_contains_parakeet_and_zipformer():
    assert "parakeet-tdt-0.6b-v3" in AVAILABLE_MODELS
    assert "zipformer-70M" in AVAILABLE_MODELS
    assert "whisper-large-v3-turbo" in AVAILABLE_MODELS
    assert "whisper-small.en" in AVAILABLE_MODELS

    models_list = get_all_models_status()
    assert len(models_list) >= 7
    parakeet_entry = next(m for m in models_list if m["id"] == "parakeet-tdt-0.6b-v3")
    assert parakeet_entry["parameters"] == "600M"
    assert parakeet_entry["supports_file"] is True


def test_api_get_models_endpoint():
    client = TestClient(app)
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    model_ids = [m["id"] for m in data]
    assert "parakeet-tdt-0.6b-v3" in model_ids
    assert "zipformer-70M" in model_ids


def test_engine_pool_zipformer_benchmark():
    pool = EnginePool()
    # 1 second of silence audio (16,000 float32 samples)
    silence = np.zeros(16000, dtype=np.float32)

    # Benchmark against the pre-downloaded Zipformer-70M model
    res = pool.benchmark_audio("zipformer-70M", silence, sample_rate=16000)
    assert res["model_id"] == "zipformer-70M"
    assert res["audio_duration_sec"] == 1.0
    assert res["inference_time_sec"] >= 0.0
    assert "rtf" in res
    assert "speedup" in res
