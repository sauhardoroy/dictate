# Dictate Privacy & Data Handling Policy

**Last Updated:** August 2026  
**Architecture:** Local-First, Offline-Default Speech Recognition

---

## 1. Core Privacy Architecture

Dictate is architected from the ground up as a **100% offline-default** voice typing application. We believe voice dictation tools should never snoop on your screen, read your clipboard, or transmit your workflow data without explicit consent.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      LOCAL DEVICE BOUNDARY (Strict)                    │
│                                                                        │
│   Microphone Audio  ──>  Local VAD  ──>  Offline ASR (Parakeet/Zip)    │
│                                                   │                    │
│   Active HWND (PID) ──>  Local Category Matching  │                    │
│   (Zero Cloud Push)      (document/code/chat)    │                    │
│                                                   ▼                    │
│                                          Direct Text Paste             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                         [Optional Opt-In Toggle]
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      CLOUD AI POLISH (Optional)                        │
│   • Only raw dictated words (<raw_transcript>...</raw_transcript>)     │
│   • ZERO window titles, ZERO process names, ZERO screenshot/clipboard  │
│   • HTTPS to user's configured provider (Groq / OpenRouter / Ollama)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hard Data Protection Boundaries

The following hard boundaries are enforced at the code, architecture, and test level:

### 2.1 No Screen Capture or Optical OCR
- Dictate **never** takes screenshots, captures display pixels, or runs optical text recognition (OCR) on your screen.
- Screen-space grabs and backdrop shaders have been completely eliminated. Floating HUD overlays declare `WDA_EXCLUDEFROMCAPTURE` on Windows.

### 2.2 No Clipboard Snooping
- Dictate **never** inspects, reads, or logs existing clipboard text or history.
- When injecting text via synthetic keystrokes or `Ctrl+V`, Dictate only puts your newly dictated transcript onto the clipboard to paste it, and does not harvest existing contents.

### 2.3 No Textbox Context Reading
- Dictate **never** reads surrounding text before or after your cursor in third-party text fields.

### 2.4 Local-Only Context & Window Matching
- Active window queries (via OS `GetForegroundWindow` / process ID lookup) are used **strictly on-device** to determine coarse application categories (e.g. `document_editor`, `code_agent`, `messaging_app`).
- **Zero Cloud Transmission:** Window titles and process names are **never** attached to any network request or sent to any cloud LLM endpoint.
- **Log Masking:** Window titles are masked by default in persistent logs and only visible when explicit local verbose debugging is active.

---

## 3. Cloud AI Polish (Optional & User-Controlled)

Dictate includes an optional Cloud AI Polish toggle (`ai_polish`, default: **disabled / False**):
- When **disabled (default)**, all punctuation, formatting, and capitalization are handled 100% locally on your machine with zero network traffic.
- When **enabled**, only the raw transcribed text is sent over HTTPS to your chosen LLM endpoint inside isolated XML tags (`<raw_transcript>...</raw_transcript>`).
- **No telemetry, no device IDs, no window titles, and no surrounding context** are ever transmitted.

---

## 4. Master Context Awareness Toggle

You have complete control over application detection:
- **Setting:** `context_awareness_enabled` (default: `true`).
- **Behavior when disabled:** All context queries immediately return `unknown`, and all features fall back to their safest universal defaults without querying OS window handles.

---

## 5. Summary Matrix

| Data Category | Processed Locally? | Sent to Cloud? | Persisted to Disk? |
|---|---|---|---|
| **Voice Audio Stream** | Yes (in RAM ring buffer) | **Never** | **Never** (discarded after transcription) |
| **Window Title & Process** | Yes (local category check) | **Never** | Masked in standard logs |
| **Dictated Transcripts** | Yes (local post-processing) | Only if AI Polish is enabled | Yes (encrypted/local `history.json` if enabled) |
| **Clipboard History** | **Never** | **Never** | **Never** |
| **Screenshots / Display** | **Never** | **Never** | **Never** |
| **Surrounding Textbox Content** | **Never** | **Never** | **Never** |
