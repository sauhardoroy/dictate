"""Experimental: Nemotron-3.5-ASR-Streaming-0.6B via a local parakeet.cpp binary.

Phase 2 scaffold. Point settings["nemotron_binary"] at a parakeet.cpp
streaming executable that reads raw 16 kHz mono PCM on stdin and writes
transcript text to stdout. Until then this engine refuses to load and the
app falls back to the Whisper engine.
"""
import subprocess

import numpy as np

from .base import ASREngine
from log import get_logger

log = get_logger(__name__)


class NemotronEngine(ASREngine):
    name = "nemotron-3.5-asr-streaming (parakeet.cpp)"

    def __init__(self, binary="", model_path=""):
        self.binary = binary
        self.model_path = model_path

    def load(self):
        if not self.binary:
            raise RuntimeError(
                "nemotron_binary not configured — see README, 'Phase 2: Nemotron'"
            )

    def is_loaded(self) -> bool:
        return bool(self.binary)

    def transcribe(self, audio) -> dict:
        if isinstance(audio, np.ndarray):
            pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        else:
            with open(audio, "rb") as f:  # treat as raw file path
                pcm = f.read()
        cmd = [self.binary]
        if self.model_path:
            cmd += ["--model", self.model_path]
        proc = subprocess.run(cmd, input=pcm, capture_output=True, timeout=120)
        if proc.returncode != 0:
            log.error("nemotron binary failed rc=%s: %s", proc.returncode, proc.stderr.decode("utf-8", "ignore")[:200])
            raise RuntimeError(proc.stderr.decode("utf-8", "ignore")[:500])
        text = proc.stdout.decode("utf-8", "ignore").strip()
        log.debug("nemotron transcribed %d chars", len(text))
        return {"text": text}
