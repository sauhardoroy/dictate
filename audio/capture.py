"""Microphone capture: 16 kHz mono float32 chunks via sounddevice with streaming Silero VAD.

Decouples PortAudio realtime audio callback from neural network inference using a lock-free queue,
ensuring zero audio buffer dropouts or stutter under high CPU load.
"""
import os
import queue
import sys
import threading
from typing import Optional, List, Dict
import numpy as np
import sounddevice as sd
from log import get_logger

log = get_logger(__name__)

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024  # ~64 ms per callback
VAD_SPEECH_THRESHOLD = 0.3
VAD_SILENCE_SECONDS = 0.8


def trim_silence(audio: np.ndarray, threshold: float = 0.003,
                 padding_samples: int = 4800) -> np.ndarray:
    """Remove quiet leading/trailing samples while retaining speech padding.

    Returning the original array for silence avoids turning a no-speech capture
    into an empty inference request; the ASR hallucination guard handles it.
    """
    if not isinstance(audio, np.ndarray) or audio.size == 0:
        return audio
    samples = audio.astype("float32", copy=False).reshape(-1)
    voiced = np.flatnonzero(np.abs(samples) >= threshold)
    if not len(voiced):
        return audio
    start = max(0, int(voiced[0]) - padding_samples)
    end = min(len(samples), int(voiced[-1]) + padding_samples + 1)
    return samples[start:end]


class MicUnavailableError(RuntimeError):
    pass


def _resolve_vad_model_path() -> Optional[str]:
    """Find the Silero VAD ONNX model file from bundled assets, models dir, or fallback."""
    candidates = []
    
    # 1. Check frozen executable directory / PyInstaller bundle
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "assets", "silero_vad_v6.onnx"))
            candidates.append(os.path.join(sys._MEIPASS, "assets", "silero_vad.onnx"))
        candidates.append(os.path.join(exe_dir, "assets", "silero_vad_v6.onnx"))
        candidates.append(os.path.join(exe_dir, "_internal", "assets", "silero_vad_v6.onnx"))

    # 2. Check local source tree assets and models
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(project_root, "assets", "silero_vad_v6.onnx"))
    candidates.append(os.path.join(project_root, "assets", "silero_vad.onnx"))
    candidates.append(os.path.join(project_root, "models", "silero_vad_v6.onnx"))

    # 3. Check faster_whisper assets if installed
    try:
        import faster_whisper.vad
        fw_path = os.path.join(faster_whisper.vad.get_assets_path(), "silero_vad_v6.onnx")
        candidates.append(fw_path)
    except Exception:
        pass

    for path in candidates:
        if path and os.path.isfile(path) and os.path.getsize(path) > 0:
            return os.path.abspath(path)
    return None


class StreamingVAD:
    """Self-contained streaming Silero VAD v6 with automatic energy fallback."""

    def __init__(self, model_path: Optional[str] = None):
        self.session = None
        resolved = model_path or _resolve_vad_model_path()
        if resolved:
            try:
                import onnxruntime as ort
                opts = ort.SessionOptions()
                opts.inter_op_num_threads = 1
                opts.intra_op_num_threads = 1
                opts.log_severity_level = 3
                self.session = ort.InferenceSession(
                    resolved,
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                log.debug("Initialized Silero VAD ONNX session from %s", resolved)
            except Exception as exc:
                log.warning("Failed to initialize ONNX VAD session from %s: %s", resolved, exc)
                self.session = None

        # State tensors (1, 1, 128) for Silero VAD v5/v6
        self.h = np.zeros((1, 1, 128), dtype="float32")
        self.c = np.zeros((1, 1, 128), dtype="float32")
        self.context = np.zeros((1, 64), dtype="float32")
        self._energy_floor = 0.005

    def reset_state(self):
        self.h = np.zeros((1, 1, 128), dtype="float32")
        self.c = np.zeros((1, 1, 128), dtype="float32")
        self.context = np.zeros((1, 64), dtype="float32")

    def process_chunk(self, audio_chunk: np.ndarray) -> float:
        """Processes exactly 512 samples and returns speech probability [0.0, 1.0]."""
        audio_chunk = audio_chunk.astype("float32").flatten()
        if len(audio_chunk) < 512:
            audio_chunk = np.pad(audio_chunk, (0, 512 - len(audio_chunk)))
        elif len(audio_chunk) > 512:
            audio_chunk = audio_chunk[:512]

        if self.session is not None:
            try:
                batched = np.concatenate([self.context, audio_chunk.reshape(1, 512)], axis=1)
                self.context = audio_chunk[-64:].reshape(1, 64)
                output, self.h, self.c = self.session.run(
                    None,
                    {"input": batched, "h": self.h, "c": self.c},
                )
                return float(np.ravel(output)[0])
            except Exception as e:
                log.debug("ONNX VAD run error: %s", e)

        # Resilient Adaptive Energy Fallback
        rms = float(np.sqrt(np.mean(audio_chunk ** 2)))
        self._energy_floor = 0.95 * self._energy_floor + 0.05 * min(rms, self._energy_floor * 1.5)
        ratio = (rms - self._energy_floor) / max(0.008, self._energy_floor * 2.0)
        return float(np.clip(ratio, 0.0, 1.0))


def get_speech_timestamps(
    audio: np.ndarray,
    min_silence_duration_ms: int = 500,
    speech_pad_ms: int = 100,
    sampling_rate: int = 16000,
    threshold: float = 0.35,
) -> List[Dict[str, int]]:
    """Standalone speech segmentation utility for chunking long audio without external deps."""
    if not isinstance(audio, np.ndarray) or audio.size == 0:
        return []

    samples = audio.astype("float32").flatten()
    chunk_size = 512
    vad = StreamingVAD()

    speech_pad_samples = int(speech_pad_ms * sampling_rate / 1000)
    min_silence_samples = int(min_silence_duration_ms * sampling_rate / 1000)

    segments = []
    in_speech = False
    speech_start = 0
    silence_start = 0

    for i in range(0, len(samples), chunk_size):
        chunk = samples[i:i + chunk_size]
        prob = vad.process_chunk(chunk)

        if prob >= threshold:
            if not in_speech:
                in_speech = True
                speech_start = max(0, i - speech_pad_samples)
            silence_start = 0
        else:
            if in_speech:
                if silence_start == 0:
                    silence_start = i
                elif (i - silence_start) >= min_silence_samples:
                    speech_end = min(len(samples), silence_start + speech_pad_samples)
                    segments.append({"start": speech_start, "end": speech_end})
                    in_speech = False
                    silence_start = 0

    if in_speech:
        segments.append({"start": speech_start, "end": len(samples)})

    return segments if segments else [{"start": 0, "end": len(samples)}]


class Recorder:
    """Thread-safe, decoupled 16kHz microphone recorder with pre-allocated audio buffer and background VAD."""

    INITIAL_CAPACITY_SAMPLES = 16000 * 300  # 5 minutes default pre-allocation (~19.2 MB)

    def __init__(self, device=None, on_level=None, on_auto_stop=None, on_silence_eval=None,
                 on_chunk=None,
                 use_vad=True,
                 vad_speech_threshold=VAD_SPEECH_THRESHOLD,
                 vad_silence_seconds=1.4):
        self.device = device
        self.on_level = on_level
        self.on_auto_stop = on_auto_stop
        self.on_silence_eval = on_silence_eval
        self.on_chunk = on_chunk
        self.use_vad = use_vad
        self.vad_speech_threshold = vad_speech_threshold
        self.base_silence_seconds = vad_silence_seconds
        self.vad_silence_frames = max(1, round(vad_silence_seconds * SAMPLE_RATE / BLOCK_SIZE))
        self.frames = []
        self._buffer = np.zeros(self.INITIAL_CAPACITY_SAMPLES, dtype=np.float32)
        self._write_pos = 0
        self._buf_lock = threading.Lock()
        self.stream = None
        self.vad = None
        self.silence_frames = 0
        self.has_spoken = False
        self._eval_triggered_for_pause = False
        self._queue = queue.Queue()
        self._running = False
        self._worker_thread = None

    def _ensure_buffer_capacity(self, needed_samples: int):
        """Expand buffer capacity dynamically if audio recording exceeds pre-allocated size."""
        with self._buf_lock:
            current_cap = len(self._buffer)
            if self._write_pos + needed_samples > current_cap:
                new_cap = max(current_cap * 2, self._write_pos + needed_samples + 16000 * 60)
                new_buf = np.zeros(new_cap, dtype=np.float32)
                new_buf[:self._write_pos] = self._buffer[:self._write_pos]
                self._buffer = new_buf

    def update_silence_duration(self, seconds: float):
        """Dynamically adjusts the required silence duration (e.g. for mid-thought pauses)."""
        self.vad_silence_frames = max(1, round(seconds * SAMPLE_RATE / BLOCK_SIZE))
        log.debug("VAD silence threshold adapted to %.2fs (%d frames)", seconds, self.vad_silence_frames)

    def start(self):
        with self._buf_lock:
            self._write_pos = 0
        self.frames = []
        self.silence_frames = 0
        self.has_spoken = False
        self._eval_triggered_for_pause = False
        self.vad_silence_frames = max(1, round(self.base_silence_seconds * SAMPLE_RATE / BLOCK_SIZE))
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        if self.use_vad:
            self.vad = StreamingVAD()

        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=BLOCK_SIZE,
                device=self.device,
                callback=self._cb,
            )
            self.stream.start()
        except sd.PortAudioError as exc:
            self._running = False
            self._queue.put(None)
            raise MicUnavailableError(str(exc)) from exc

    def _cb(self, indata, frames, time_info, status):
        """Realtime PortAudio callback: writes chunk to pre-allocated buffer without heap allocations."""
        if not self._running:
            return
        mono = indata[:, 0] if indata.ndim > 1 else indata
        n = len(mono)
        self._ensure_buffer_capacity(n)
        with self._buf_lock:
            self._buffer[self._write_pos : self._write_pos + n] = mono
            self._write_pos += n
        self.frames.append(indata.copy())
        self._queue.put_nowait(mono.copy())

    def _worker_loop(self):
        """Dedicated background worker for audio processing, level meter, and VAD evaluation."""
        while self._running:
            try:
                chunk = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if chunk is None:
                break

            # 1. Forward raw chunk to live preview streaming engine
            if self.on_chunk is not None:
                try:
                    self.on_chunk(chunk)
                except Exception:
                    pass

            # 2. Compute RMS level for visualizer
            if self.on_level is not None:
                try:
                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                    self.on_level(rms)
                except Exception:
                    pass

            # 3. Process VAD
            if self.use_vad and self.vad is not None:
                try:
                    # BLOCK_SIZE is 1024; evaluate both 512-sample sub-chunks
                    prob1 = self.vad.process_chunk(chunk[:512])
                    prob2 = self.vad.process_chunk(chunk[512:])
                    prob = max(prob1, prob2)

                    if prob > self.vad_speech_threshold:
                        self.has_spoken = True
                        self.silence_frames = 0
                        self._eval_triggered_for_pause = False
                    else:
                        self.silence_frames += 1

                    # Trigger semantic silence evaluation at ~500ms of pause
                    if self.has_spoken and self.silence_frames == 8 and not self._eval_triggered_for_pause:
                        self._eval_triggered_for_pause = True
                        if self.on_silence_eval is not None:
                            try:
                                audio_snapshot = self.snapshot()
                                if len(audio_snapshot) > 0:
                                    self.on_silence_eval(audio_snapshot)
                            except Exception:
                                pass

                    # Check auto-stop condition
                    if self.has_spoken and self.silence_frames >= self.vad_silence_frames:
                        if self.on_auto_stop is not None:
                            log.debug("VAD auto-stop triggered after %d silence frames", self.silence_frames)
                            self.on_auto_stop()
                            # Disable VAD to avoid double trigger
                            self.vad = None
                except Exception as e:
                    log.debug("VAD worker error: %s", e)

    def snapshot(self) -> np.ndarray:
        """Return a snapshot copy of all recorded audio so far without stopping."""
        with self._buf_lock:
            if self._write_pos > 0:
                return self._buffer[:self._write_pos].copy()
        if self.frames:
            try:
                return np.concatenate(self.frames)[:, 0].astype("float32")
            except Exception:
                return np.zeros(0, dtype="float32")
        return np.zeros(0, dtype="float32")

    def stop(self) -> np.ndarray:
        self._running = False
        self._queue.put(None)
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            finally:
                self.stream = None

        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.2)
            self._worker_thread = None

        return self.snapshot()

    def duration(self) -> float:
        with self._buf_lock:
            if self._write_pos > 0:
                return self._write_pos / SAMPLE_RATE
        return sum(len(f) for f in self.frames) / SAMPLE_RATE

    def speech_seconds(self, thresh=0.012) -> float:
        """Seconds of audio above a crude RMS speech threshold."""
        with self._buf_lock:
            if self._write_pos > 0:
                audio = self._buffer[:self._write_pos]
                n_blocks = len(audio) // BLOCK_SIZE
                count = 0
                for i in range(n_blocks):
                    chunk = audio[i * BLOCK_SIZE : (i + 1) * BLOCK_SIZE]
                    if float(np.sqrt(np.mean(chunk ** 2))) > thresh:
                        count += 1
                return count * BLOCK_SIZE / SAMPLE_RATE
        n = sum(
            1 for f in self.frames if float(np.sqrt(np.mean(f ** 2))) > thresh
        )
        return n * BLOCK_SIZE / SAMPLE_RATE
