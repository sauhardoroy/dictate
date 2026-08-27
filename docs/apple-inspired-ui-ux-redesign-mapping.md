# Dictate: Apple-Inspired UI/UX Redesign Mapping

## Purpose and scope

This document maps the current Dictate UI to the Apple Human Interface Guidelines (HIG) and the Liquid Glass material model, then turns the mapping into an implementation-ready redesign brief.

It covers the floating pill, onboarding, settings, transcript history, tray menu, theme system, and custom shader. It is based on the implementation as inspected on 2026-08-27, not on screenshots or an assumed design. The goal is an **Apple-inspired, platform-respectful Windows experience**, not a literal imitation of macOS. On Windows, retain familiar Windows behaviors and the system typeface; borrow Apple’s principles of clarity, deference, depth, direct manipulation, semantic color, and purposeful motion.

## The design thesis

Dictate should feel like a quiet, trustworthy voice utility that appears when needed, explains itself at a glance, and disappears without disrupting the person’s work.

The visual system has two intentionally different layers:

```text
Content layer — what the person reads, edits, searches, or configures
  • onboarding copy and setup rows
  • settings forms and preference groups
  • transcript history, transcript text, and search results
  • flat or standard-material surfaces; stable contrast

Functional layer — controls that navigate, invoke, or transiently float
  • floating dictation pill
  • active navigation treatment
  • primary action, contextual menu, confirmation sheet
  • Liquid Glass, used once per local region and only where it adds hierarchy
```

Apple describes Liquid Glass as a distinct functional layer above content and explicitly advises against using it in the content layer. It should be sparing, adaptive, and reserved for important controls and navigation ([Apple HIG: Materials](https://developer.apple.com/design/human-interface-guidelines/materials)). This distinction is the highest-impact change for Dictate.

## Apple principles translated for Dictate

| Apple principle | Meaning for Dictate | Observable rule |
|---|---|---|
| Clarity | Voice capture state, privacy, and the next action must never be ambiguous. | Every state combines an icon, a short text/tooltip/accessibility label, and color; color alone never carries meaning. |
| Deference | The writing app remains the star; Dictate must not compete with it. | Keep idle UI to one small pill. Make settings and history visually quiet. Do not decorate transcript content with glass. |
| Depth | Layering explains interaction rather than adding ornament. | The pill floats above the desktop; a menu or confirmation grows from the invoking control; content remains visually grounded. |
| Direct manipulation | A control responds immediately and proportionally. | The microphone meter follows actual input; pill drag follows pointer; recording changes are reversible and clear. |
| Consistency | Identical meanings look and behave alike across every surface. | One state vocabulary, one semantic token set, one icon family, and one confirmation pattern. |
| Platform respect | Familiar behavior is more valuable than cosmetic imitation. | Use Windows-native window/tray conventions and Segoe UI Variable. Do not require SF Pro or macOS-only interaction patterns. |
| Accessibility by adaptation | Visual effects must adapt to people and context. | Support reduced motion, reduced transparency, increased contrast, keyboard focus, scaling, and nonvisual state announcements. |

Apple’s materials guidance distinguishes Liquid Glass for controls/navigation from standard materials for content, while its motion guidance calls for animation that conveys status and responds to accessibility settings ([Materials](https://developer.apple.com/design/human-interface-guidelines/materials), [Motion](https://developer.apple.com/design/human-interface-guidelines/motion)).

## Current experience map

```text
First run
  Onboarding dialog → choose shortcut → optional transcript polish → start

Everyday capture
  Idle circular pill → recording expanded pill → transcribing → injected / error → idle
                           ↘ tray menu can start/stop or open settings/history

Review and control
  Tray or pill context menu → Settings dialog / Transcript History dialog
```

The architecture is already well suited to the redesign. The pill is a single state machine, a shared shader exists, and dialogs have reusable theme entry points. The work is primarily to tighten hierarchy, simplify the live-preview treatment, centralize tokens, and add adaptive states—not to replace the interaction model.

## Component-by-component mapping

### 1. Floating pill

Relevant implementation: [ui/pill.py](../ui/pill.py), [ui/theme.py](../ui/theme.py), and [ui/liquid_glass_shader.py](../ui/liquid_glass_shader.py).

| Current element | Existing behavior | Apple principle it already supports | Redesign direction | Priority |
|---|---|---|---|---|
| Idle 60 × 60 circular pill | Always on top, nonactivating, draggable, centered near the lower screen edge. | Deference and direct manipulation. It stays small and does not steal focus. | Retain it as Dictate’s signature control. Add an explicit accessible name such as “Dictate, ready. Activate to start dictation.” Preserve a generous invisible pointer target. | P0 |
| State machine | `idle`, `recording`, `preview`, `transcribing`, `injecting`, `loading`, and `error` have distinct colors, tooltips, and dimensions. | Clarity through state feedback. | Collapse `preview` into the listening state unless it exposes a distinct user choice. Use a stable state vocabulary: Ready, Listening, Processing, Inserted, Needs attention. | P0 |
| Recording expansion | The pill morphs to 310 × 102 and shows microphone, waveform, separator, and a word-card carousel. | Depth and continuity—the same object becomes the active control. | Keep the morph, but make one expanded capsule the only glass surface. Replace the three nested “glass cards” with a single content treatment: a one-line live transcript with an optional subtle fade at the edges. This prevents glass-on-glass and makes speech easier to scan. | P0 |
| Waveform | Five bars respond to microphone RMS; microphone glow and status dot animate. | Direct manipulation; status is physically connected to input. | Retain the meter but limit its visual range and make the state label available beside or below it on hover/focus. The waveform must describe activity, not pretend precision. | P1 |
| Processing / injected / error symbols | Dots pulse; checkmark confirms insertion; error icon shakes. | Motion as feedback. | Use a short, single-purpose response: processing dots; a brief check plus “Inserted”; error icon plus actionable message in a notification or tooltip. Do not rely on a shake alone. | P0 |
| Shape geometry | Idle uses a 30 px radius; expanded form uses a 20 px radius. | Rounded floating form suggests touchability. | Establish a concentric shape scale rather than independent radii. The expanded pill should retain a visibly related, generous radius (for example, 24 px at 102 px height) and all internal content should inset from that curve. Validate it at 100%, 125%, 150%, and 200% DPI. | P1 |
| Hover and drag | Hover brightens the mic; dragging moves the pill after an 8 px threshold. | Direct manipulation. | Preserve drag behavior. On hover, use a restrained elevation/highlight rather than continuous refractive agitation; a persistent “drag” affordance is unnecessary. | P1 |
| Screen capture protection | The widget is set to not activate and is excluded from display capture. | Deference and privacy intent. | Keep these protections. Clearly explain in privacy copy that glass samples only local pixels behind the pill and does not transmit screen content. Also provide a “static material” option for people who do not want screen sampling. | P1 |

#### Pill target composition

```text
Idle
  [ microphone symbol ]                  one glass capsule, one semantic accent

Listening
  [ mic ] [ live audio bars ] [ Stop ]   one glass capsule
  [ “Listening” / live transcript ]      plain vibrant text inside the same surface

Processing
  [ • • • ] Processing speech…           small glass capsule; no looping depth motion in reduced-motion mode

Completion
  [ check ] Inserted                      quick status, then return to idle
```

The pill qualifies for Liquid Glass because it is a transient, top-level functional control. The transcript itself is content and should be rendered as text inside that single surface—not as additional glazed cards. Apple notes that controls placed over glass should not become a second glass layer ([Apple HIG: Materials](https://developer.apple.com/design/human-interface-guidelines/materials)).

### 2. Onboarding

Relevant implementation: [ui/onboarding.py](../ui/onboarding.py).

| Current element | Apple mapping | Keep | Change |
|---|---|---|---|
| Three scenes: Welcome, Setup, Get Started | Progressive disclosure and clarity. | The concise, task-first sequence. | Treat this as a guided flow: prevent jumping ahead of required setup, or make skipped items explicit and recoverable. The current sidebar allows a direct jump to “Get Started.” |
| 900 × 590 frameless dialog | Focus and depth. | A contained first-run space is appropriate. | Use standard window controls or an explicit close/skip path. A frameless dialog must still provide discoverable dismissal and keyboard escape behavior. Avoid making a setup step feel like an unclosable branded splash screen. |
| Sidebar rail | Navigation lives in the functional layer. | The compact progress affordance. | Use it as a progress list rather than a standard app sidebar: numbered steps, current label, completed checkmark. The active row may receive the only local glass treatment; the rail itself stays a calm standard surface. |
| Animated hero stage | Emotional design and depth. | One meaningful illustration per step. | Keep it decorative and subordinate to the setup task. Reduce the perpetual timer-driven ripple to a static frame with a single entry transition; turn it off with Reduce Motion. |
| Liquid primary/back buttons | A primary action is functional. | The primary action’s clear hierarchy. | Use one prominent, filled or regular-glass primary button. Make Back a quiet text/secondary control on a standard surface. Do not make every button a shader-rendered object. |
| Shortcut capture | Direct manipulation. | Capturing a real key combination is excellent. | Add a conflict result, a “Use default” action, and a readable confirmation, for example “Ctrl + Shift + P will start Dictate in any app.” |
| “Speech recognition stays on your device” + AI polish enabled by default | Trust is part of clarity. | Explicit local-processing statement. | Do **not** enable cloud polishing by default. Use a separate, off-by-default consent step: state what leaves the device, provider, retention assumptions, and that transcription works without it. This is the most important onboarding trust correction. |

Recommended copy hierarchy:

1. Explain the immediate benefit: “Speak where you write.”
2. Explain the required permission/shortcut and confirm it works.
3. Present cloud polish as an optional enhancement with clear data disclosure.
4. End with a one-sentence practice instruction and a “Start Dictating” action.

### 3. Settings dialog

Relevant implementation: [ui/settings_dialog.py](../ui/settings_dialog.py).

| Current element | Apple mapping | Main issue | Redesign specification |
|---|---|---|---|
| Fixed 580 × 560 dark dialog | Clarity requires sufficient room for the current task. | Five long labels in one compact segmented bar are crowded and will become fragile under scaling or localization. | Make the preferences window resizable with a sensible minimum width. Use a compact side list or a toolbar/segmented control with no more than three broad categories. Suggested categories: General, Dictation, Audio, Advanced. Put Cloud polish inside Advanced with a privacy callout. |
| `FrostedCard` per group | Standard materials separate content groups. | “Frosted” terminology and semi-transparent cards imply glass throughout content. | Replace with content-layer group boxes: flat/standard-material fill, separator, 12–16 px inset, semantic heading, and aligned rows. No refractive effects in forms. |
| Form controls | Familiar controls improve usability. | Custom dark QSS, small 12 px text, fixed colors, and square custom checkbox styling do not adapt enough. | Use native-looking Qt controls where possible; minimum 32 px pointer row height and 44 logical px touch target when touch is supported. Use a rounded switch for binary settings, not a square checkbox when the setting applies immediately. Preserve a clear focus ring. |
| Save / Cancel footer | Reversibility. | The dialog mixes potentially immediate interactions (microphone test, input changes) with deferred “Save Changes” semantics. | Choose one model: (a) staged preferences with Apply/Cancel and unsaved-change prompt, or (b) immediate settings with a single Done button. Do not imply live application unless it is live. |
| Dictation setup | Progressive disclosure. | Options like Voice Commands, transcript preview, and silence timing are presented with similar weight. | Put the simple defaults first: trigger mode and shortcut. Move silence tuning and voice commands into “More options.” Reveal silence timing only when Auto-Stop is selected. |
| Speech model page | Clarity and technical honesty. | Dense, branded strings and readiness emoji make scanning difficult; hardware/model choices are advanced. | Use human labels first, technical details second. Example: “Fast (recommended)” with model name and download size in a secondary line. Reserve download/status symbols for an icon column, not prose. |
| Microphone tester | Direct manipulation. | The real audio meter is useful, but test state is represented mostly through color and small text. | Keep it. Show an explicit “Testing microphone” label, meter value/level description for assistive tech, device error recovery, and an obvious stop action. |
| AI Polish page | Trust and privacy. | A cloud capability is grouped like an ordinary visual preference and exposes low-level provider configuration by default. | Begin with a compact privacy explainer and off switch. Reveal provider, endpoint, API key, and model only after opt-in. Add “Learn what is sent” and a test action that uses non-sensitive sample text. |

#### Recommended settings information architecture

```text
General
  Launch at sign-in
  Restore clipboard
  Appearance: System / Light / Dark / Reduced transparency

Dictation
  Activation: Hold / Toggle
  Global shortcut
  Stop listening: Auto / Manual
  More options: silence time, live preview, voice commands

Audio
  Input device
  Test microphone [meter]

Advanced
  Speech engine: Recommended / Fast / Accurate
  Device acceleration
  Vocabulary
  Optional cloud transcript polish [off by default]
```

### 4. Transcript history

Relevant implementation: [ui/history_dialog.py](../ui/history_dialog.py).

| Current element | Apple mapping | Redesign direction |
|---|---|---|
| Header and concise subtitle | Clarity. | Retain, but use the same title style and dynamic appearance as settings. |
| Stats strip | Deference. | Demote to a compact optional summary (“24 dictations · 1,204 words”), or hide it when there is no history. A dashboard strip should not outrank the transcripts. |
| Search field | Familiarity and direct manipulation. | Keep search and clear affordance. Replace the emoji in placeholder text with an icon or plain “Search transcripts.” |
| Transcript cards | Content-layer grouping. | Use a native-feeling list with a flat standard-material row, timestamp/app metadata, transcript preview, and a selected state. Avoid multiple heavy borders and neon hover fills. Use disclosure/context actions rather than permanently showing three buttons in every row. |
| Copy feedback | Immediate feedback. | Keep the temporary “Copied” outcome and expose it through an accessibility announcement. Use a check symbol from one icon system instead of emoji. |
| “Paste to App” | Clear causality. | Rename to “Insert in [target app]” when the target is known; otherwise “Insert at previous cursor.” Confirm or explain if the target window is unavailable. The current hide-then-paste behavior needs a visible outcome if insertion fails. |
| Per-row delete / Clear All | Safe destructive actions. | Provide an Undo toast for one-row delete. Keep confirmation for Clear All, use a destructive button style, and make Cancel the default. |
| Export sheet | Platform convention. | Preserve the system save dialog. Default to a descriptive filename and a format that matches the chosen extension. |

Apple’s accessibility guidance recommends enough contrast in every appearance and a clear alternative when it is not present; it gives WCAG AA contrast ratios as guidance ([Apple HIG: Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)).

### 5. Tray icon and menu

Relevant implementation: [ui/tray.py](../ui/tray.py).

| Current element | Apple mapping | Redesign direction |
|---|---|---|
| Colored circular microphone tray icon | Semantic status. | Use a simple monochrome microphone glyph that respects the Windows tray context. Add a small status badge only when recording or attention is required. A different full icon color for every background activity can become noise. |
| Tooltip status | Clarity. | Keep the status wording. Use the same named states as the pill: Ready, Listening, Processing, Inserted, Needs attention. |
| Single-click starts/stops | Directness. | Retain only if documented and safe in the current trigger mode. Consider double-click to reveal/open controls if accidental tray clicks are common. |
| Emoji-prefixed menu actions | Consistency and scanability. | Remove emoji. Use a single vector/symbol family or text-only native menu entries. Let the operating system render the menu; do not force a dark custom dialog stylesheet onto it. |
| Action order | Hierarchy. | Use: Start/Stop Dictation; Copy Last Transcript (disabled when unavailable); Transcript History; separator; Settings; separator; Quit. Make the first action context-aware. |

The tray is system-managed functional chrome. It should be the least custom surface in the product, not another glass showcase.

### 6. Themes and design tokens

Relevant implementation: [ui/theme.py].

The current theme has a useful start: semantic token pairs, state styles, shared dialog stylesheet, and centralized animation constants. However, several dialogs and widgets bypass it with hard-coded dark hexadecimal colors. That causes inconsistency and makes accessibility adaptation expensive.

Replace palette names based on appearance (for example, `SYSTEM_GRAY3` or `SURFACE_ELEVATED`) with roles based on purpose:

| Token group | Suggested roles | Usage |
|---|---|---|
| Background | `background.base`, `background.grouped`, `background.elevated` | Window and content layer only. |
| Content | `content.primary`, `content.secondary`, `content.tertiary`, `content.separator` | Labels, metadata, dividers; never encode status only by tint. |
| Interaction | `action.accent`, `action.accentPressed`, `focus.ring`, `selection.fill` | Links, primary actions, selection, keyboard focus. |
| Status | `status.recording`, `status.success`, `status.warning`, `status.error` | Pair with icon and text. Recording red should be reserved for the active microphone state and destructive actions. |
| Materials | `material.content`, `material.chromeRegular`, `material.chromeClear`, `material.chromeFallback` | Content uses standard material; only chrome/pill/menu presentation may select Liquid Glass. |
| Geometry | `radius.control`, `radius.container`, `radius.pill`, `spacing.4/8/12/16/24/32` | Establish concentric rounding and predictable rhythm. |
| Motion | `motion.instant`, `motion.feedback`, `motion.transition`, `motion.reduced` | All effects take one motion policy rather than hard-coded per widget. |

Each token must supply light, dark, increased-contrast, and reduced-transparency values. Use OS appearance as the default, with an in-app override only if the app needs it. Apple recommends semantic/system-aware color because it adapts across appearance and accessibility contexts ([Apple HIG: Color](https://developer.apple.com/design/human-interface-guidelines/color)).

Typography should use the installed Windows system UI typeface—`Segoe UI Variable` is the correct choice here—rather than shipping or pretending to be SF Pro. Borrow Apple’s hierarchy, not its licensed font: a clearly larger page title, readable body text, subdued secondary metadata, no all-caps section labels unless they are truly short, and no reliance on 9–12 px text for core instructions.

### 7. Liquid Glass shader

Relevant implementation: [ui/liquid_glass_shader.py] and its use in [ui/pill.py](../ui/pill.py) and [ui/onboarding.py](../ui/onboarding.py).

| Current shader capability | Apple-inspired value | Guardrail |
|---|---|---|
| Captures the actual local backdrop | Makes the pill belong to the desktop rather than sit on an arbitrary fill. | Use only for the top-level pill or a single primary transient control. Do not use it behind reading content. |
| Refraction, edge lensing, Fresnel reflection, and specular highlights | Communicates material boundary and depth. | Reduce chromatic dispersion and broad glints until they are perceived as a crisp edge, not a visual effect. Never make text harder to read. |
| Screen-center light direction | Lets highlights respond to surrounding context. | Keep the effect slow and subtle; lighting should support legibility, not call attention to itself. |
| Dynamic ripple | Adds a liquid response. | Trigger it on interaction/state transition. Do not run visual ripples continuously in idle state. |
| 2× supersampling and frequent desktop captures | Can produce clean edges. | Set a performance budget. Reuse cached backdrop/geometry, update the backdrop only when position, size, state, or visual context changes, and cap active animation appropriately. Provide a static fallback. |
| Dark recording tint | Helps active state separation. | Let the semantic recording state be understandable without forcing an opaque dark look. Use regular, adaptive material first; apply modest tint only after contrast checks. |

Apple describes Liquid Glass as adaptive: it shifts tint, shadows, and dynamic range to retain legibility over changing content, and its lensing becomes more apparent as forms grow ([Meet Liquid Glass, WWDC25](https://developer.apple.com/videos/play/wwdc2025/219/)). Treat those as perceptual goals, not a request for maximum optical simulation.

#### Shader policy

```text
Regular glass (default)
  Pill, active onboarding progress item, primary transient control.
  Adaptive tint + modest blur/refraction + 1 px inner highlight + soft shadow.

Clear glass (exception)
  Only a short-lived control over rich imagery where extra transparency is valuable.
  Never use alongside regular glass in the same local region.

Standard material / flat fill
  Settings cards, history rows, transcript text, onboarding body, hero stage background.

Fallbacks
  Reduced transparency: opaque elevated surface, no backdrop sampling/refraction.
  Increased contrast: stronger fill/separator/focus ring, tested text contrast.
  Reduced motion: no ripple, no pulse loop, cross-fade state changes instead of overshoot or shake.
  Low-power/performance mode: cached static material; no continuous screen capture.
```

## Motion and state specification

Motion needs a reason: it should explain a state change, preserve object identity, or confirm an action. Apple cautions against excessive repetitive, scaling, depth, and blur animations when Reduce Motion is enabled ([Apple HIG: Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility), [Apple HIG: Motion](https://developer.apple.com/design/human-interface-guidelines/motion)).

| Transition | Recommended behavior | Reduced-motion behavior |
|---|---|---|
| Ready → Listening | Pill grows from its center; meter fades in. 180–220 ms, ease-out; no visible bounce. | Cross-fade and resize without overshoot. |
| Listening → Processing | Meter settles; transcript fades to “Processing speech…”. | Immediate text/symbol replacement or a 100 ms fade. |
| Processing → Inserted | Dots resolve to a checkmark; “Inserted” appears briefly. | Checkmark cross-fade only. |
| Failure | Static error symbol plus a concise reason and recovery action. | Same; never depend on shake. |
| Onboarding step | Content cross-fade/slide with one shared hero transition. | Cross-fade only; stop hero timer. |
| Settings section | Indicator moves once with the chosen section; page cross-fades. | Immediate section switch with focus moved to the heading. |

Use direct, gesture-linked movement for dragging, not ornamental movement at the screen edge. The pill is often in peripheral vision, so ongoing pulsing and high-frequency background updates deserve particular restraint.

## Accessibility and trust requirements

These are release requirements, not polish items.

- Expose the pill’s name, role, and state to Qt accessibility APIs. Tooltips are supportive, not a substitute for accessible state.
- Every state needs an icon/symbol, readable label, and semantic color. Avoid relying on the current red/purple/green state changes alone.
- Maintain at least 4.5:1 contrast for normal text and 3:1 for large text/bold text in light, dark, and increased-contrast themes, following the WCAG guidance Apple cites in its accessibility documentation.
- Make all custom controls keyboard reachable. `SegmentedNavBar`, onboarding navigation items, the pill menu, and custom toggle need focus, arrow-key behavior where appropriate, visible focus treatment, and accessible names/values.
- Scale font, row height, and dialog layout with system text/DPI. Do not let five settings tabs truncate or overlap at 200% scaling.
- Implement three visual policies: normal, reduced motion, and reduced transparency/increased contrast. Do not merely lower animation speed; replace nonessential movement with fades or static states.
- State the local screen-sampling behavior, local transcription behavior, and optional cloud-polish data flow in plain language. Cloud polish must require affirmative opt-in and remain easy to disable.
- Provide confirmation/Undo for destructive transcript actions, and confirm where “Insert” will send text when the target is uncertain.

## Prioritized implementation plan

### P0 — establish hierarchy and trust

1. Define the content-versus-functional layer policy in `ui/theme.py`; remove refractive/frosted card styling from settings and history content.
2. Recompose the recording pill as one glass capsule with plain transcript text, eliminating its nested transcript cards.
3. Standardize named states across pill, tray, tooltips, and accessibility announcements.
4. Make cloud polish opt-in, with disclosure in onboarding and settings.
5. Replace custom per-widget hard-coded colors with semantic tokens and add light/dark/high-contrast variants.
6. Add a keyboard/focus/accessibility pass to custom controls and destructive-action confirmation/Undo.

### P1 — refine structure and adaptation

1. Rebuild settings navigation around four resilient sections, progressive disclosure, and one clear save model.
2. Rework history into a calm native-like list with contextual actions and target-aware insertion.
3. Simplify the tray into OS-respectful monochrome chrome with text-first menu actions.
4. Add reduced-motion, reduced-transparency, and static-material fallbacks.
5. Replace onboarding’s free-jump sidebar with a clear progress model; add an explicit close/skip path.

### P2 — tune the signature material

1. Tune shader optics against varied desktop backgrounds: reduce color fringing, retain edge definition, and test type legibility.
2. Move ripples from continuous decoration to interaction feedback.
3. Add performance telemetry in development builds: backdrop captures/second, render time, and CPU use while idle/listening.
4. Test multi-monitor moves, high-DPI scaling, high contrast, and screen capture privacy behavior.

## Acceptance checklist

The redesign is ready for visual QA when all of the following are true:

- [ ] One can identify Ready, Listening, Processing, Inserted, and Needs attention without relying on color.
- [ ] No transcript, settings row, history row, or reading surface is a Liquid Glass pane.
- [ ] No local region has a glass control sitting on another glass control; nearby functional controls are merged or separated.
- [ ] The pill remains recognizably the same object as it grows and contracts, with no gratuitous bounce.
- [ ] Settings remain fully readable and navigable at 200% display scaling and with keyboard-only input.
- [ ] Light, dark, increased-contrast, reduced-transparency, and reduced-motion modes each have intentional outputs.
- [ ] The default onboarding path makes it unambiguous that transcription is local and cloud polish is optional.
- [ ] Tray menus are readable as native system actions with no emoji dependency.
- [ ] Delete, Clear All, and Insert flows have clear consequences and recovery where possible.
- [ ] Idle CPU/GPU work is near zero; the richer material activates only when Dictate’s control is visible and useful.

## Sources

- [Apple Human Interface Guidelines — Materials](https://developer.apple.com/design/human-interface-guidelines/materials)
- [Apple Human Interface Guidelines — Motion](https://developer.apple.com/design/human-interface-guidelines/motion)
- [Apple Human Interface Guidelines — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)
- [Apple Human Interface Guidelines — Color](https://developer.apple.com/design/human-interface-guidelines/color)
- [Apple WWDC25 — Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/)
- [Apple WWDC25 — Build an AppKit app with the new design](https://developer.apple.com/videos/play/wwdc2025/310/)

