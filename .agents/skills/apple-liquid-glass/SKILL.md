---
name: apple-liquid-glass-design
description: Apply Apple's Human Interface Guidelines (HIG) and Liquid Glass design language (iOS 26 / iPadOS 26 / macOS Tahoe 26 / watchOS 26 / tvOS 26, introduced WWDC 2025) when designing or building Apple-platform UI, SwiftUI/UIKit/AppKit interfaces, or any mockup/prototype/artifact that should look "native Apple." Use this whenever the user asks for an Apple-style, iOS-style, or "liquid glass" UI, mentions tab bars, sidebars, toolbars, navigation bars, sheets, or asks how to layer glass/materials/blur correctly, what goes in the "content layer" vs. "functional layer," which corner radius/concentricity to use, or how to avoid common Liquid Glass misuse (glass-on-glass, glass on content, overuse). Push to use this skill even if the user just says "make it feel more like Apple" or "iOS 26 style" without naming Liquid Glass explicitly.
---

# Apple Liquid Glass Design

Guidance for applying Apple's Liquid Glass material and the wider Human
Interface Guidelines (HIG) correctly — whether the deliverable is a SwiftUI
view, a Figma-style mockup, an HTML/React artifact, or design advice in
prose. Liquid Glass is Apple's cross-platform material introduced at
WWDC25 (June 2025), shipping across iOS/iPadOS 26, macOS Tahoe 26,
watchOS 26, tvOS 26, and echoing visionOS. It is described as the biggest
UI shift since iOS 7.

Read `references/liquid-glass-guidelines.md` for the full detail (layer
model, material anatomy, variants, per-component rules, accessibility,
performance budgets, sourced citations). This file is the fast-reference
summary — enough for most requests; open the reference file for anything
component-specific or when precision matters (e.g. building a real
`.glassEffect()` SwiftUI view, or a pixel-accurate mockup).

## The one rule that matters most

**Liquid Glass belongs to the functional layer, never the content layer.**

Apple's HIG defines exactly two layers in every iOS 26+ interface:

| Layer | What lives there | Material to use |
|---|---|---|
| **Content layer** | The document, feed, photo, list, map, or media a person is actually consuming | Standard materials only (`.regularMaterial`, `.thinMaterial`, flat fills) — **never Liquid Glass** |
| **Functional layer** | Navigation and transient controls that float above content: tab bars, sidebars, toolbars, floating action buttons, sheets, alerts, popovers, the Dock | **Liquid Glass** |

If you find yourself tempted to put glass behind text the user is meant
to read, on a card in a list, on a full-screen background, or on a
scrollable content view — stop. That's a content-layer surface. Use a
plain fill or a standard (non-Liquid-Glass) material there instead.

Corollary rules, always apply:
- **Never stack glass on glass.** One glass layer at a time; nesting or
  overlapping two Liquid Glass elements muddies the hierarchy.
- **Elements placed on top of glass** (icons, labels) should NOT also get
  a glass effect — use plain fills/vibrancy so they read as a thin layer
  fused to the material, not a second pane of glass.
- **Use sparingly.** Liquid Glass exists to draw the eye to controls that
  need it (primary nav, key actions) — applying it to every button or
  panel defeats its purpose and hurts legibility/performance.

## Quick decision checklist

1. **What layer is this element in?** Content → standard material or flat
   fill. Functional/navigation/transient → Liquid Glass.
2. **Which variant?** Default to **Regular** (adaptive, legible in any
   context). Only use **Clear** when: the element sits over media-rich
   content (photo, video), AND a dimming layer won't hurt that content's
   legibility, AND you need max transparency for a deliberate, temporary
   effect. Never mix Regular and Clear on the same screen.
3. **Shape**: match corner radius to the device/window's corner
   radius family — this is Apple's "concentricity" principle (controls
   and containers nest visually with the hardware's rounded corners).
   Don't use arbitrary radii.
4. **Motion & light**: glass should react to scroll, touch, and device
   motion (specular highlights, subtle refraction) — but respect Reduced
   Motion (disable elastic/parallax effects) and Reduced Transparency
   (fall back to a frostier, more opaque rendering) when those
   accessibility settings are on. These fallbacks are automatic in
   system components; replicate them in custom ones.
5. **One glass surface per region.** If two floating controls would
   overlap, merge them into a single glass shape rather than stacking.

## Typography, color, layout (still governs everything, glass or not)

- **Typeface**: SF Pro (SF Pro Rounded/Mono for special cases). Dynamic
  Type scale — Body 17pt, Large Title 34pt at default size — must scale
  with the user's text-size setting.
- **Color**: semantic system colors (e.g. `systemBlue`) that auto-adapt
  to light/dark mode — don't hardcode hex values for anything
  system-adjacent.
- **Targets**: 44×44pt minimum tappable area.
- **Three long-standing HIG principles** that Liquid Glass is built on
  top of, not a replacement for: **Clarity, Deference, Depth.**

## When building an artifact/prototype (HTML, React, SVG)

- Approximate the glass look with: `backdrop-filter: blur(...)`,
  low-opacity white/black fill depending on light/dark, a subtle inner
  highlight border, and soft drop shadow — reserved for the nav/toolbar
  chrome only, exactly as above. Keep blur radius modest (roughly
  20–40px equivalent) — real Liquid Glass is refined, not a heavy frosted
  blur.
- Keep actual content (text blocks, images, cards being read) on flat or
  standard-material backgrounds so the content/functional distinction
  reads clearly even outside a real Apple runtime.
- See `references/liquid-glass-guidelines.md` for per-component notes
  (tab bars, sidebars, toolbars, sheets) and copy-ready CSS/SwiftUI
  snippets.

## Sources

Apple's own HIG (`developer.apple.com/design/human-interface-guidelines`,
Materials page) and WWDC25 session "Meet Liquid Glass" are authoritative.
This skill was compiled from those plus practitioner write-ups current as
of mid-2026 (full citation list in the reference file) — treat Apple's
live HIG pages as the tie-breaker if anything here seems to have drifted.
