# Dictate — User Guide & Setup Manual

Welcome to **Dictate**! Dictate is a fast, lightweight, and private offline voice-typing widget for Windows and macOS. It allows you to speak naturally into any application, instantly converting your voice to text right at your cursor position with no cloud requirement.

---

## Table of Contents
1. [Installation & First Run](#installation--first-run)
   - [Windows Setup](#windows-setup)
   - [macOS Setup](#macos-setup)
2. [How to Dictate](#how-to-dictate)
   - [Trigger Modes (Push-to-Talk vs Toggle)](#trigger-modes)
   - [Default Hotkeys](#default-hotkeys)
   - [Floating Pill Widget & Visual Feedback](#floating-pill-widget--visual-feedback)
3. [Features & Capabilities](#features--capabilities)
   - [Universal Text Injection](#universal-text-injection)
   - [Offline Speech Models](#offline-speech-models)
   - [Custom Vocabulary & Jargon Bias](#custom-vocabulary--jargon-bias)
   - [AI Post-Processing / Polish (Optional)](#ai-post-processing--polish-optional)
   - [Voice Commands](#voice-commands)
   - [Transcription History](#transcription-history)
4. [Customization & Settings](#customization--settings)
5. [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## 1. Installation & First Run

### Windows Setup
1. **Download & Extract:** Download the `Dictate-Windows-x64.zip` distribution file and extract it to a folder of your choice (e.g., `C:\Program Files\Dictate` or `Documents\Dictate`).
2. **Launch:** Double-click **`Dictate.exe`**.
3. **Tray & Pill:** A subtle floating pill widget will appear at the top of your screen, and a Dictate icon will appear in your Windows System Tray (near the clock).
4. **Auto-Start (Optional):** Right-click the tray icon → **Settings** → toggle **Launch on Startup** if you want Dictate ready every time your PC boots.

### macOS Setup
1. **Download & Mount DMG:** Open `Dictate-macOS.dmg`.
2. **Install:** Drag `Dictate.app` into your **Applications** folder.
3. **Grant Essential Permissions (Required by macOS Security):**
   - **Microphone Access:** Go to *System Settings → Privacy & Security → Microphone* and ensure **Dictate** is toggled **ON**.
   - **Accessibility Access:** Go to *System Settings → Privacy & Security → Accessibility* and toggle **Dictate** **ON**. (This is required so Dictate can detect the global hotkey and paste text into your active app).
4. **Unsigned App First Run Note:**
   If macOS displays "Dictate cannot be opened because Apple cannot check it for malicious software", simply:
   - Right-click (or Control-click) `Dictate.app` in Finder and select **Open**, then click **Open** in the dialog.
   - Or open Terminal and run: `xattr -cr /Applications/Dictate.app`

---

## 2. How to Dictate

### Trigger Modes

Dictate supports two intuitive operating modes:

- **Push-to-Talk (Recommended & Default):**
  - **Press and hold** the hotkey (`Ctrl + Shift + P` or your custom shortcut).
  - Speak into your microphone.
  - **Release the key** when you finish speaking.
  - Dictate automatically stops recording, transcribes your voice, and pastes the text directly where your cursor was typing.

- **Toggle Mode:**
  - **Press the hotkey once** to start listening.
  - Speak freely.
  - **Press the hotkey again** to stop and transcribe.
  - *Tip:* Auto-stop on silence will also finish recording if you pause for more than ~1.4 seconds.

- **Cancel Recording:**
  - Press `Esc` at any time while recording to immediately discard without pasting anything.

---

## 3. Visual & Audio Feedback

### Floating Pill Widget
The floating pill widget displays live status states:
- **Idle / Ready (Blue/Soft Glow):** Ready to listen.
- **Recording (Pulsing Red Aura & Waveform):** Capturing your voice in real time.
- **Processing (Spinning Amber/Accent Accent):** Transcribing audio / applying AI polish.
- **Success (Green Glow):** Text has been injected into your focused app.

*Tip:* You can click and drag the floating pill anywhere on your screen. Dictate remembers your preferred placement across restarts.

---

## 4. Features & Capabilities

### Universal Text Injection
Dictate operates system-wide. Whether you are typing in:
- Web browsers (Google Chrome, Edge, Safari, Firefox)
- Code editors (VS Code, Cursor, JetBrains IDEs)
- Communication tools (Slack, Discord, Teams, WhatsApp)
- Documents & Emails (Microsoft Word, Notion, Obsidian, Outlook, Apple Notes)

When you trigger the hotkey, Dictate remembers which text field was active and returns focus before pasting. Even if no text field is focused, the transcript is placed into your system clipboard so you can manually paste with `Ctrl+V` (Windows) / `Cmd+V` (macOS).

### Offline Speech Models
Dictate runs local neural ASR models completely offline:
- **Parakeet TDT 0.6B:** Ultra-fast, near-instant streaming transcription with high accuracy and low CPU/RAM footprint.
- **Whisper Models (via Faster-Whisper):** Choose between `tiny.en`, `base.en`, `small.en`, `medium.en`, and `large-v3-turbo` depending on your hardware.

### Custom Vocabulary & Jargon Bias (`hotwords.txt`)
If you frequently dictate unusual proper names, medical terms, programming keywords, company jargon, or acronyms:
- Open **Settings → Custom Vocabulary**.
- Add your terms or edit `hotwords.txt`.
- The engine will boost those words during transcription without needing retraining.

### Optional AI Polish (Cloud LLM)
If you want to automatically clean up filler words ("um", "ah", "like"), fix tricky punctuation, or format transcriptions into clean prose:
- Go to **Settings → AI Polish**.
- Toggle **Enable AI Polish**.
- Select your provider (e.g. OpenRouter, NVIDIA NIM, OpenAI, or custom endpoint) and enter your API key.

### Voice Commands
When **Voice Commands** are enabled in Settings, saying phrases like:
- `"Undo"` → triggers system Undo (`Ctrl+Z` / `Cmd+Z`)
- `"Redo"` → triggers system Redo (`Ctrl+Y` / `Cmd+Shift+Z`)
- `"Select All"` → highlights all text
- `"New Line"` / `"Enter"` → inserts a line break

### Transcription History
Accidentally overwrite text? Right-click the pill or tray icon and choose **History** to view and search your last 100 dictation transcripts with one-click copy.

---

## 5. Customization & Settings Summary

Right-click the pill widget or system tray icon and select **Settings**:
- **Trigger Key & Mode:** Rebind the shortcut to any single key (e.g., `F9`, `Pause`, `ScrollLock`) or multi-key combo (e.g., `Ctrl+Alt+Space`).
- **Input Device:** Choose which microphone Dictate listens to.
- **Processing Device:** Automatic (NVIDIA GPU / Metal / CPU).
- **Silence Threshold:** Tune how long to wait after silence before auto-stopping in toggle mode.
- **Show Interim Preview:** Show real-time partial transcript preview right on the pill.

---

## 6. Troubleshooting & FAQs

- **Q: Nothing pastes into my application.**
  - *Windows:* Ensure Dictate is running with standard user permissions (or run as administrator if dictating into elevated administrative windows).
  - *macOS:* Check *System Settings → Privacy & Security → Accessibility* and confirm Dictate has permission to inject keystrokes.
- **Q: Audio is not detected or transcript is empty.**
  - *Check Microphone:* Open Dictate Settings and explicitly select your active microphone from the dropdown instead of default.
  - *Check Permissions:* On macOS, ensure Microphone access is granted in System Settings.
- **Q: How do I change the hotkey?**
  - Open Settings, click on the **Trigger Key** capture field, press your desired key combination, and click Save.
