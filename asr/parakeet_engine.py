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
    name = "parakeet"

    def __init__(self, num_threads: int = 4, hotwords_file: str = "hotwords.txt",
                 hotwords_score: float = 2.0, device: str = "auto", language: str = "en", **kwargs):
        self.num_threads = num_threads or 4
        self.hotwords_file = hotwords_file or "hotwords.txt"
        self.hotwords_score = float(hotwords_score) if hotwords_score else 2.0
        self.device = device or "auto"
        self.language = language or "en"
        self.recognizer = None
        self._is_loaded = False

    def _resolve_hotwords_file(self) -> str:
        """Find valid hotwords.txt and prepare a sanitized version for Sherpa-ONNX."""
        if not self.hotwords_file:
            return ""
        candidates = [
            self.hotwords_file,
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.hotwords_file),
            os.path.join(os.path.dirname(sys.executable), self.hotwords_file) if getattr(sys, "frozen", False) else "",
        ]
        raw_path = ""
        for cand in candidates:
            if cand and os.path.isfile(cand) and os.path.getsize(cand) > 0:
                raw_path = os.path.abspath(cand)
                break

        if not raw_path:
            return ""

        # Prepare clean hotwords without punctuation / colons that fail token lookup
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
            log.warning("Could not sanitize hotwords file: %s", e)

        return raw_path

    def load(self):
        """Load the Parakeet TDT INT8 ONNX model with Sherpa-ONNX."""
        import sherpa_onnx
        from asr.model_manager import ensure_model_downloaded

        model_dir = ensure_model_downloaded("parakeet-tdt-0.6b-v3")
        encoder = os.path.join(model_dir, "encoder.int8.onnx")
        decoder = os.path.join(model_dir, "decoder.int8.onnx")
        joiner = os.path.join(model_dir, "joiner.int8.onnx")
        tokens = os.path.join(model_dir, "tokens.txt")

        hw_path = self._resolve_hotwords_file()
        if hw_path:
            log.info("Loading Parakeet TDT with hotwords phrase boosting from: %s (score=%.1f)", hw_path, self.hotwords_score)
            decoding_method = "modified_beam_search"
        else:
            log.info("Loading Parakeet TDT with greedy search (no hotwords file)")
            decoding_method = "greedy_search"

        provider = "cpu"
        # If cuda provider requested and supported by onnxruntime/sherpa-onnx
        if self.device == "cuda":
            provider = "cuda"

        self.active_provider = "cpu"
        try:
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                tokens=tokens,
                num_threads=self.num_threads,
                sample_rate=16000,
                feature_dim=80,
                decoding_method=decoding_method,
                model_type="nemo_transducer",
                max_active_paths=4,
                hotwords_file=hw_path,
                hotwords_score=self.hotwords_score,
                provider=provider,
            )
            self.active_provider = provider
            log.info("Initialized Parakeet TDT recognizer with provider=%s", provider)
        except Exception as exc:
            log.warning("Failed to initialize with provider=%s (%s), falling back to CPU", provider, exc)
            self.active_provider = "cpu"
            try:
                self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                    encoder=encoder,
                    decoder=decoder,
                    joiner=joiner,
                    tokens=tokens,
                    num_threads=self.num_threads,
                    sample_rate=16000,
                    feature_dim=80,
                    decoding_method=decoding_method,
                    model_type="nemo_transducer",
                    max_active_paths=4,
                    hotwords_file=hw_path,
                    hotwords_score=self.hotwords_score,
                    provider="cpu",
                )
            except Exception as exc2:
                log.warning("Failed to initialize with hotwords (%s), falling back to greedy search without hotwords", exc2)
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
                    provider="cpu",
                )

        self._is_loaded = True
        log.info("Parakeet TDT engine ready (provider=%s, hotwords=%s)", self.active_provider, bool(hw_path))

    def is_loaded(self) -> bool:
        return self._is_loaded and self.recognizer is not None

    def transcribe(self, audio: np.ndarray, fast: bool = False) -> dict:
        """Transcribe 16kHz float32 audio with adaptive VAD chunking and acoustic timestamp stitching."""
        if not self.is_loaded():
            raise RuntimeError("Parakeet TDT model is not loaded")

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if audio.ndim > 1:
            audio = audio.flatten()

        duration_sec = len(audio) / 16000.0

        if duration_sec > 20.0 and not fast:
            log.info("Parakeet audio duration (%.1fs) exceeds 20s; chunking via VAD...", duration_sec)

            def _get_safe_segments(audio_seg: np.ndarray, offset: int = 0, min_silence: int = 500) -> list[dict]:
                try:
                    from audio.capture import get_speech_timestamps
                    timestamps = get_speech_timestamps(
                        audio_seg,
                        min_silence_duration_ms=min_silence,
                        speech_pad_ms=200,
                        sampling_rate=16000,
                    )
                except Exception as e:
                    log.warning("VAD chunking failed: %s", e)
                    timestamps = []

                if not timestamps:
                    timestamps = [{"start": 0, "end": len(audio_seg)}]

                max_samples = 18 * 16000
                final_segments = []
                for ts in timestamps:
                    seg_len = ts["end"] - ts["start"]
                    if seg_len > max_samples and min_silence >= 100:
                        sub_segments = _get_safe_segments(
                            audio_seg[ts["start"]:ts["end"]],
                            offset=0,
                            min_silence=max(50, min_silence // 2)
                        )
                        for sub_ts in sub_segments:
                            final_segments.append({
                                "start": offset + ts["start"] + sub_ts["start"],
                                "end": offset + ts["start"] + sub_ts["end"]
                            })
                    elif seg_len > max_samples:
                        for j in range(0, seg_len, max_samples):
                            final_segments.append({
                                "start": offset + ts["start"] + j,
                                "end": offset + min(ts["end"], ts["start"] + j + max_samples)
                            })
                    else:
                        final_segments.append({
                            "start": offset + ts["start"],
                            "end": offset + ts["end"]
                        })
                return final_segments

            safe_segments = _get_safe_segments(audio, 0, 500)

            # Acoustic timestamp cut-point stitching algorithm:
            # For N overlapping/adjacent segments, compute mid-point cut points in global seconds.
            # Each segment decodes with acoustic context padding, and tokens are filtered by their
            # global timestamp to prevent boundary truncation or duplication.
            pad_samp = 3200  # 200ms acoustic context pad
            n_segs = len(safe_segments)
            cut_points = []
            for i in range(n_segs - 1):
                mid_sample = (safe_segments[i]["end"] + safe_segments[i + 1]["start"]) / 2.0
                cut_points.append(mid_sample / 16000.0)

            results = []
            for i, ts in enumerate(safe_segments):
                seg_start = max(0, ts["start"] - pad_samp)
                seg_end = min(len(audio), ts["end"] + pad_samp)
                segment = np.ascontiguousarray(audio[seg_start:seg_end], dtype=np.float32)
                if len(segment) < 800:
                    continue

                stream = self.recognizer.create_stream()
                stream.accept_waveform(16000, segment)
                self.recognizer.decode_stream(stream)

                tokens = getattr(stream.result, "tokens", [])
                ts_list = getattr(stream.result, "timestamps", [])
                seg_offset_sec = seg_start / 16000.0

                if tokens and ts_list and len(tokens) == len(ts_list):
                    kept_tokens = []
                    for tok, t_rel in zip(tokens, ts_list):
                        t_glob = seg_offset_sec + t_rel
                        if i > 0 and t_glob <= cut_points[i - 1]:
                            continue
                        if i < n_segs - 1 and t_glob > cut_points[i]:
                            continue
                        kept_tokens.append(tok)
                    t = "".join(kept_tokens).replace("\u2581", " ").strip()
                else:
                    t = stream.result.text.strip()

                if t:
                    results.append(t)

            text = " ".join(results).strip()
            return {"text": text, "language": "en"}

        else:
            stream = self.recognizer.create_stream()
            stream.accept_waveform(16000, audio)
            self.recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            return {"text": text, "language": "en"}


# Alias for backward compatibility
ParakeetEngine = ParakeetTDTEngine


