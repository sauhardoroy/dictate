"""Real-time streaming speech recognition engine powered by Sherpa-ONNX Zipformer.

Provides ultra-low latency (<40ms) streaming ASR for the live 4-word preview ticker.
Runs on streaming 64ms audio chunks independently from the Whisper batch engine.
"""
import os
import sys
import threading
import urllib.request
import tarfile
from typing import Optional, Callable
import numpy as np

from log import get_logger

log = get_logger(__name__)

MODEL_DIR_NAME = "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17"
MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2"


def get_models_dir() -> str:
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        for cand in [os.path.join(exe_dir, "models"), os.path.join(exe_dir, "_internal", "models")]:
            if os.path.isdir(cand):
                return cand
        return os.path.join(exe_dir, "models")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


class SherpaStreamingEngine:
    def __init__(self):
        self.recognizer = None
        self.stream = None
        self._lock = threading.Lock()
        self._is_ready = False
        self._last_text = ""

    def is_available(self) -> bool:
        return self._is_ready and self.recognizer is not None

    def _resolve_hotwords_file(self, hotwords_file: str = "hotwords.txt") -> str:
        """Find valid hotwords.txt and prepare a sanitized lowercase version for Sherpa-ONNX."""
        if not hotwords_file:
            return ""
        candidates = [
            hotwords_file,
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), hotwords_file),
            os.path.join(os.path.dirname(sys.executable), hotwords_file) if getattr(sys, "frozen", False) else "",
        ]
        raw_path = ""
        for cand in candidates:
            if cand and os.path.isfile(cand) and os.path.getsize(cand) > 0:
                raw_path = os.path.abspath(cand)
                break

        if not raw_path:
            return ""

        try:
            import re
            clean_lines = []
            with open(raw_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    word = line.split(":", 1)[0].split("/", 1)[0].strip()
                    word = re.sub(r"[^\w\s\-]", "", word).strip()
                    if word:
                        clean_lines.append(word.lower())

            if clean_lines:
                clean_path = os.path.join(os.path.dirname(raw_path), ".hotwords_sherpa.txt")
                with open(clean_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(clean_lines) + "\n")
                return clean_path
        except Exception as e:
            log.warning("Could not sanitize streaming hotwords file: %s", e)

        return raw_path

    def load(self, model_choice: str = "nemo-fast-conformer-80ms", async_download: bool = False,
             hotwords_file: str = "hotwords.txt", hotwords_score: float = 2.0) -> bool:
        """Initialize the Sherpa-ONNX online recognizer with NVIDIA FastConformer CTC, Alibaba Paraformer, or Zipformer."""
        try:
            import sherpa_onnx
            from asr.model_manager import ensure_model_downloaded
        except ImportError:
            log.warning("sherpa-onnx not installed; streaming live preview disabled")
            return False

        hw_path = self._resolve_hotwords_file(hotwords_file)

        # 1. Alibaba Streaming Paraformer (Bilingual ZH/EN)
        if model_choice in ("paraformer-zh-en", "streaming-paraformer", "paraformer", "alibaba-paraformer", "sense-voice-small"):
            try:
                model_dir = ensure_model_downloaded("paraformer-zh-en")
                log.info("Loading Alibaba Streaming Paraformer (Bilingual)...")
                encoder = os.path.join(model_dir, "encoder.int8.onnx")
                if not os.path.exists(encoder):
                    encoder = os.path.join(model_dir, "encoder.onnx")
                decoder = os.path.join(model_dir, "decoder.int8.onnx")
                if not os.path.exists(decoder):
                    decoder = os.path.join(model_dir, "decoder.onnx")
                tokens = os.path.join(model_dir, "tokens.txt")
                self.recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
                    tokens=tokens,
                    encoder=encoder,
                    decoder=decoder,
                    num_threads=2,
                    sample_rate=16000,
                    feature_dim=80,
                    decoding_method="greedy_search",
                )
                self._is_ready = True
                log.info("Alibaba Streaming Paraformer ready (Paraformer architecture uses greedy search)")
                return True
            except Exception as e:
                log.warning("Alibaba Paraformer load failed (%s); checking fallbacks", e)

        # 2. NVIDIA FastConformer CTC (80ms Streaming)
        try:
            model_dir = ensure_model_downloaded("nemo-fast-conformer-80ms")
            log.info("Loading NVIDIA Streaming FastConformer CTC (80ms)...")
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_nemo_ctc(
                model=os.path.join(model_dir, "model.onnx"),
                tokens=os.path.join(model_dir, "tokens.txt"),
                num_threads=4,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
            )
            self._is_ready = True
            log.info("NVIDIA Streaming FastConformer CTC ready (CTC architecture uses greedy search)")
            return True
        except Exception as e:
            log.warning("FastConformer load failed (%s); checking local models", e)

        models_base = get_models_dir()
        high_acc_dir = os.path.join(models_base, "sherpa-onnx-streaming-zipformer-en-2023-06-26")
        enc_high = os.path.join(high_acc_dir, "encoder-epoch-99-avg-1-chunk-16-left-128.int8.onnx")
        dec_high = os.path.join(high_acc_dir, "decoder-epoch-99-avg-1-chunk-16-left-128.int8.onnx")
        join_high = os.path.join(high_acc_dir, "joiner-epoch-99-avg-1-chunk-16-left-128.int8.onnx")
        tokens_high = os.path.join(high_acc_dir, "tokens.txt")

        if os.path.exists(enc_high) and os.path.exists(dec_high) and os.path.exists(join_high) and os.path.exists(tokens_high):
            log.info("Loading high-accuracy Sherpa Zipformer 70M streaming model...")
            return self._init_recognizer(tokens_high, enc_high, dec_high, join_high, hw_path=hw_path, hotwords_score=hotwords_score)


        # 3. Handle Bilingual Zh/En Zipformer
        if model_choice in ("bilingual-zh-en", "zipformer-bilingual-zh-en", "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"):
            bi_dir = os.path.join(models_base, "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20")
            if os.path.exists(bi_dir):
                onnx_files = [f for f in os.listdir(bi_dir) if f.endswith(".onnx")]
                enc_candidates = [f for f in onnx_files if "encoder" in f]
                dec_candidates = [f for f in onnx_files if "decoder" in f]
                joi_candidates = [f for f in onnx_files if "joiner" in f]
                tokens = os.path.join(bi_dir, "tokens.txt")
                if enc_candidates and dec_candidates and joi_candidates and os.path.exists(tokens):
                    return self._init_recognizer(tokens, os.path.join(bi_dir, enc_candidates[0]), os.path.join(bi_dir, dec_candidates[0]), os.path.join(bi_dir, joi_candidates[0]), hw_path=hw_path, hotwords_score=hotwords_score)
                log.warning("Bilingual Zipformer folder %s is missing required onnx or tokens files", bi_dir)

        # 4. 20M Lightweight Zipformer
        model_dir = os.path.join(models_base, MODEL_DIR_NAME)
        encoder = os.path.join(model_dir, "encoder-epoch-99-avg-1.int8.onnx")
        decoder = os.path.join(model_dir, "decoder-epoch-99-avg-1.int8.onnx")
        joiner = os.path.join(model_dir, "joiner-epoch-99-avg-1.int8.onnx")
        tokens = os.path.join(model_dir, "tokens.txt")

        # Check if complete model exists
        if not (os.path.exists(encoder) and os.path.exists(decoder) and os.path.exists(joiner) and os.path.exists(tokens)):
            if async_download:
                threading.Thread(target=lambda: self._download_and_init(hw_path=hw_path, hotwords_score=hotwords_score), daemon=True).start()
                return False
            else:
                self._download_model(models_base)

        return self._init_recognizer(tokens, encoder, decoder, joiner, hw_path=hw_path, hotwords_score=hotwords_score)

    def _download_model(self, dest_dir: str):
        try:
            os.makedirs(dest_dir, exist_ok=True)
            archive = os.path.join(dest_dir, "streaming_model.tar.bz2")
            log.info("Downloading Sherpa-ONNX streaming model (~25 MB)...")
            req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "Dictate/2.0"})
            with urllib.request.urlopen(req, timeout=30.0) as response, open(archive, "wb") as out_file:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    out_file.write(chunk)
            log.info("Extracting Sherpa-ONNX streaming model...")
            with tarfile.open(archive, "r:bz2") as tar:
                tar.extractall(dest_dir)
            if os.path.exists(archive):
                os.remove(archive)
            log.info("Sherpa-ONNX streaming model ready at %s", dest_dir)
        except Exception as e:
            log.error("Failed to download Sherpa-ONNX streaming model: %s", e)

    def _download_and_init(self, hw_path: str = "", hotwords_score: float = 2.0):
        models_base = get_models_dir()
        self._download_model(models_base)
        model_dir = os.path.join(models_base, MODEL_DIR_NAME)
        encoder = os.path.join(model_dir, "encoder-epoch-99-avg-1.int8.onnx")
        decoder = os.path.join(model_dir, "decoder-epoch-99-avg-1.int8.onnx")
        joiner = os.path.join(model_dir, "joiner-epoch-99-avg-1.int8.onnx")
        tokens = os.path.join(model_dir, "tokens.txt")
        self._init_recognizer(tokens, encoder, decoder, joiner, hw_path=hw_path, hotwords_score=hotwords_score)

    def _init_recognizer(self, tokens: str, encoder: str, decoder: str, joiner: str,
                         hw_path: str = "", hotwords_score: float = 2.0) -> bool:
        try:
            import sherpa_onnx
            if hw_path:
                try:
                    self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                        tokens=tokens,
                        encoder=encoder,
                        decoder=decoder,
                        joiner=joiner,
                        num_threads=2,
                        sample_rate=16000,
                        feature_dim=80,
                        decoding_method="modified_beam_search",
                        hotwords_file=hw_path,
                        hotwords_score=hotwords_score,
                    )
                    self._is_ready = True
                    log.info("Sherpa-ONNX streaming Zipformer engine initialized with hotwords (score=%.1f)", hotwords_score)
                    return True
                except Exception as hw_exc:
                    log.warning("Failed to initialize streaming Zipformer with hotwords (%s), falling back to greedy search", hw_exc)

            self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=tokens,
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
            )
            self._is_ready = True
            log.info("Sherpa-ONNX streaming Zipformer engine initialized")
            return True
        except Exception as exc:
            log.error("Failed to initialize Sherpa-ONNX OnlineRecognizer: %s", exc)
            self._is_ready = False
            return False

    def start_stream(self):
        """Create a fresh streaming session for a new recording."""
        with self._lock:
            self._last_text = ""
            if self._is_ready and self.recognizer:
                try:
                    self.stream = self.recognizer.create_stream()
                except Exception as e:
                    log.error("Failed to create sherpa stream: %s", e)
                    self.stream = None
            else:
                self.stream = None

    def reset_stream(self):
        """Reset the streaming session and clear decoded interim text for mid-session restart."""
        with self._lock:
            self._last_text = ""
            if self._is_ready and self.recognizer:
                try:
                    self.stream = self.recognizer.create_stream()
                except Exception as e:
                    log.error("Failed to reset sherpa stream: %s", e)
                    self.stream = None
            else:
                self.stream = None

    def accept_chunk(self, chunk: np.ndarray) -> Optional[str]:
        """Accept a 16kHz mono float32 chunk, decode, and return new text if updated."""
        with self._lock:
            if not self._is_ready or self.recognizer is None or self.stream is None:
                return None

            try:
                # Ensure float32 1D array
                if chunk.dtype != np.float32:
                    chunk = chunk.astype(np.float32)
                if chunk.ndim > 1:
                    chunk = chunk.flatten()

                self.stream.accept_waveform(16000, chunk)
                while self.recognizer.is_ready(self.stream):
                    self.recognizer.decode_stream(self.stream)

                res = self.recognizer.get_result(self.stream)
                current_text = (res.text if hasattr(res, "text") else str(res)).strip()
                if current_text and current_text != self._last_text:
                    self._last_text = current_text
                    return current_text
            except Exception as e:
                log.debug("Sherpa stream decoding error: %s", e)
            return None

    def get_last_text(self) -> str:
        """Return the most recently decoded streaming text thread-safely."""
        with self._lock:
            return self._last_text

    def stop_stream(self) -> str:
        """Finish and close the current streaming session."""
        with self._lock:
            final_text = self._last_text
            self.stream = None
            self._last_text = ""
            return final_text

