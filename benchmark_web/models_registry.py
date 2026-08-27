"""Central Model Registry for ASR Models."""
import os
import sys
from typing import Dict, Any, List

def get_models_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "models")


AVAILABLE_MODELS: Dict[str, Dict[str, Any]] = {
    "parakeet-tdt-0.6b-v3": {
        "id": "parakeet-tdt-0.6b-v3",
        "name": "NVIDIA Parakeet TDT 0.6B v3 (INT8 ONNX)",
        "framework": "sherpa-onnx",
        "type": "transcription & streaming",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "600M",
        "size_mb": 620,
        "wer": "1.9% (State of the Art)",
        "hf_repo": "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
        "description": "NVIDIA NeMo Parakeet TDT (Token-and-Duration Transducer) quantized to INT8. SOTA accuracy on English, French, German, Spanish.",
    },
    "nemo-fast-conformer-80ms": {
        "id": "nemo-fast-conformer-80ms",
        "name": "NVIDIA FastConformer CTC (80ms Streaming)",
        "framework": "sherpa-onnx",
        "type": "streaming & transcription",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "120M",
        "size_mb": 420,
        "wer": "2.4% (Ultra-Low Latency)",
        "hf_repo": "csukuangfj/sherpa-onnx-nemo-streaming-fast-conformer-ctc-en-80ms",
        "description": "NVIDIA NeMo FastConformer CTC streaming model with 80ms lookahead chunk. Excellent acoustic precision and low latency.",
    },
    "zipformer-70M": {
        "id": "zipformer-70M",
        "name": "Sherpa Zipformer 70M (Streaming Transducer)",
        "framework": "sherpa-onnx",
        "type": "streaming & transcription",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "70M",
        "size_mb": 75,
        "wer": "2.8% (High Accuracy)",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-2023-06-26.tar.bz2",
        "dir_name": "sherpa-onnx-streaming-zipformer-en-2023-06-26",
        "description": "Next-gen Kaldi Zipformer transducer model. ~0.4ms chunk latency on CPU with high accuracy for conversational speech and accents.",
    },
    "zipformer-20M": {
        "id": "zipformer-20M",
        "name": "Sherpa Zipformer 20M (Ultra Lightweight)",
        "framework": "sherpa-onnx",
        "type": "streaming & transcription",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "20M",
        "size_mb": 25,
        "wer": "6.5% (Ultra Fast)",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2",
        "dir_name": "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17",
        "description": "Ultra-lightweight 20M parameter Zipformer model. <0.2ms chunk latency, ideal for low-end hardware.",
    },
    "sense-voice-small": {
        "id": "sense-voice-small",
        "name": "Alibaba SenseVoice Small (Multilingual)",
        "framework": "sherpa-onnx",
        "type": "transcription & streaming",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "230M",
        "size_mb": 230,
        "wer": "2.6% (50x Faster)",
        "hf_repo": "csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
        "description": "Alibaba FunASR SenseVoice Small. Recognizes English, Mandarin, Cantonese, Japanese, Korean with audio event & emotion detection.",
    },
    "paraformer-zh-en": {
        "id": "paraformer-zh-en",
        "name": "Alibaba Streaming Paraformer (Bilingual ZH/EN)",
        "framework": "sherpa-onnx",
        "type": "streaming & transcription",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "220M",
        "size_mb": 236,
        "wer": "2.5% (Real-Time)",
        "hf_repo": "csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en",
        "description": "Alibaba FunASR real-time streaming speech recognition (English + Mandarin).",
    },
    "moonshine-tiny": {
        "id": "moonshine-tiny",
        "name": "Useful Sensors Moonshine Tiny (INT8)",
        "framework": "sherpa-onnx",
        "type": "transcription & streaming",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "34M",
        "size_mb": 45,
        "wer": "5.8% (Edge Fast)",
        "hf_repo": "csukuangfj/sherpa-onnx-moonshine-tiny-en-int8",
        "description": "Useful Sensors Moonshine Tiny INT8 architecture designed for on-device live streaming transcription.",
    },
    "moonshine-base": {
        "id": "moonshine-base",
        "name": "Useful Sensors Moonshine Base (INT8)",
        "framework": "sherpa-onnx",
        "type": "transcription & streaming",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "103M",
        "size_mb": 115,
        "wer": "3.8% (Balanced)",
        "hf_repo": "csukuangfj/sherpa-onnx-moonshine-base-en-int8",
        "description": "Useful Sensors Moonshine Base INT8 model for resource-friendly English transcription.",
    },
    "whisper-large-v3-turbo": {
        "id": "whisper-large-v3-turbo",
        "name": "OpenAI Whisper Large v3 Turbo",
        "framework": "faster-whisper",
        "type": "transcription & streaming",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "809M",
        "size_mb": 1600,
        "wer": "2.1% (State of the Art)",
        "model_id": "deepdml/faster-whisper-large-v3-turbo",
        "description": "OpenAI's latest Turbo architecture. 4 decoder layers instead of 32 for 8x faster inference with full Large v3 accuracy.",
    },
    "whisper-distil-large-v3": {
        "id": "whisper-distil-large-v3",
        "name": "Distil-Whisper Large v3 (Ultra Fast)",
        "framework": "faster-whisper",
        "type": "transcription & streaming",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "756M",
        "size_mb": 1500,
        "wer": "2.4% (Near-Large)",
        "model_id": "Systran/faster-distil-whisper-large-v3",
        "description": "Knowledge-distilled version of Whisper large v3. 6x faster than standard large-v3 while retaining 99% accuracy.",
    },
    "whisper-medium.en": {
        "id": "whisper-medium.en",
        "name": "Faster-Whisper Medium.en",
        "framework": "faster-whisper",
        "type": "transcription & streaming",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "769M",
        "size_mb": 1500,
        "wer": "3.2% (High Accuracy)",
        "model_id": "medium.en",
        "description": "English-specialized Whisper model with high vocabulary and contextual punctuation accuracy.",
    },
    "whisper-small.en": {
        "id": "whisper-small.en",
        "name": "Faster-Whisper Small.en",
        "framework": "faster-whisper",
        "type": "transcription & streaming",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "244M",
        "size_mb": 460,
        "wer": "5.5% (Balanced)",
        "model_id": "small.en",
        "description": "Lightweight, reliable English model with balanced speed and footprint.",
    },
    "zipformer-bilingual-zh-en": {
        "id": "zipformer-bilingual-zh-en",
        "name": "Sherpa Bilingual Zh/En Zipformer",
        "framework": "sherpa-onnx",
        "type": "streaming & transcription",
        "supports_streaming": True,
        "supports_file": True,
        "parameters": "70M",
        "size_mb": 80,
        "wer": "3.1% (Bilingual)",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2",
        "dir_name": "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20",
        "description": "Bilingual streaming Zipformer transducer supporting mixed English and Mandarin Chinese speech.",
    },
}


def is_model_downloaded(model_id: str) -> bool:
    """Check if the given model is present and ready to use locally."""
    meta = AVAILABLE_MODELS.get(model_id)
    if not meta:
        return False

    models_base = get_models_dir()
    framework = meta.get("framework")

    if framework == "sherpa-onnx":
        if "hf_repo" in meta:
            # Check local folder or HuggingFace hub cache
            local_dir = os.path.join(models_base, model_id)
            if os.path.exists(local_dir) and any(f.endswith(".onnx") for f in os.listdir(local_dir)):
                return True
            try:
                import huggingface_hub
                cached = huggingface_hub.try_to_load_from_cache(meta["hf_repo"], "tokens.txt")
                return isinstance(cached, str) and os.path.exists(cached)
            except Exception:
                return False
        elif "dir_name" in meta:
            local_dir = os.path.join(models_base, meta["dir_name"])
            return os.path.exists(local_dir) and any(f.endswith(".onnx") for f in os.listdir(local_dir))

    elif framework == "faster-whisper":
        m_id = meta.get("model_id", "")
        if os.path.exists(os.path.join(models_base, m_id, "model.bin")):
            return True
        try:
            import huggingface_hub
            hf_id = f"Systran/faster-whisper-{m_id}" if "/" not in m_id and not m_id.startswith("Systran") else m_id
            cached = huggingface_hub.try_to_load_from_cache(hf_id, "model.bin")
            return isinstance(cached, str) and os.path.exists(cached)
        except Exception:
            return False

    return False


def get_all_models_status() -> List[Dict[str, Any]]:
    """Return list of models with current download/readiness status."""
    res = []
    for m_id, meta in AVAILABLE_MODELS.items():
        item = dict(meta)
        item["is_downloaded"] = is_model_downloaded(m_id)
        res.append(item)
    return res
