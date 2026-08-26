# 💧 Dictate — Chrome Extension (Manifest V3)

> **Shape-Shifting Apple Liquid Glass Voice Typing in Any Browser Tab**

The Dictate Chrome Extension brings the floating **Apple Liquid Glass Pill**, browser-native **Web Speech recognition**, **Voice Punctuation Commands**, and **NVIDIA AI Grammar Polish** into any web app (Google Docs, Notion, ChatGPT, Gmail, Twitter/X, Slack, GitHub, etc.).

---

## 🚀 Quick Install Instructions (Load Unpacked)

1. Open Google Chrome (or any Chromium browser like Brave / Edge).
2. In the URL bar, go to: `chrome://extensions`
3. Enable **Developer mode** (toggle in the top-right corner).
4. Click the **Load unpacked** button (top-left).
5. Select this folder:
   ```
   C:\Dodo Drive\Hermes Agent\Projects\dictate\chrome_extension
   ```
6. **Done!** Dictate is now active on all web pages.

---

## 🎙️ How to Use

- **Global Shortcut**: Press **`Ctrl+Shift+P`** (or **`Cmd+Shift+P`** on macOS) anywhere in the browser to start/stop dictation.
- **Click the Floating Pill**: Click the bottom-right liquid glass pill to toggle recording.
- **Drag Anywhere**: Click and drag the pill to place it wherever you like on the webpage. Its position is automatically remembered across page reloads.
- **Automatic Text Insertion**: Dictated and polished text is injected directly into your active input box, textarea, or contenteditable editor.

---

## ⚡ NVIDIA AI Cloud Polish Setup

1. Click the **Dictate** icon in your Chrome extensions toolbar.
2. In the popup under **⚡ NVIDIA AI Cloud Polish**:
   - Toggle **Enable NVIDIA AI Polish** ON.
   - Enter your free API key (`nvapi-...`) from [build.nvidia.com](https://build.nvidia.com/).
   - Select your preferred model (e.g. `Nemotron 70B` or `Llama 3.3 70B`).
   - Click **Save Settings**.
3. Now all spoken speech will be cleaned of filler words (*um, uh, like*) and perfectly punctuated before insertion!

---

## 🗣️ Supported Voice Commands

| Voice Command | Result |
|---|---|
| *"new line"* or *"newline"* | Inserts `\n` |
| *"new paragraph"* | Inserts `\n\n` |
| *"period"* or *"full stop"* | Inserts `.` |
| *"comma"* | Inserts `,` |
| *"question mark"* | Inserts `?` |
| *"exclamation mark"* | Inserts `!` |
| *"colon"* / *"semicolon"* | Inserts `:` / `;` |
| *"open quote"* / *"close quote"* | Inserts `"` |
| *"dash"* / *"hyphen"* | Inserts `-` |
| *"ellipsis"* / *"dot dot dot"* | Inserts `...` |

---

## 📁 Architecture Overview

- **`manifest.json`**: Chrome Extension Manifest V3 configuration.
- **`background.js`**: Background service worker handling shortcuts and NVIDIA AI API calls.
- **`content/pill_overlay.js`**: Shadow-DOM isolated shape-shifting liquid glass pill.
- **`content/liquid_glass_shader.js`**: Canvas liquid optical physics renderer (Snell refraction, dynamic lighting).
- **`content/content.js`**: Web Speech API controller & active element text injector.
- **`services/voice_commands.js`**: Real-time punctuation and command parser.
- **`popup/`**: Dark glassmorphic settings, NVIDIA API configuration, and transcript history.
