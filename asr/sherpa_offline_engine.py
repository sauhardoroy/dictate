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
        from asr.model_manager import ensure_model_downloaded

        log.info("Loading Alibaba SenseVoice offline model: %s...", self.model_id)

        if self.model_id == "sense-voice-small":
            model_dir = ensure_model_downloaded("sense-voice-small")
            model_file = os.path.join(model_dir, "model.int8.onnx" if os.path.exists(os.path.join(model_dir, "model.int8.onnx")) else "model.onnx")
            tokens_file = os.path.join(model_dir, "tokens.txt")

            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_file,
                tokens=tokens_file,
                num_threads=self.num_threads,
                use_itn=True,
            )
            self._is_loaded = True
        else:
            raise ValueError(f"Unsupported offline model: {self.model_id}. Only 'sense-voice-small' is supported.")

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

        duration_sec = len(audio) / 16000.0

        if duration_sec > 25.0:
            log.info("Audio duration (%.1fs) exceeds 25s; chunking via VAD...", duration_sec)
            
            def _get_safe_segments(audio_seg: np.ndarray, offset: int = 0, min_silence: int = 500) -> list[dict]:
                try:
                    from faster_whisper.vad import get_speech_timestamps, VadOptions
                    timestamps = get_speech_timestamps(
                        audio_seg, 
                        vad_options=VadOptions(
                            min_silence_duration_ms=min_silence,
                            speech_pad_ms=100
                        ),
                        sampling_rate=16000
                    )
                except Exception as e:
                    log.warning("VAD chunking failed: %s", e)
                    timestamps = []

                if not timestamps:
                    timestamps = [{"start": 0, "end": len(audio_seg)}]

                max_samples = 25 * 16000
                final_segments = []
                for ts in timestamps:
                    seg_len = ts["end"] - ts["start"]
                    # If the segment is STILL too long and we can lower the silence threshold further:
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
                        # Reached minimum silence threshold, MUST mechanically split as last resort
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
            
            results = []
            for i, ts in enumerate(safe_segments):
                segment = audio[ts["start"]:ts["end"]]
                stream = self.recognizer.create_stream()
                stream.accept_waveform(16000, segment)
                self.recognizer.decode_stream(stream)
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
