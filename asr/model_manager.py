"""Model registry and on-demand downloader for NVIDIA and Alibaba speech models."""
import os
import sys
from typing import Callable, Optional
from log import get_logger

log = get_logger(__name__)

# Strictly restricted models suite: 2 NVIDIA models + 2 Alibaba models (Offline & Streaming)
SUPPORTED_MODELS = {
    # NVIDIA Model 1: Final Speech Dictation (Offline)
    "parakeet-tdt-0.6b-v3": {
        "name": "NVIDIA Parakeet TDT 0.6B v3",
        "provider": "NVIDIA",
        "type": "offline",
        "repo_id": "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
        "files": ["encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"],
        "size_mb": 250,
        "description": "State-of-the-art English transcription with fast punctuation.",
    },
    # NVIDIA Model 2: Real-time Live Preview Ticker (Streaming 80ms)
    "nemo-fast-conformer-80ms": {
        "name": "NVIDIA FastConformer CTC 80ms",
        "provider": "NVIDIA",
        "type": "streaming",
        "repo_id": "csukuangfj/sherpa-onnx-nemo-streaming-fast-conformer-ctc-en-80ms",
        "files": ["model.onnx", "tokens.txt"],
        "size_mb": 420,
        "description": "Ultra-low-latency real-time live preview ticker.",
    },
    # Alibaba Model 1: Multilingual Final Speech Dictation (Offline)
    "sense-voice-small": {
        "name": "Alibaba SenseVoice Small",
        "provider": "Alibaba",
        "type": "offline",
        "repo_id": "csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
        "files": ["model.int8.onnx", "tokens.txt"],
        "size_mb": 110,
        "description": "Multilingual (EN, ZH, JA, KO, YUE) with Inverse Text Normalization.",
    },
    # Alibaba Model 2: Real-time Live Preview Ticker (Streaming)
    "paraformer-zh-en": {
        "name": "Alibaba Streaming Paraformer (Bilingual)",
        "provider": "Alibaba",
        "type": "streaming",
        "repo_id": "csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en",
        "files": ["encoder.int8.onnx", "decoder.int8.onnx", "tokens.txt"],
        "size_mb": 236,
        "description": "Alibaba FunASR real-time streaming speech recognition (English + Mandarin).",
    },
}


def get_models_dir() -> str:
    """Resolve storage directory for models (portable or system appdata)."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        for cand in [os.path.join(exe_dir, "models"), os.path.join(exe_dir, "_internal", "models")]:
            if os.path.isdir(cand):
                return cand
        if sys.platform == "darwin":
            path = os.path.expanduser("~/Library/Application Support/Dictate/models")
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
            path = os.path.join(appdata, "Dictate", "models")
        else:
            path = os.path.expanduser("~/.config/dictate/models")
        os.makedirs(path, exist_ok=True)
        return path
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")



def is_model_cached(model_id: str) -> bool:
    """Check if all required files for model_id are present locally."""
    meta = SUPPORTED_MODELS.get(model_id)
    if not meta:
        return False

    # 1. Check local models directory
    local_dir = os.path.join(get_models_dir(), model_id)
    if os.path.isdir(local_dir):
        def _check_local_file(f: str) -> bool:
            if os.path.exists(os.path.join(local_dir, f)):
                return True
            if f == "model.int8.onnx" and os.path.exists(os.path.join(local_dir, "model.onnx")):
                return True
            if f == "encoder.int8.onnx" and os.path.exists(os.path.join(local_dir, "encoder.onnx")):
                return True
            if f == "decoder.int8.onnx" and os.path.exists(os.path.join(local_dir, "decoder.onnx")):
                return True
            return False

        if all(_check_local_file(f) for f in meta["files"]):
            return True

    # 2. Check HuggingFace hub cache
    try:
        from huggingface_hub import try_to_load_from_cache
        for f in meta["files"]:
            cached = try_to_load_from_cache(repo_id=meta["repo_id"], filename=f)
            if not isinstance(cached, str) or not os.path.exists(cached):
                if f == "model.int8.onnx":
                    alt = try_to_load_from_cache(repo_id=meta["repo_id"], filename="model.onnx")
                    if isinstance(alt, str) and os.path.exists(alt):
                        continue
                if f == "encoder.int8.onnx":
                    alt = try_to_load_from_cache(repo_id=meta["repo_id"], filename="encoder.onnx")
                    if isinstance(alt, str) and os.path.exists(alt):
                        continue
                if f == "decoder.int8.onnx":
                    alt = try_to_load_from_cache(repo_id=meta["repo_id"], filename="decoder.onnx")
                    if isinstance(alt, str) and os.path.exists(alt):
                        continue
                return False
        return True
    except Exception:
        return False


def ensure_model_downloaded(model_id: str, status_callback: Optional[Callable[[str], None]] = None) -> str:
    """Download model files on-demand if not cached, and return the directory path."""
    meta = SUPPORTED_MODELS.get(model_id)
    if not meta:
        raise ValueError(f"Unsupported model: {model_id}. Allowed models: {list(SUPPORTED_MODELS.keys())}")

    # Check local folder first
    local_dir = os.path.join(get_models_dir(), model_id)
    if os.path.isdir(local_dir) and all(os.path.exists(os.path.join(local_dir, f)) for f in meta["files"]):
        log.info("Model %s found in local models directory: %s", model_id, local_dir)
        return local_dir

    if status_callback:
        status_callback(f"Downloading {meta['name']} (~{meta['size_mb']}MB)...")

    log.info("Downloading/verifying %s (~%sMB) from %s...", meta["name"], meta["size_mb"], meta["repo_id"])

    try:
        import huggingface_hub
        model_dir = huggingface_hub.snapshot_download(
            repo_id=meta["repo_id"],
            allow_patterns=["*.onnx", "tokens.txt"],
        )
        log.info("Model %s downloaded and verified at %s", model_id, model_dir)
        return model_dir
    except Exception as exc:
        log.error("Failed to download model %s: %s", model_id, exc)
        raise RuntimeError(f"Could not download {meta['name']} (network issue?): {exc}") from exc


def get_model_files(model_id: str) -> dict[str, str]:
    """Ensure model is downloaded and return a dict of file names to absolute paths."""
    meta = SUPPORTED_MODELS.get(model_id)
    if not meta:
        raise ValueError(f"Unknown model ID: {model_id}")

    model_dir = ensure_model_downloaded(model_id)
    result = {}
    for f in meta["files"]:
        path = os.path.join(model_dir, f)
        # Handle fallback for sense-voice and paraformer int8 vs full onnx
        if not os.path.exists(path) and f == "model.int8.onnx":
            alt_path = os.path.join(model_dir, "model.onnx")
            if os.path.exists(alt_path):
                path = alt_path
        if not os.path.exists(path) and f == "encoder.int8.onnx":
            alt_path = os.path.join(model_dir, "encoder.onnx")
            if os.path.exists(alt_path):
                path = alt_path
        if not os.path.exists(path) and f == "decoder.int8.onnx":
            alt_path = os.path.join(model_dir, "decoder.onnx")
            if os.path.exists(alt_path):
                path = alt_path
        result[f] = path
    return result
