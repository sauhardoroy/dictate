"""Microphone capture: 16 kHz mono float32 chunks via sounddevice with streaming Silero VAD."""
import numpy as np
import sounddevice as sd
from log import get_logger

log = get_logger(__name__)

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024  # ~64 ms per callback
VAD_SPEECH_THRESHOLD = 0.3
VAD_SILENCE_SECONDS = 0.8


def trim_silence(audio: np.ndarray, threshold: float = 0.012,
                 padding_samples: int = 1600) -> np.ndarray:
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


class StreamingVAD:
    def __init__(self):
        from faster_whisper.vad import get_vad_model
        self.model = get_vad_model()
        self.session = self.model.session
        # V3/V4 state tensors (1, 1, 128)
        self.h = np.zeros((1, 1, 128), dtype="float32")
        self.c = np.zeros((1, 1, 128), dtype="float32")
        self.context = np.zeros((1, 64), dtype="float32")

    def process_chunk(self, audio_chunk: np.ndarray) -> float:
        """Processes exactly 512 samples and returns speech probability [0.0, 1.0]."""
        audio_chunk = audio_chunk.astype("float32").flatten()
        batched = np.concatenate([self.context, audio_chunk.reshape(1, 512)], axis=1)
        self.context = audio_chunk[-64:].reshape(1, 64)
        output, self.h, self.c = self.session.run(
            None,
            {"input": batched, "h": self.h, "c": self.c},
        )
        return float(np.ravel(output)[0])


class Recorder:
    def __init__(self, device=None, on_level=None, on_auto_stop=None, on_silence_eval=None,
                 use_vad=True,
                 vad_speech_threshold=VAD_SPEECH_THRESHOLD,
                 vad_silence_seconds=1.4):
        self.device = device
        self.on_level = on_level
        self.on_auto_stop = on_auto_stop
        self.on_silence_eval = on_silence_eval
        self.use_vad = use_vad
        self.vad_speech_threshold = vad_speech_threshold
        self.base_silence_seconds = vad_silence_seconds
        self.vad_silence_frames = max(1, round(vad_silence_seconds * SAMPLE_RATE / BLOCK_SIZE))
        self.frames = []
        self.stream = None
        self.vad = None
        self.silence_frames = 0
        self.has_spoken = False
        self._eval_triggered_for_pause = False

    def update_silence_duration(self, seconds: float):
        """Dynamically adjusts the required silence duration (e.g. for mid-thought pauses)."""
        self.vad_silence_frames = max(1, round(seconds * SAMPLE_RATE / BLOCK_SIZE))
        log.debug("VAD silence threshold adapted to %.2fs (%d frames)", seconds, self.vad_silence_frames)

    def start(self):
        self.frames = []
        self.silence_frames = 0
        self.has_spoken = False
        self._eval_triggered_for_pause = False
        self.vad_silence_frames = max(1, round(self.base_silence_seconds * SAMPLE_RATE / BLOCK_SIZE))
        if self.use_vad:
            try:
                self.vad = StreamingVAD()
            except Exception as e:
                log.warning("Failed to initialize StreamingVAD: %s", e)
                self.vad = None

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
            raise MicUnavailableError(str(exc)) from exc

    def _cb(self, indata, frames, time_info, status):
        self.frames.append(indata.copy())

        if self.on_level:
            try:
                rms = float(np.sqrt(np.mean(indata ** 2)))
                self.on_level(rms)
            except Exception:
                pass

        if self.use_vad and self.vad is not None:
            try:
                # BLOCK_SIZE is 1024, VAD expects 512 samples per evaluation
                prob1 = self.vad.process_chunk(indata[:512, 0])
                prob2 = self.vad.process_chunk(indata[512:, 0])
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
                    if self.on_silence_eval:
                        try:
                            audio_snapshot = np.concatenate(self.frames)[:, 0].astype("float32")
                            self.on_silence_eval(audio_snapshot)
                        except Exception:
                            pass

                if self.has_spoken and self.silence_frames >= self.vad_silence_frames:
                    if self.on_auto_stop:
                        log.debug("VAD auto-stop triggered after %d silence frames", self.silence_frames)
                        self.on_auto_stop()
                        # Disable VAD to prevent multiple triggers
                        self.vad = None
            except Exception as e:
                log.debug("VAD processing error: %s", e)

    def stop(self) -> np.ndarray:
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            finally:
                self.stream = None
        if not self.frames:
            return np.zeros(0, dtype="float32")
        return np.concatenate(self.frames)[:, 0].astype("float32")

    def duration(self) -> float:
        return sum(len(f) for f in self.frames) / SAMPLE_RATE

    def speech_seconds(self, thresh=0.012) -> float:
        """Seconds of audio above a crude RMS speech threshold."""
        n = sum(
            1 for f in self.frames if float(np.sqrt(np.mean(f ** 2))) > thresh
        )
        return n * BLOCK_SIZE / SAMPLE_RATE
