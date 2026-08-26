from pathlib import Path

from asr import faster_whisper_engine as engine_module


def test_resolve_model_path_prefers_complete_local_model(tmp_path, monkeypatch):
    project_models = tmp_path / "models" / "small.en"
    project_models.mkdir(parents=True)
    (project_models / "model.bin").write_bytes(b"model")
    monkeypatch.setattr(engine_module, "__file__", str(tmp_path / "asr" / "faster_whisper_engine.py"))

    assert engine_module.resolve_model_path("small.en") == str(project_models)


def test_resolve_model_path_uses_model_name_when_no_complete_local_model(tmp_path, monkeypatch):
    incomplete = tmp_path / "models" / "small.en"
    incomplete.mkdir(parents=True)
    monkeypatch.setattr(engine_module, "__file__", str(tmp_path / "asr" / "faster_whisper_engine.py"))

    assert engine_module.resolve_model_path("small.en") == "small.en"


def test_is_local_model_available_matches_resolved_model_directory(tmp_path, monkeypatch):
    model = tmp_path / "models" / "small.en"
    model.mkdir(parents=True)
    (model / "model.bin").write_bytes(b"model")
    monkeypatch.setattr(engine_module, "__file__", str(tmp_path / "asr" / "faster_whisper_engine.py"))

    assert engine_module.is_local_model_available("small.en") is True
    assert engine_module.is_local_model_available("base.en") is False


def test_engine_loading_message_distinguishes_download_from_local_load(monkeypatch):
    monkeypatch.setattr(engine_module, "is_local_model_available", lambda name: False)
    assert "Downloading" in engine_module.model_loading_message("small.en")

    monkeypatch.setattr(engine_module, "is_local_model_available", lambda name: True)
    assert "Loading" in engine_module.model_loading_message("small.en")
