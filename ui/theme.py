"""Compatibility bridge for Dictate UI design tokens and states.

All tokens, shapes, motion constants, and color definitions are consolidated
in `ui.material_theme`. This file re-exports standard HUD states and token
accessors.
"""
from __future__ import annotations

from ui.material_theme import (
    FONT_FAMILY,
    HUD_STATES,
    MOTION,
    Shape,
    StateSpec,
    Tokens,
    build_qss,
    get_tokens,
    is_system_dark_mode,
)

# Pill State Specs (width, height, label, accessible_name)
STATES = HUD_STATES

# Geometry constants
WIDTH_IDLE = HUD_STATES["idle"].width
HEIGHT_IDLE = HUD_STATES["idle"].height

WIDTH_RECORDING = HUD_STATES["recording"].width
HEIGHT_RECORDING = HUD_STATES["recording"].height

WIDTH_TRANSCRIBING = HUD_STATES["transcribing"].width
HEIGHT_TRANSCRIBING = HUD_STATES["transcribing"].height

WIDTH_INJECTING = HUD_STATES["injecting"].width
HEIGHT_INJECTING = HUD_STATES["injecting"].height

WIDTH_LOADING = HUD_STATES["loading"].width
HEIGHT_LOADING = HUD_STATES["loading"].height

WIDTH_ERROR = HUD_STATES["error"].width
HEIGHT_ERROR = HUD_STATES["error"].height
