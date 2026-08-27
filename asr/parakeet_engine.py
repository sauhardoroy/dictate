"""NVIDIA NeMo Parakeet TDT 0.6B v3 (INT8 ONNX) Engine for Dictate."""
import os
import sys
import numpy as np
from .base import ASREngine
from log import get_logger

log = get_logger(__name__)

HF_REPO_ID = "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"


def get_models_dir() -> str:
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        for cand in [os.path.join(exe_dir, "models"), os.path.join(exe_dir, "_internal", "models")]:
            if os.path.isdir(cand):
                return cand
        return os.path.join(exe_dir, "models")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


class ParakeetTDTEngine(ASREngine):
    name = "parakeet-tdt"

    def __init__(self, num_threads: int = 4):
        self.num_threads = num_threads or 4
        self.recognizer = None
        self._is_loaded = False

    def load(self):
        """Load the Parakeet TDT INT8 ONNX model."""
        import sherpa_onnx
        import huggingface_hub

        models_base = get_models_dir()
        local_dir = os.path.join(models_base, "parakeet-tdt-0.6b-v3")

        # Check if stored in local models folder or HF cache
        if os.path.exists(os.path.join(local_dir, "encoder.int8.onnx")):
            model_dir = local_dir
        else:
            log.info("Downloading/verifying Parakeet TDT 0.6B v3 from HuggingFace...")
            model_dir = huggingface_hub.snapshot_download(
                repo_id=HF_REPO_ID,
                allow_patterns=["*.onnx", "tokens.txt"],
            )

        encoder = os.path.join(model_dir, "encoder.int8.onnx")
        decoder = os.path.join(model_dir, "decoder.int8.onnx")
        joiner = os.path.join(model_dir, "joiner.int8.onnx")
        tokens = os.path.join(model_dir, "tokens.txt")

        log.info("Initializing Parakeet TDT NeMo transducer...")
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            tokens=tokens,
            num_threads=self.num_threads,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            model_type="nemo_transducer",
        )
        self._is_loaded = True
        log.info("Parakeet TDT engine ready")

    def is_loaded(self) -> bool:
        return self._is_loaded and self.recognizer is not None

    def transcribe(self, audio: np.ndarray, fast: bool = False) -> dict:
        """Transcribe 16kHz float32 audio."""
        if not self.is_loaded():
            raise RuntimeError("Parakeet TDT model is not loaded")

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if audio.ndim > 1:
            audio = audio.flatten()

        stream = self.recognizer.create_stream()
        stream.accept_waveform(16000, audio)
        self.recognizer.decode_stream(stream)
        text = stream.result.text.strip()
        return {"text": text, "language": "en"}
