"""Offline tests: post-processor, clipboard round-trip, ASR on a sample wav.

Run:  .venv/Scripts/python.exe tests/test_pipeline.py
"""
import os
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS = []


def check(name, fn):
    try:
        detail = fn()
        RESULTS.append((name, "PASS", detail or ""))
    except AssertionError as exc:
        RESULTS.append((name, "FAIL", str(exc)))
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((name, "ERROR", f"{type(exc).__name__}: {exc}"))


def test_polish():
    from punctuation.post_processor import polish

    assert polish("  hello   world ") == "Hello world."
    assert polish("the quick brown fox") == "The quick brown fox."
    assert polish("already ended!") == "Already ended!"
    assert polish("space before , punctuation") == "Space before, punctuation."
    assert polish("") == ""
    return "5 assertions ok"


def test_clipboard():
    from injection.typer import copy_to_clipboard, get_clipboard_text

    marker = "dictate-test-12345"
    backup = get_clipboard_text()
    assert copy_to_clipboard(marker), "copy_to_clipboard returned False"
    got = get_clipboard_text()
    copy_to_clipboard(backup)
    assert got == marker, f"clipboard round-trip got {got!r}"
    return "set/get/restore ok"


def _download_sample() -> str:
    url = ("https://raw.githubusercontent.com/ggml-org/whisper.cpp/"
           "master/samples/jfk.wav")
    dest = os.path.join(tempfile.gettempdir(), "dictate_jfk.wav")
    if not os.path.exists(dest):
        urllib.request.urlretrieve(url, dest)
    return dest


def test_asr():
    from asr.faster_whisper_engine import FasterWhisperEngine

    wav = _download_sample()
    eng = FasterWhisperEngine("tiny.en", language="en")
    eng.load()
    res = eng.transcribe(wav)
    text = res["text"].lower()
    assert any(w in text for w in ("fellow", "americans", "ask not")), res["text"]
    return f"heard: {res['text'][:60]!r}"


if __name__ == "__main__":
    check("post_processor", test_polish)
    check("clipboard", test_clipboard)
    check("asr_tiny_en", test_asr)
    for name, status, detail in RESULTS:
        print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    failed = [r for r in RESULTS if r[1] != "PASS"]
    sys.exit(1 if failed else 0)
