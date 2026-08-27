import os
import sys

from .base import ASREngine
from log import get_logger

log = get_logger(__name__)


def resolve_model_path(model_size: str) -> str:
    """Resolve model size name or bundled directory path."""
    # Check bundled models directory (e.g. in frozen app or adjacent folder)
    candidates = []
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        # 1. Next to exe
        candidates.append(os.path.join(exe_dir, "models", model_size))
        # 2. In _internal subfolder (PyInstaller 6+ default layout)
        candidates.append(os.path.join(exe_dir, "_internal", "models", model_size))
        # 3. In _MEIPASS if bundled inside
        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "models", model_size))
    
    # 3. In project models folder
    candidates.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", model_size))

    for path in candidates:
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "model.bin")):
            return path

    return model_size


def is_local_model_available(model_size: str) -> bool:
    """Whether a complete model was bundled or downloaded beside the app."""
    resolved = resolve_model_path(model_size)
    return resolved != model_size and os.path.isdir(resolved)


def model_loading_message(model_size: str) -> str:
    """Human-readable state for a non-blocking first run."""
    if is_local_model_available(model_size):
        return f"Loading {model_size} model…"
    return f"Downloading {model_size} model (first run only)…"


def _setup_cuda_dlls():
    """Ensure Windows locates NVIDIA CUDA / cuDNN DLLs from installed pip packages, frozen bundle, or CUDA Toolkit."""
    if sys.platform != "win32":
        return

    dll_dirs = []

    # 1. If running as a frozen PyInstaller application
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        for cand in [exe_dir, os.path.join(exe_dir, "_internal"), getattr(sys, "_MEIPASS", "")]:
            if cand and os.path.isdir(cand) and cand not in dll_dirs:
                dll_dirs.append(cand)

    # 2. Installed python nvidia packages in virtualenv/site-packages
    for pkg in ("nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_nvrtc", "nvidia.cuda_runtime"):
        try:
            mod = __import__(pkg, fromlist=["__path__"])
            for p in getattr(mod, "__path__", []):
                bin_dir = os.path.join(p, "bin")
                if os.path.isdir(bin_dir) and bin_dir not in dll_dirs:
                    dll_dirs.append(bin_dir)
        except ImportError:
            pass

    # 3. System CUDA_PATH if defined
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        bin_dir = os.path.join(cuda_path, "bin")
        if os.path.isdir(bin_dir) and bin_dir not in dll_dirs:
            dll_dirs.append(bin_dir)

    for d in dll_dirs:
        try:
            os.add_dll_directory(d)
        except Exception:
            pass
        if d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


class FasterWhisperEngine(ASREngine):
    name = "faster-whisper"

    def __init__(self, model_size="small.en", device="auto", compute_type="auto",
                 language="en", vad_filter=True, initial_prompt="", cpu_threads=0):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language or None
        self.vad_filter = vad_filter
        # Mutable at runtime (no reload needed): settings dialog updates this
        # attribute directly so custom-vocabulary edits take effect immediately.
        self.initial_prompt = initial_prompt or ""
        self.cpu_threads = cpu_threads or 0
        self.model = None

    def load(self):
        _setup_cuda_dlls()
        from faster_whisper import WhisperModel  # deferred: heavy import
        resolved_model = resolve_model_path(self.model_size)
        log.info(
            "loading faster-whisper model %r (device=%s, compute=%s, cpu_threads=%s, resolved to %r)",
            self.model_size, self.device, self.compute_type,
            self.cpu_threads or "auto", resolved_model,
        )
        try:
            self.model = WhisperModel(
                resolved_model,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
            log.info("faster-whisper model %r ready (device=%s)", self.model_size, self.device)
        except Exception as exc:
            # If CUDA or auto-detection failed on a machine without a compatible NVIDIA GPU,
            # fall back gracefully to CPU so the app never crashes.
            if self.device in ("cuda", "auto"):
                log.warning(
                    "Failed to initialize faster-whisper on device=%s (%s); falling back to CPU",
                    self.device, exc,
                )
                self.device = "cpu"
                self.compute_type = "auto"
                self.model = WhisperModel(
                    resolved_model,
                    device="cpu",
                    compute_type="auto",
                    cpu_threads=self.cpu_threads,
                )
                log.info("faster-whisper model %r ready on CPU fallback", self.model_size)
            else:
                raise

    def is_loaded(self) -> bool:
        return self.model is not None

    def transcribe(self, audio, fast: bool = False) -> dict:
        if not self.model:
            raise RuntimeError("model not loaded")
        log.debug("transcribe start: %d samples (fast=%s)", len(audio) if hasattr(audio, "__len__") else 0, fast)
        segments, _info = self.model.transcribe(
            audio,
            language=self.language,
            vad_filter=False if fast else self.vad_filter,
            beam_size=1,
            temperature=0.0,
            condition_on_previous_text=False,
            without_timestamps=True if fast else False,
            initial_prompt=self.initial_prompt or None,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        log.debug("transcribe done: %d chars", len(text))
        return {"text": text}
