# Dictate User Interface (UI) Architecture

The `ui/` directory houses the entire visual layer, interaction pipeline, and design system of Dictate. The application implements a unified, flat, matte **Google Material 3 Monochrome design system** across both the floating heads-up display (Pill, Preview Overlay, Tray) and all application dialogs (Settings, History, Onboarding).

---

## Table of Contents
1. [Design Principles & Core Directives](#design-principles--core-directives)
2. [Design Tokens & Theme Architecture](#design-tokens--theme-architecture)
3. [End-to-End User Journey & UI Flow](#end-to-end-user-journey--ui-flow)
4. [Component State Machine](#component-state-machine)
5. [File Utility & Architectural Breakdown](#file-utility--architectural-breakdown)
6. [Visual & Technical Engineering Standards](#visual--technical-engineering-standards)

---

## 1. Design Principles & Core Directives

Dictate is designed as an invisible, ambient productivity tool that feels completely native to modern desktop environments (Windows 11 / macOS Sequoia).

```
┌────────────────────────────────────────────────────────────────────────┐
│               UNIFIED MATERIAL 3 MONOCHROME ARCHITECTURE               │
├───────────────────────────────────┬────────────────────────────────────┤
│   FLOATING HUD LAYER (Ambient)    │   STRUCTURAL APP LAYER (Surfaces)  │
│   • Flat matte surface container  │   • Tonal Surface Elevation Ladder │
│   • 1px hairline border outline   │   • Clean hairlines & no blur      │
│   • Signal dot for recording only │   • Consistent Segoe UI typography │
│   • Zero Focus Stealing (Win32)   │   • Shape.LG / Shape.FULL radii    │
│   [pill.py, preview_overlay.py]   │   [settings, history, onboarding]  │
└───────────────────────────────────┴────────────────────────────────────┘
```

### Core Design Principles
1. **Monochrome First:** The palette is a refined tonal grayscale ladder (`surface_dim` to `surface_container_highest`). Visual hierarchy is communicated through tone, contrast, and typography weight rather than decorative colored accents.
2. **Matte, Not Glossy:** Every surface is a flat matte fill with a 1px hairline border. No drop shadows, no gradients, no screen-space shaders, and no blur/translucency stacking.
3. **One Reserved Signal Tone:** To ensure instant readability across a busy desktop, exactly one desaturated warm-neutral tone (`signal_recording`) is reserved for the live recording indicator dot, and one muted tone (`signal_error`) is reserved for error states. All other states (idle, transcribing, inserted, loading) are differentiated by **icon shape and motion**, not color.
4. **Zero Focus Stealing (`WS_EX_NOACTIVATE`):** Floating widgets (the Pill and Preview HUD) never steal keyboard or OS window focus from the active text editor, terminal, browser, or IDE.
5. **Single Typeface Scale:** Consistent typography powered by Segoe UI Variable / Inter (`material_theme.FONT_FAMILY`).

---

## 2. Design Tokens & Theme Architecture

The single source of truth for all colors, shapes, typography, and motion is [`material_theme.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/material_theme.py).

### 2.1 Geometry (`Shape`)
| Token | Value | Target UI Elements |
|---|---|---|
| `Shape.FULL` | `999px` | Buttons, status pills, key capture chip, floating HUD capsule |
| `Shape.LG` | `16px` | Content cards, transcript history cards, dialog group containers |
| `Shape.MD` | `12px` | Dashboard stat summary cards, sub-sections |
| `Shape.SM` | `8px` | Text inputs, dropdowns, small badges |
| `Shape.XL` | `24px` | Frameless dialog outer window borders |

### 2.2 Motion (`MOTION`)
- `MOTION["fast"]` ($120\,\text{ms}$): Micro-interactions, button hover/press feedback, dismissals.
- `MOTION["standard"]` ($220\,\text{ms}$): Symmetrical 2D pill size morphing, tab transitions.
- `MOTION["slow"]` ($320\,\text{ms}$): Dialog opacity fades.

---

## 3. End-to-End User Journey & UI Flow

```
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│  1. First Run   │  ──>  │ 2. Ambient Idle │  ──>  │ 3. Push-to-Talk  │
│  Onboarding     │       │ Capsule & Tray  │       │ (Pill Expands +  │
│  (onboarding.py)│       │ Indicator       │       │ Grayscale Meter) │
└─────────────────┘       └─────────────────┘       └──────────────────┘
                                                              │
                                                              ▼
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│ 6. Management   │  <──  │ 5. Text Paste   │  <──  │ 4. VAD Silence   │
│ (Settings &     │       │ & History Log   │       │ Auto-Stop        │
│ History Dialog) │       │ (Checkmark)     │       │ (Processing Dots)│
└─────────────────┘       └─────────────────┘       └──────────────────┘
```

### 1. First-Run Onboarding (`onboarding.py`)
- **Trigger:** First application launch (`onboarding_completed: false`).
- **Experience:** A 3-step navigation-rail wizard with smooth opacity entrance:
  - **Step 1 (Welcome):** Clear privacy guarantee emphasizing 100% offline, local speech processing.
  - **Step 2 (Setup):** Interactive global hotkey recorder (`KeyCaptureButton`) and automatic verification of bundled offline neural speech models.
  - **Step 3 (Get Started):** Optional Cloud AI Polish toggle (with clear data handling disclosures) and test dictation prompt.

### 2. Ambient Readiness & System Tray (`tray.py` + `pill.py`)
- **Experience:** Dictate operates silently in the background. 
- **Floating Pill:** A circular matte capsule ($60 \times 60\,\text{px}$) floats unobtrusively on-screen with an idle microphone glyph. It is smoothly draggable and remembers its coordinates across sessions.
- **System Tray:** A crisp monochrome microphone icon provides immediate right-click access to Settings, History, Quick Actions, and Quit.

### 3. Live Dictation & Streaming Preview (`pill.py` + `preview_overlay.py`)
- **Trigger:** Pressing the global hotkey (e.g., `Ctrl+Shift+P` in Push-to-Talk or Toggle mode).
- **Pill Morphing:** The capsule smoothly morphs into an expanded horizontal shape ($320 \times 74\,\text{px}$):
  - **Top Row:** Left recording dot in `signal_recording` + 5-bar grayscale audio level meter + right status dot.
  - **Bottom Row:** High-contrast streaming interim transcription with edge clipping.
- **Subtitle Preview (`preview_overlay.py`):** If enabled, a floating subtitle HUD tracks near the active cursor or pill, displaying a 4-word sliding window with the latest active word highlighted.

### 4. Acoustic Auto-Stop & Processing (`pill.py`)
- **Trigger:** Semantic VAD detects thought completion or silence threshold ($1.4\,\text{s}$).
- **Pill Morphing:** Shrinks to a compact processing capsule ($130 \times 52\,\text{px}$) with 3 breathing dots in `on_surface_muted` and `"Processing"`. Offline Parakeet/SenseVoice decodes the full acoustic audio while preserving background UI responsiveness.

### 5. Instant Text Injection & Visual Confirmation
- **Trigger:** Transcription completes.
- **Injection:** Direct paste (`Ctrl+V` / synthetic keystrokes) into the previously focused application window.
- **Pill Morphing:** Capsule displays a checkmark glyph with `"Inserted"`, then springs back to the circular idle capsule ($60 \times 60\,\text{px}$) after $900\,\text{ms}$.
- **History Record:** The utterance is automatically logged to `history.json`.

### 6. Audit, Preferences & Maintenance (`history_dialog.py` + `settings_dialog.py`)
- **History Explorer:** Rich card-based log of all past dictations with duration, word count, target app badges, search, and one-click re-injection.
- **Settings Dialog:** Material 3 tabbed interface (General, Dictation, Audio, Advanced) allowing live mic testing, hotword boosting configuration, hardware acceleration toggles, and model selection.

---

## 4. Component State Machine

```mermaid
stateDiagram-v2
    [*] --> Onboarding : First Run
    Onboarding --> Idle : Setup Complete
    [*] --> Idle : Normal Launch

    state "Pill: Idle Capsule (60x60)" as Idle
    state "Pill: Recording Capsule (320x74)" as Recording
    state "Pill: Processing Capsule (130x52)" as Processing
    state "Pill: Inserted Feedback (120x52)" as Inserted
    state "Pill: Error / Mic Blocked (60x60)" as ErrorState

    Idle --> Recording : Hotkey Pressed / PTT Down
    Recording --> Processing : Hotkey Released / VAD Auto-Stop
    Recording --> Idle : Cancel / No Speech Detected
    Processing --> Inserted : ASR Decoded & Injected
    Processing --> ErrorState : Engine / Mic Exception
    Inserted --> Idle : 900ms Delay Complete
    ErrorState --> Idle : 1800ms Auto-Dismiss

    state "Modal Surfaces" as Modals {
        SettingsDialog : Preferences (settings_dialog.py)
        HistoryDialog : History Explorer (history_dialog.py)
    }

    Idle --> SettingsDialog : Tray Menu / Pill Context Menu
    Idle --> HistoryDialog : Tray Menu / Hotkey
```

---

## 5. File Utility & Architectural Breakdown

| File | Primary Role & Use Case | Design Language & Key Techniques |
|---|---|---|
| **[`pill.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/pill.py)** | Floating shape-shifting status pill and interactive dictation indicator. | **Flat Matte Material 3:** `surface_container_high` fill, `outline` border, 2D symmetrical morphing (`MOTION["standard"]`, `OutCubic`), grayscale audio meter, `signal_recording` indicator dot. |
| **[`preview_overlay.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/preview_overlay.py)** | Floating real-time subtitle HUD for streaming interim words. | **Monochrome Subtitle HUD:** `surface_container_low` fill, 4-word sliding window with bold `on_surface` active word emphasis, and `signal_recording` mic dot. |
| **[`settings_dialog.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/settings_dialog.py)** | Preferences window for engine, audio, hotkeys, and AI polish. | **Material 3 Monochrome:** 4 categorized tabs (General, Dictation, Audio, Advanced), live audio level meter, key capture button, and model dropdowns. |
| **[`history_dialog.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/history_dialog.py)** | Full-text searchable transcript archive and export tool. | **M3 Card Explorer:** Real-time search filter, aggregate stat counters, `make_card` items (`Shape.LG`), one-click copy feedback ("Copied"), re-injection, and Markdown/TXT export. |
| **[`onboarding.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/onboarding.py)** | First-run interactive onboarding wizard. | **M3 Navigation Rail:** 3-step progressive disclosure, animated opacity transitions, hardware model readiness checks, and global shortcut setup. |
| **[`tray.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/tray.py)** | System tray icon, status indicator, and global context menu. | **System Integration:** Dynamic QPainter icon generation with status badge dots (`signal_recording` for listening, `signal_error` for error). |
| **[`material_theme.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/material_theme.py)** | Material 3 tonal surface tokens, shape scales, and dynamic QSS compiler. | **M3 Token Engine:** Single source of truth for dark/light surface elevation ladder (`surface_dim` to `surface_container_highest`), signal tokens, and typography scales. |
| **[`theme.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/theme.py)** | Compatibility bridge re-exporting HUD states and tokens. | **Token Bridge:** Re-exports `HUD_STATES`, `Shape`, `MOTION`, and token accessors from `material_theme.py`. |
| **[`widgets.py`](file:///c:/Dodo%20Drive/Hermes%20Agent/Projects/dictate/ui/widgets.py)** | Reusable custom UI controls. | **M3 Interactive Components:** `ToggleSwitch` (animated thumb travel), `KeyCaptureButton` (raw key listener), `LevelMeter` (smooth audio RMS bar), `SegmentedTabBar`, and `StatusPill`. |

---

## 6. Visual & Technical Engineering Standards

### 1. Window Flags & OS Integration
All floating HUD windows (`pill.py`, `preview_overlay.py`) enforce:
```python
self.setWindowFlags(
    Qt.WindowType.FramelessWindowHint |
    Qt.WindowType.WindowStaysOnTopHint |
    Qt.WindowType.Tool |
    Qt.WindowType.WindowDoesNotAcceptFocus
)
self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
```
On Windows, `WS_EX_NOACTIVATE` ($0x08000000$) is applied via `SetWindowLong` to prevent focus stealing from the user's active application.

### 2. Zero Hex Colors Outside `material_theme.py`
All UI components strictly obtain colors from `Tokens` (`get_tokens()`). No raw hex string literals exist anywhere in component files.
