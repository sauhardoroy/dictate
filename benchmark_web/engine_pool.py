"""Unified Runtime Engine Pool for Streaming and File ASR Benchmarking."""
import os
import sys
import time
import tarfile
import urllib.request
import threading
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from log import get_logger

from benchmark_web.models_registry import AVAILABLE_MODELS, get_models_dir, is_model_downloaded

log = get_logger(__name__)


class EnginePool:
    def __init__(self):
        self._loaded_engines: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def download_model(self, model_id: str, progress_callback=None) -> bool:
        """Download and prepare the model files for the given model ID."""
        meta = AVAILABLE_MODELS.get(model_id)
        if not meta:
            raise ValueError(f"Unknown model: {model_id}")

        models_base = get_models_dir()
        os.makedirs(models_base, exist_ok=True)
        framework = meta.get("framework")

        if framework == "sherpa-onnx":
            if "hf_repo" in meta:
                import huggingface_hub
                log.info("Downloading %s from HuggingFace...", meta["hf_repo"])
                huggingface_hub.snapshot_download(
                    repo_id=meta["hf_repo"],
                    allow_patterns=["*.onnx", "tokens.txt"],
                )
                return True
            elif "url" in meta:
                archive_name = f"{model_id}.tar.bz2"
                archive_path = os.path.join(models_base, archive_name)
                log.info("Downloading %s from %s...", model_id, meta["url"])
                urllib.request.urlretrieve(meta["url"], archive_path)
                log.info("Extracting %s...", archive_name)
                with tarfile.open(archive_path, "r:bz2") as tar:
                    tar.extractall(models_base)
                if os.path.exists(archive_path):
                    os.remove(archive_path)
                return True

        elif framework == "faster-whisper":
            from faster_whisper import WhisperModel
            m_id = meta.get("model_id", "")
            log.info("Downloading Faster-Whisper model %s...", m_id)
            model = WhisperModel(m_id, device="cpu", compute_type="int8")
            return True

        return False

    def get_or_load_engine(self, model_id: str) -> Any:
        """Load engine into memory (caching loaded instances)."""
        with self._lock:
            if model_id in self._loaded_engines:
                return self._loaded_engines[model_id]

            meta = AVAILABLE_MODELS.get(model_id)
            if not meta:
                raise ValueError(f"Unknown model: {model_id}")

            models_base = get_models_dir()
            framework = meta.get("framework")

            if framework == "sherpa-onnx":
                import sherpa_onnx
                import huggingface_hub

                if model_id == "nemo-fast-conformer-80ms":
                    # NVIDIA Streaming FastConformer CTC (Online)
                    model_dir = huggingface_hub.snapshot_download(meta["hf_repo"], allow_patterns=["model.onnx", "tokens.txt"])
                    model_file = os.path.join(model_dir, "model.onnx")
                    tokens_file = os.path.join(model_dir, "tokens.txt")

                    recognizer = sherpa_onnx.OnlineRecognizer.from_nemo_ctc(
                        model=model_file,
                        tokens=tokens_file,
                        num_threads=4,
                        sample_rate=16000,
                        feature_dim=80,
                        decoding_method="greedy_search",
                    )
                    self._loaded_engines[model_id] = ("sherpa_online", recognizer)
                    return self._loaded_engines[model_id]

                elif model_id == "sense-voice-small":
                    # Alibaba SenseVoice Small (Offline)
                    model_dir = huggingface_hub.snapshot_download(meta["hf_repo"], allow_patterns=["*.onnx", "tokens.txt"])
                    model_file = os.path.join(model_dir, "model.int8.onnx" if os.path.exists(os.path.join(model_dir, "model.int8.onnx")) else "model.onnx")
                    tokens_file = os.path.join(model_dir, "tokens.txt")

                    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                        model=model_file,
                        tokens=tokens_file,
                        num_threads=4,
                        use_itn=True,
                    )
                    self._loaded_engines[model_id] = ("sherpa_offline", recognizer)
                    return self._loaded_engines[model_id]

                elif model_id.startswith("moonshine-"):
                    # Useful Sensors Moonshine (Offline)
                    model_dir = huggingface_hub.snapshot_download(meta["hf_repo"], allow_patterns=["*.onnx", "tokens.txt"])
                    preprocess = os.path.join(model_dir, "preprocess.onnx")
                    encode = os.path.join(model_dir, "encode.int8.onnx")
                    uncached_decode = os.path.join(model_dir, "uncached_decode.int8.onnx")
                    cached_decode = os.path.join(model_dir, "cached_decode.int8.onnx")
                    tokens = os.path.join(model_dir, "tokens.txt")

                    recognizer = sherpa_onnx.OfflineRecognizer.from_moonshine(
                        preprocessor=preprocess,
                        encoder=encode,
                        uncached_decoder=uncached_decode,
                        cached_decoder=cached_decode,
                        tokens=tokens,
                        num_threads=4,
                    )
                    self._loaded_engines[model_id] = ("sherpa_offline", recognizer)
                    return self._loaded_engines[model_id]

                elif "hf_repo" in meta:
                    # Parakeet TDT (NVIDIA NeMo Transducer)
                    model_dir = huggingface_hub.snapshot_download(meta["hf_repo"], allow_patterns=["*.onnx", "tokens.txt"])
                    encoder = os.path.join(model_dir, "encoder.int8.onnx")
                    decoder = os.path.join(model_dir, "decoder.int8.onnx")
                    joiner = os.path.join(model_dir, "joiner.int8.onnx")
                    tokens = os.path.join(model_dir, "tokens.txt")

                    engine = sherpa_onnx.OfflineRecognizer.from_transducer(
                        encoder=encoder,
                        decoder=decoder,
                        joiner=joiner,
                        tokens=tokens,
                        num_threads=4,
                        sample_rate=16000,
                        feature_dim=80,
                        decoding_method="greedy_search",
                        model_type="nemo_transducer",
                    )
                    self._loaded_engines[model_id] = ("sherpa_offline", engine)
                    return self._loaded_engines[model_id]

                elif "dir_name" in meta:
                    dir_name = meta["dir_name"]
                    model_dir = os.path.join(models_base, dir_name)
                    if not os.path.exists(model_dir):
                        self.download_model(model_id)

                    onnx_files = [f for f in os.listdir(model_dir) if f.endswith(".int8.onnx") or f.endswith(".onnx")]
                    enc = [f for f in onnx_files if "encoder" in f][0]
                    dec = [f for f in onnx_files if "decoder" in f][0]
                    joi = [f for f in onnx_files if "joiner" in f][0]
                    tokens = os.path.join(model_dir, "tokens.txt")

                    recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                        tokens=tokens,
                        encoder=os.path.join(model_dir, enc),
                        decoder=os.path.join(model_dir, dec),
                        joiner=os.path.join(model_dir, joi),
                        num_threads=2,
                        sample_rate=16000,
                        feature_dim=80,
                        decoding_method="greedy_search",
                    )
                    self._loaded_engines[model_id] = ("sherpa_online", recognizer)
                    return self._loaded_engines[model_id]

            elif framework == "faster-whisper":
                from faster_whisper import WhisperModel
                m_id = meta.get("model_id", "")
                model = WhisperModel(m_id, device="cpu", compute_type="int8")
                self._loaded_engines[model_id] = ("whisper", model)
                return self._loaded_engines[model_id]

            raise RuntimeError(f"Unsupported framework: {framework}")

    def create_streaming_session(self, model_id: str):
        """Create a real-time streaming session for any model."""
        engine_type, engine = self.get_or_load_engine(model_id)
        stream = engine.create_stream() if engine_type == "sherpa_online" else None
        return StreamingSession(engine_type, engine, stream)

    def benchmark_audio(self, model_id: str, audio_pcm: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """Benchmark a complete audio array against the specified model."""
        if audio_pcm.dtype != np.float32:
            audio_pcm = audio_pcm.astype(np.float32)
        if audio_pcm.ndim > 1:
            audio_pcm = audio_pcm.mean(axis=1)

        audio_duration_sec = len(audio_pcm) / sample_rate
        engine_type, engine = self.get_or_load_engine(model_id)

        t_start = time.perf_counter()

        if engine_type == "sherpa_offline":
            stream = engine.create_stream()
            stream.accept_waveform(sample_rate, audio_pcm)
            engine.decode_stream(stream)
            transcript = stream.result.text.strip()

        elif engine_type == "sherpa_online":
            stream = engine.create_stream()
            chunk_size = 1024
            for i in range(0, len(audio_pcm), chunk_size):
                chunk = audio_pcm[i:i + chunk_size]
                stream.accept_waveform(sample_rate, chunk)
                while engine.is_ready(stream):
                    engine.decode_stream(stream)
            res = engine.get_result(stream)
            transcript = (res.text if hasattr(res, "text") else str(res)).strip()

        elif engine_type == "whisper":
            segments, _info = engine.transcribe(
                audio_pcm,
                beam_size=1,
                language="en",
                temperature=0.0,
            )
            transcript = " ".join([seg.text.strip() for seg in segments]).strip()
        else:
            raise RuntimeError(f"Unknown engine type {engine_type}")

        t_end = time.perf_counter()
        elapsed_sec = t_end - t_start
        rtf = elapsed_sec / max(0.001, audio_duration_sec)  # Real Time Factor

        return {
            "model_id": model_id,
            "transcript": transcript,
            "audio_duration_sec": round(audio_duration_sec, 2),
            "inference_time_sec": round(elapsed_sec, 4),
            "rtf": round(rtf, 4),
            "speedup": round(1.0 / max(0.0001, rtf), 1),
            "chars_count": len(transcript),
            "words_count": len(transcript.split()),
        }


class StreamingSession:
    """Manages an active real-time online streaming recognition session for any model."""
    def __init__(self, engine_type: str, recognizer: Any, stream: Any = None):
        self.engine_type = engine_type
        self.recognizer = recognizer
        self.stream = stream
        self.audio_buffer: List[np.ndarray] = []
        self.last_text = ""
        self.last_eval_time = 0.0
        self._lock = threading.Lock()

    def process_chunk(self, chunk: np.ndarray) -> Tuple[Optional[str], float]:
        """Accept an audio chunk (16kHz float32), decode, and return (new_text, chunk_latency_ms)."""
        with self._lock:
            if chunk.dtype != np.float32:
                chunk = chunk.astype(np.float32)
            if chunk.ndim > 1:
                chunk = chunk.flatten()

            t0 = time.perf_counter()
            self.audio_buffer.append(chunk)

            if self.engine_type == "sherpa_online":
                self.stream.accept_waveform(16000, chunk)
                while self.recognizer.is_ready(self.stream):
                    self.recognizer.decode_stream(self.stream)
                t1 = time.perf_counter()
                latency_ms = (t1 - t0) * 1000.0
                res = self.recognizer.get_result(self.stream)
                current_text = (res.text if hasattr(res, "text") else str(res)).strip()
                self.last_text = current_text
                return current_text, latency_ms

            elif self.engine_type == "sherpa_offline":
                now = time.perf_counter()
                if now - self.last_eval_time >= 0.22:
                    self.last_eval_time = now
                    concat_audio = np.concatenate(self.audio_buffer)
                    stream = self.recognizer.create_stream()
                    stream.accept_waveform(16000, concat_audio)
                    self.recognizer.decode_stream(stream)
                    self.last_text = stream.result.text.strip()
                t1 = time.perf_counter()
                latency_ms = (t1 - t0) * 1000.0
                return self.last_text, latency_ms

            elif self.engine_type == "whisper":
                now = time.perf_counter()
                if now - self.last_eval_time >= 0.30:
                    self.last_eval_time = now
                    concat_audio = np.concatenate(self.audio_buffer)
                    eval_audio = concat_audio if len(concat_audio) <= 48000 else concat_audio[-48000:]
                    segments, _ = self.recognizer.transcribe(eval_audio, beam_size=1, language="en", temperature=0.0)
                    self.last_text = " ".join([s.text.strip() for s in segments]).strip()
                t1 = time.perf_counter()
                latency_ms = (t1 - t0) * 1000.0
                return self.last_text, latency_ms

            return self.last_text, 0.0

    def finish(self) -> str:
        with self._lock:
            if not self.audio_buffer:
                return self.last_text

            concat_audio = np.concatenate(self.audio_buffer)
            if self.engine_type == "sherpa_online":
                res = self.recognizer.get_result(self.stream)
                return (res.text if hasattr(res, "text") else str(res)).strip()
            elif self.engine_type == "sherpa_offline":
                stream = self.recognizer.create_stream()
                stream.accept_waveform(16000, concat_audio)
                self.recognizer.decode_stream(stream)
                return stream.result.text.strip()
            elif self.engine_type == "whisper":
                segments, _ = self.recognizer.transcribe(concat_audio, beam_size=1, language="en", temperature=0.0)
                return " ".join([s.text.strip() for s in segments]).strip()

            return self.last_text


# Global Engine Pool Singleton
global_engine_pool = EnginePool()
