# Liquid Glass — Full Reference

Compiled from Apple's Human Interface Guidelines (Materials page), the
WWDC25 session "Meet Liquid Glass," Apple's "Adopting Liquid Glass"
technology overview, and practitioner analyses published June 2025–mid
2026. Where Apple's own wording is especially precise, it's quoted below;
otherwise this is a synthesis. Applies to iOS 26, iPadOS 26, macOS
Tahoe 26, watchOS 26, tvOS 26 and later.

## Contents
1. What Liquid Glass is
2. The layer model (content vs. functional)
3. Anatomy of the material (sub-layers)
4. Variants: Regular vs. Clear
5. Concentricity and shape
6. Per-component guidance
7. Accessibility & adaptive behavior
8. Performance budgets
9. Common misuse patterns
10. Implementation notes (SwiftUI / web approximation)
11. Sources

---

## 1. What Liquid Glass is

Apple describes it as a "digital meta-material" that dynamically bends
and shapes light — a translucent material that reflects and refracts its
surroundings while dynamically transforming to bring focus to content.
It's heavily inspired by visionOS and is Apple's biggest visual shift
since iOS 7 (2013). It spans every major platform for the first time as
one unified cross-platform language, applied to controls, navigation,
the Dock, lock screen, Control Center, CarPlay, and system apps (Camera,
Photos, Safari, FaceTime, Music, News, Podcasts).

Apple's three long-standing HIG principles still underpin it:
**Clarity, Deference, Depth.** Liquid Glass is the mechanism for Depth
and Deference in this generation — controls float above and give way to
content, rather than competing with it.

## 2. The layer model — the core rule

Apple's HIG defines exactly two layers in every iOS 26+ interface:

- **Content layer**: the document, list, photo, video, or media a person
  is consuming. Use standard materials here (`.regularMaterial`,
  `.thinMaterial`, etc.) or flat fills — not Liquid Glass.
- **Functional layer**: controls, navigation, tab bars, sidebars,
  toolbars, transient overlays (sheets, popovers, alerts) — floats above
  content. Use Liquid Glass here.

Apple's own instruction (HIG, Materials): *"Don't use Liquid Glass in the
content layer. Liquid Glass works best when it provides a clear
distinction between interactive elements and content, and including it
in the content layer can result in unnecessary complexity and a confused
visual hierarchy."* From the WWDC25 session: *"Liquid Glass is best
reserved for the navigation layer. Avoid putting glass in the content
layer, and avoid putting [glass] within or on top of other glass
elements, to maintain hierarchy and prevent clutter."*

Practically: tab bars and sidebars are the flagship functional-layer
elements — they float above content and let it scroll/peek through
beneath them, which is where Liquid Glass's translucency actually earns
its keep (content is legible in the gaps, but the control itself stays
legible too via refraction and edge highlighting rather than heavy
blur/darkening the way older materials worked).

## 3. Anatomy of the material (sub-layers within Liquid Glass itself)

Liquid Glass is itself built from several layers acting as modifiers on
one material system:

- **Highlights layer** — responds to environmental lighting and device
  motion (specular highlights that shift as you tilt/scroll).
- **Material/blur layer** — the visual engine: backdrop blur,
  translucency, tint, glow; can introduce distortion/fluid-like
  deformation reacting to motion.
- **Content layer (within the glass element itself)** — a layer dedicated
  to the text/icon sitting on the glass control; carries its own text
  effects/vibrancy, separate from the app's underlying content layer
  described in §2. (Confusingly named the same as §2's "content layer"
  in some breakdowns — context disambiguates: this is the label/icon
  *inside* a glass control, not the app's scrollable content.)
- **Shadow layer** — handles the control's cast shadow (opacity, size).

Together these produce Apple's named behaviors: **materialization**
(elements appear by modulating light bending, not simple fade/scale),
**fluidity** (gel-like flexibility, instant touch responsiveness),
**morphing** (dynamic transformation between control states, e.g. a
button expanding into a menu), **adaptivity** (multi-layer composition
that adjusts to content, color scheme, and size).

## 4. Variants: Regular vs. Clear

Two variants exist. **They must never be mixed on the same screen/region.**

- **Regular** — the default and most versatile. Full adaptive behavior;
  Apple tunes it to stay legible in any context (bright sunlight, busy
  background, dark mode). Use this unless you have a specific reason for
  Clear.
- **Clear** — more transparent, lets underlying detail show through with
  much less filtering. Use **only** when all three hold:
  1. The element sits over media-rich content (photo/video), and
  2. Adding a dimming layer for legibility won't hurt that content, and
  3. You deliberately want maximum see-through (e.g. a minimal playback
     control over a full-bleed photo/video).
  Clear generally needs an extra dimming layer to keep controls legible,
  which Regular doesn't need.

## 5. Concentricity and shape

Controls, toolbars, and navigation elements are now drawn with
**context-aware, concentric rounded corners** that match the curvature of
the physical device and the app window — not arbitrary fixed radii. This
"concentric design" principle (explicit in the iOS 26 HIG) means:
interface shapes nest visually inside the hardware's corners the way
concentric circles share a center. When you set a corner radius on a
container, pair/derive it from the corner radius of whatever it's nested
inside, rather than picking a flat number in isolation.

Organizational components (lists, tables, forms) also got larger row
height/padding and increased section corner radius in this generation, to
match the softer, more rounded system-wide language.

## 6. Per-component guidance

- **Tab bars (iOS)**: top-level navigation between major app sections
  only — not for one-off actions. Rule of thumb: if a destination
  doesn't have its own "world" of screens you'd want to return to in the
  same state tomorrow, it's an action, not a tab (put it elsewhere, not
  in the tab bar). Tab bars float in the Liquid Glass functional layer;
  content scrolls beneath/through them. New APIs (SwiftUI/UIKit) support
  a `search` role tab, minimize-on-scroll behavior, and a persistent
  "bottom accessory" region for global (not per-screen) controls.
- **Sidebars (iPadOS, macOS)**: same functional-layer role as tab bars,
  for larger-screen navigation.
- **Toolbars**: `ToolbarItemPlacement` now affects both placement and
  rendering — e.g. `.confirmationAction` placement applies a
  "glassProminent" button style automatically. Don't hand-roll glass
  styling that fights these system placements.
- **Sheets, popovers, alerts, the Dock, Control Center**: all functional-
  layer, all candidates for Liquid Glass, all subject to the
  no-stacking-glass rule.
- **Content surfaces (lists, cards, feeds, reading views, media
  players' body content)**: never Liquid Glass. Use standard materials
  or flat fills. Reading apps in particular should prioritize legibility
  over any glass effect.
- **Scroll edge effects**: a companion system that works with Liquid
  Glass to maintain separation between floating functional-layer
  elements and the content scrolling beneath them (e.g., content fades
  or blurs slightly right at the edge where it passes under a glass tab
  bar) — inherently adaptive, like the glass itself.

## 7. Accessibility & adaptive behavior

These system accessibility settings automatically modify Liquid Glass —
replicate the same fallbacks if you build custom glass components:

- **Reduce Transparency** → glass becomes frostier / more opaque,
  obscuring more of what's behind it.
- **Increase Contrast** → elements become predominantly black or white
  with a contrasting border, dropping most of the translucency effect.
- **Reduce Motion** → lowers effect intensity and disables elastic /
  parallax behaviors.

Content-first hierarchy still governs: keep glass minimal above busy
imagery, and always provide a solid-fill fallback style in any design
token set so glass isn't a hard dependency for legibility.

## 8. Performance budgets (practical, not official Apple numbers)

Practitioner guidance converging around: max ~4 compositing/glass layers
per screen; blur radius roughly ≤40px on iPhone, ≤60px on iPad/Mac.
Treat these as sane defaults for custom implementations and prototypes,
not hard Apple-published limits.

## 9. Common misuse patterns to avoid

- Applying glass to a full-screen background.
- Applying glass to scrollable content itself (lists, tables, feeds).
- Stacking two glass elements (glass control inside/over another glass
  panel).
- Mixing Regular and Clear variants in the same view.
- Applying glass to *every* control "because it looks nice" — dilutes
  the signal that glass = functional/navigational.
- Giving glass-topped icons/labels their own glass effect too (should be
  flat/vibrant, sitting *on* the one glass layer, not adding a second).
- Ignoring Reduced Transparency / Reduced Motion / Increased Contrast in
  custom (non-system) glass components.

## 10. Implementation notes

**SwiftUI**: `.glassEffect()` modifier produces both variants (Regular
default; pass `.clear` for the Clear variant). System components (TabView,
NavigationSplitView sidebars, toolbars) adopt Liquid Glass automatically
under iOS/iPadOS/macOS 26 SDKs — prefer these over custom glass views
wherever possible, since they inherit the accessibility fallbacks for
free.

**Web/HTML/React approximation** (for mockups/artifacts, not real Apple
runtimes):
```css
.liquid-glass-functional {
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  background: rgba(255, 255, 255, 0.55); /* swap for dark-mode rgba(30,30,30,0.45) */
  border: 1px solid rgba(255, 255, 255, 0.35); /* inner highlight edge */
  border-radius: 20px; /* derive from parent/device corner radius, not arbitrary */
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
/* Content underneath keeps a flat/standard background — never this class */
```
Reserve this styling for nav bars, floating toolbars, and sheets in the
mockup; keep reading content, cards, and feed items on plain surfaces.

## 11. Sources

- Apple, Human Interface Guidelines → Materials:
  developer.apple.com/design/human-interface-guidelines/materials
- Apple, WWDC25 "Meet Liquid Glass": developer.apple.com/videos/play/wwdc2025/219/
- Apple, "Adopting Liquid Glass" technology overview:
  developer.apple.com/documentation/TechnologyOverviews/adopting-liquid-glass
- Apple HIG → Tab Bars (developer.apple.com/design/human-interface-guidelines/tab-bars)
- Practitioner analysis: blakecrosley.com/blog/liquid-glass-swiftui-patterns (Apr 2026)
- Practitioner analysis: joshcusick.substack.com — sub-layer anatomy breakdown (Nov 2025)
- Practitioner analysis: blog.logrocket.com/ux-design/adopting-liquid-glass-examples-best-practices
- Practitioner analysis: designedforhumans.tech — accessibility/performance guidance
- Practitioner analysis: rogerwong.me/2025/06/breaking-down-apples-liquid-glass
- Practitioner analysis: fenx.substack.com/p/beyond-liquid-glass-apples-transformations
- Superdesign, "Apple Design System Breakdown" (2026) — HIG fundamentals (Clarity/Deference/Depth, SF Pro, Dynamic Type, semantic color)

Apple's live HIG pages are the authority if this drifts from what's
currently published — check developer.apple.com/design/human-interface-guidelines
directly for anything that must be pixel/API accurate.
