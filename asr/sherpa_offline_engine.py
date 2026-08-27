"""Sherpa-ONNX Offline Engines (SenseVoice, Moonshine) for Dictate."""
import os
import sys
import numpy as np
from .base import ASREngine
from log import get_logger

log = get_logger(__name__)


def get_models_dir() -> str:
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        for cand in [os.path.join(exe_dir, "models"), os.path.join(exe_dir, "_internal", "models")]:
            if os.path.isdir(cand):
                return cand
        return os.path.join(exe_dir, "models")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


class SherpaOfflineEngine(ASREngine):
    """Generic offline engine wrapping SenseVoice or Moonshine models from Sherpa-ONNX."""
    name = "sherpa-offline"

    def __init__(self, model_id: str = "sense-voice-small", num_threads: int = 4):
        self.model_id = model_id
        self.num_threads = num_threads or 4
        self.recognizer = None
        self._is_loaded = False

    def load(self):
        import sherpa_onnx
        import huggingface_hub

        log.info("Loading Sherpa-ONNX offline model: %s...", self.model_id)

        if self.model_id == "sense-voice-small":
            repo = "csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
            model_dir = huggingface_hub.snapshot_download(repo, allow_patterns=["*.onnx", "tokens.txt"])
            model_file = os.path.join(model_dir, "model.int8.onnx" if os.path.exists(os.path.join(model_dir, "model.int8.onnx")) else "model.onnx")
            tokens_file = os.path.join(model_dir, "tokens.txt")

            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_file,
                tokens=tokens_file,
                num_threads=self.num_threads,
                use_itn=True,
            )
            self._is_loaded = True

        elif self.model_id.startswith("moonshine-"):
            repo = f"csukuangfj/sherpa-onnx-{self.model_id}-en-int8"
            model_dir = huggingface_hub.snapshot_download(repo, allow_patterns=["*.onnx", "tokens.txt"])
            preprocess = os.path.join(model_dir, "preprocess.onnx")
            encode = os.path.join(model_dir, "encode.int8.onnx")
            uncached_decode = os.path.join(model_dir, "uncached_decode.int8.onnx")
            cached_decode = os.path.join(model_dir, "cached_decode.int8.onnx")
            tokens = os.path.join(model_dir, "tokens.txt")

            self.recognizer = sherpa_onnx.OfflineRecognizer.from_moonshine(
                preprocessor=preprocess,
                encoder=encode,
                uncached_decoder=uncached_decode,
                cached_decoder=cached_decode,
                tokens=tokens,
                num_threads=self.num_threads,
            )
            self._is_loaded = True
        else:
            raise ValueError(f"Unsupported offline model: {self.model_id}")

        log.info("Model %s loaded successfully", self.model_id)

    def is_loaded(self) -> bool:
        return self._is_loaded and self.recognizer is not None

    def transcribe(self, audio: np.ndarray, fast: bool = False) -> dict:
        if not self.is_loaded():
            raise RuntimeError(f"{self.model_id} model is not loaded")

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if audio.ndim > 1:
            audio = audio.flatten()

        stream = self.recognizer.create_stream()
        stream.accept_waveform(16000, audio)
        self.recognizer.decode_stream(stream)
        text = stream.result.text.strip()
        return {"text": text, "language": "en"}
