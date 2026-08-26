import numpy as np

from audio.capture import trim_silence


def test_trim_silence_keeps_padding_around_detected_speech():
    audio = np.concatenate([np.zeros(1600), np.full(320, 0.1), np.zeros(1600)]).astype("float32")

    trimmed = trim_silence(audio, threshold=0.01, padding_samples=160)

    assert len(trimmed) == 640
    assert np.allclose(trimmed[160:480], 0.1)


def test_trim_silence_returns_original_when_no_speech_is_found():
    audio = np.zeros(320, dtype="float32")

    trimmed = trim_silence(audio, threshold=0.01, padding_samples=160)

    assert trimmed is audio


def test_trim_silence_preserves_multichannel_contract_as_mono_array():
    audio = np.array([0, 0, 0.2, 0, 0], dtype="float32")

    trimmed = trim_silence(audio, threshold=0.01, padding_samples=1)

    assert np.allclose(trimmed, [0, 0.2, 0])
