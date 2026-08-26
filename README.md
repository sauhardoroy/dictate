# Dictate

A standalone, offline voice typing widget for Windows. Press a hotkey, speak into any application, and your words appear — no typing required.

## Quick Start

```bat
cd dictate
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

For development diagnostics: `python main.py --debug --console`. Logs rotate at
`dictate.log` next to the source tree, or `%APPDATA%\Dictate\dictate.log` in the packaged app.

Or just double-click **run.bat** after the first install.

## How It Works

1. A small floating **pill** appears on your screen (always-on-top, doesn't steal focus)
2. A **system tray icon** appears for quick access
3. **Press F9** (default — configurable) to start recording
   - **Push-to-talk mode:** hold the key, speak, release to stop
   - **Toggle mode:** press to start, press again to stop
4. Your speech is transcribed locally and **pasted into the text field you were using when dictation began**
5. Dictate restores your previous clipboard after pasting (configurable)

## Tech Stack

| Component | Technology |
|---|---|
| UI | PyQt6 (frameless, always-on-top pill widget) |
| Global Hotkey | `keyboard` library |
| Audio Capture | `sounddevice` (WASAPI, 16 kHz mono) |
| ASR Engine | **faster-whisper** (Whisper via CTranslate2, INT8 CPU inference) |
| Text Injection | Clipboard + Ctrl+V (works in any app) |
| Punctuation | Whisper outputs punctuation natively; rule-based polish layer |

## Supported Models

Run **Settings → Speech model** to change. Bigger = more accurate but slower. The
`distil-*` variants are drop-in Distil-Whisper models that trade a little
accuracy for a large speed win — try `distil-small.en` first if latency
matters more than accuracy.

| Model | Size | RAM | Speed (CPU) | Accuracy |
|---|---|---|---|---|
| tiny.en | 39 MB | ~300 MB | Very fast | Basic |
| base.en | 74 MB | ~400 MB | Fast | Fair |
| small.en | 244 MB | ~1 GB | Good | Good |
| distil-small.en | smaller than small.en | lower than small.en | Faster than small.en | Close to small.en |
| medium.en | 769 MB | ~2.5 GB | Moderate | Very good |
| distil-medium.en | smaller than medium.en | lower than medium.en | Faster than medium.en | Close to medium.en |
| distil-large-v3 | smaller than large-v3 | lower than large-v3 | Faster than large-v3 | Close to large-v3 |
| large-v3-turbo | 809 MB | ~3 GB | Moderate | Best (7.7% WER) |

**Default:** `small.en` — good balance of speed and accuracy. Exact
download size/RAM for `distil-*` models vary by release; check the model
card on Hugging Face (`Systran/faster-distil-whisper-*`) before committing
to one for a memory-constrained machine.

### Processing device

**Settings → Processing device** defaults to **Automatic**, which asks
CTranslate2 to use an NVIDIA GPU (CUDA) when one is available and
transparently fall back to CPU otherwise — no manual configuration needed.
Compute type similarly defaults to `auto`, which lets CTranslate2 pick the
fastest numeric precision the detected device actually supports, and CPU
thread count defaults to `0` (auto-sized to the host CPU). Power users can
override `compute_type`/`cpu_threads` directly in `settings.json`.

### Custom vocabulary

**Settings → Custom vocabulary hint** biases transcription toward names,
acronyms, or jargon you dictate often (passed through as Whisper's
`initial_prompt`). It takes effect immediately without reloading the model.

## Controls

| Action | Default |
|---|---|
| Start/stop dictation | F9 |
| Cancel recording | Esc |
| Move the pill | Click and drag |
| Settings | Right-click pill or tray icon |
| Quit | Right-click → Quit |

## Settings

- **Trigger mode:** Push-to-talk / Toggle
- **Trigger key:** Any key (click "capture" then press)
- **Whisper model:** tiny.en → large-v3-turbo, including faster `distil-*` variants
- **Processing device:** Automatic (GPU if available) / CPU only / NVIDIA GPU
- **Custom vocabulary hint:** Bias transcription toward names/jargon you use often
- **Microphone:** Choose input device
- **Silence timeout before auto-stop:** 0.3–3.0s (default 0.8s) — shorter feels snappier in Toggle mode
- **Restore clipboard:** On/off
- **Autostart:** Launch with Windows

## Project Structure

```
dictate/
├── main.py                  # Entry point
├── app.py                   # Orchestrator (recording lifecycle)
├── config/settings.py      # JSON-backed user settings
├── ui/
│   ├── pill.py              # Floating always-on-top pill widget
│   ├── tray.py              # System tray icon
│   └── settings_dialog.py  # Settings panel
├── audio/capture.py         # Microphone capture via sounddevice
├── asr/
│   ├── base.py              # Abstract ASR interface
│   ├── faster_whisper_engine.py   # Whisper via faster-whisper
│   └── nemotron_engine.py   # Nemotron (Phase 2, experimental)
├── injection/typer.py       # Clipboard + Ctrl+V text injection
├── hotkey/manager.py        # Global hotkey via Win32 polling
├── punctuation/post_processor.py   # Capitalize, spacing, terminal punctuation
├── tests/test_pipeline.py   # Offline tests
├── requirements.txt
├── run.bat                  # Silent launcher (no console window)
└── README.md
```

## Testing

```bat
.venv\Scripts\python.exe -m pytest
```

The default suite is fast and does not require a microphone, model download, or network connection. It covers settings migration, focus-safe injection, silence trimming, model-path resolution, logging, and transcript cleanup.

The older end-to-end diagnostic remains available when you explicitly want a real clipboard and ASR check:

```bat
.venv\Scripts\python.exe tests\test_pipeline.py
```

## Roadmap

- [x] Phase 1: Core pipeline (Whisper + pill widget + hotkey + injection)
- [ ] Phase 2: Nemotron-3.5-ASR-Streaming integration (via parakeet.cpp)
- [ ] Phase 3: Live transcript preview, custom vocabulary, multi-language

## Requirements

- Windows 10/11
- Python 3.10+ (tested on 3.14)
- Microphone
- ~1-3 GB RAM (depending on model)
- No GPU required (CPU inference)

## License

MIT
