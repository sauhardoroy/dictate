"""Abstract ASR engine interface — keep the app model-agnostic."""
from abc import ABC, abstractmethod


class ASREngine(ABC):
    name = "base"

    @abstractmethod
    def load(self) -> None:
        """Download/initialize the model. May take minutes on first run."""

    @abstractmethod
    def is_loaded(self) -> bool:
        ...

    @abstractmethod
    def transcribe(self, audio) -> dict:
        """audio: np.float32 mono 16 kHz array, or a path to a wav/flac file.

        Returns {"text": str}. Raises on failure.
        """
