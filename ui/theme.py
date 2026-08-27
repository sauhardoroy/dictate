"""Design tokens, typography, concentric geometry, and animation parameters adhering to
Apple's Human Interface Guidelines (HIG) and the Liquid Glass functional layer specification.

==============================================================================
APPLE LIQUID GLASS DESIGN SYSTEM TOKENS & PARAMETERS
==============================================================================
"""
from dataclasses import dataclass
from PyQt6.QtGui import QFont

# ---------------------------------------------------------------------------
# 1. CONCENTRIC GEOMETRY & PILL MORPHING DIMENSIONS
# ---------------------------------------------------------------------------
PILL_BASELINE_HEIGHT = 60      # Idle circular pill diameter

WIDTH_IDLE = 60
HEIGHT_IDLE = 60
RADIUS_PILL_IDLE = 30.0

WIDTH_RECORDING = 320          # Expanded listening capsule (waveform + live text)
HEIGHT_RECORDING = 74
RADIUS_PILL_RECORDING = 24.0

WIDTH_PREVIEW = 320
HEIGHT_PREVIEW = 74

WIDTH_TRANSCRIBING = 130       # Compact processing capsule
HEIGHT_TRANSCRIBING = 52
RADIUS_PILL_TRANSCRIBING = 26.0

WIDTH_INJECTING = 120          # Confirmation capsule
HEIGHT_INJECTING = 52
RADIUS_PILL_INJECTING = 26.0

WIDTH_LOADING = 60
HEIGHT_LOADING = 60

WIDTH_ERROR = 60
HEIGHT_ERROR = 60

# Concentric corner radius scale
RADIUS_CONTROL = 8.0           # Buttons, inputs, switches
RADIUS_CARD = 12.0             # Content cards, group boxes, list items
RADIUS_CONTAINER = 16.0        # Segmented bars, dialog sections, popovers
RADIUS_WINDOW = 20.0           # Frameless dialogs, onboarding window

# Standard Spacing Scale (4, 8, 12, 16, 20, 24, 32)
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 20
SPACE_2XL = 24
SPACE_3XL = 32

# ---------------------------------------------------------------------------
# 2. MOTION, SPRING TIMINGS & ADAPTIVE CONSTANTS
# ---------------------------------------------------------------------------
DURATION_INSTANT = 0
DURATION_FEEDBACK = 140        # Button clicks, micro-interactions, copy checkmarks
DURATION_MORPH = 240           # Smooth symmetrical capsule expansion
DURATION_EXIT = 200            # Clean collapse back to idle orb
DURATION_PULSE = 800           # Breathing cycle for Processing/Loading
DURATION_CROSSFADE = 160       # Page/tab cross-fades

MORPH_OVERSHOOT = 0.35         # Gentle organic rebound (restrained, no bouncy agitation)
SHAKE_DURATION_MS = 260        # Error shake duration
SHAKE_DISTANCE_PX = 4          # Horizontal displacement during error

METER_SMOOTHING = 0.28         # Audio level exponential interpolation factor
BACKDROP_UPDATE_MS = 25        # Background screen sampling interval (~40 FPS when active)

# ---------------------------------------------------------------------------
# 3. SEMANTIC SYSTEM PALETTE (Light / Dark Pairs)
# ---------------------------------------------------------------------------
# Interaction Accents
SYSTEM_BLUE = ("#007AFF", "#0A84FF")       # Primary actions, links, active state
SYSTEM_CYAN = ("#0284C7", "#38BDF8")       # Idle & ready state (Ice Sapphire)
SYSTEM_GREEN = ("#16A34A", "#30D158")      # Injected & success (Emerald)
SYSTEM_ROSE = ("#E11D48", "#FB7185")       # Recording / listening (Rose)
SYSTEM_PINK = SYSTEM_ROSE
SYSTEM_PURPLE = ("#7C3AED", "#A855F7")     # Processing / AI polish (Royal Amethyst)
SYSTEM_RED = ("#DC2626", "#F87171")        # Error & cancel
SYSTEM_AMBER = ("#D97706", "#FBBF24")      # Warning & notice
SYSTEM_TEAL = SYSTEM_CYAN

# Neutral Scales
SYSTEM_GRAY = ("#8E8E93", "#64748B")
SYSTEM_GRAY2 = ("#636366", "#475569")
SYSTEM_GRAY3 = ("#48484A", "#334155")
SYSTEM_GRAY4 = ("#3A3A3C", "#1E293B")
SYSTEM_GRAY5 = ("#2C2C2E", "#0F172A")
SYSTEM_GRAY6 = ("#1C1C1E", "#090D16")

WHITE = "#FFFFFF"
BLACK = "#000000"

# ---------------------------------------------------------------------------
# 4. CONTENT & SURFACE TOKENS (Light / Dark Pairs)
# ---------------------------------------------------------------------------
# Typography Hierarchy (Contrast & Vibrancy)
TEXT_PRIMARY = ("#0F172A", "#F8FAFC")      # 100% contrast: Titles, active words, primary labels
TEXT_SECONDARY = ("#475569", "#94A3B8")    # 70% vibrancy: Subtitles, keycaps, secondary metadata
TEXT_MUTED = ("#64748B", "#64748B")        # 45% vibrancy: Timestamps, hints, caption notes
TEXT_TERTIARY = TEXT_MUTED
TEXT_QUATERNARY = ("#CBD5E1", "#334155")   # Hairlines, subtle dividers

# Structural Surfaces (Content Layer - Standard Flat & Grouped Materials)
SURFACE_CANVAS = ("#F8FAFC", "#090D16")    # System canvas
SURFACE_BG = ("#FFFFFF", "#0F172A")        # Dialog window background
SURFACE_CARD = ("#F1F5F9", "#131B2E")      # Inset grouped cards / list rows
SURFACE_ELEVATED = ("#E2E8F0", "#1E293B")  # Elevated planks, groupboxes, inputs
SURFACE_HOVER = ("#CBD5E1", "#283548")     # Interactive hover state
SURFACE_SUNKEN = ("#E2E8F0", "#0B101C")    # Sunken wells, progress tracks

# Borders & Rings
BORDER_SUBTLE = ("rgba(0, 0, 0, 0.08)", "rgba(255, 255, 255, 0.08)")
BORDER_STRONG = ("#CBD5E1", "#334155")
BORDER_FOCUS = ("#007AFF", "#38BDF8")

# ---------------------------------------------------------------------------
# 5. LIQUID GLASS OPTICAL PARAMETERS (Functional Layer)
# ---------------------------------------------------------------------------
GLASS_IOR = 1.22                           # Index of refraction (smooth Snell's law)
GLASS_DISPERSION = 0.10                    # Restrained chromatic dispersion for razor-sharp text
GLASS_SPECULAR_POW = 8.0                   # Blinn-Phong shininess exponent
GLASS_FRESNEL_POW = 4.5                    # Grazing edge rim reflectance
GLASS_RIM_WIDTH = 1.0                      # 1px inner highlight edge

# High Contrast / Reduced Transparency Fallback Colors
SURFACE_OPAQUE_FALLBACK_DARK = "#1E293B"
SURFACE_OPAQUE_FALLBACK_LIGHT = "#FFFFFF"


@dataclass(frozen=True)
class StateStyle:
    accent: tuple[str, str]     # (light, dark)
    width: int                  # target pill width in logical px
    height: int                 # target pill height in logical px
    corner_radius: float        # concentric corner radius in logical px
    label: str                  # accessible / tooltip text
    accessible_name: str        # screen reader state description
    morphs: bool                # whether this state triggers a morph


STATES: dict[str, StateStyle] = {
    "idle":         StateStyle(SYSTEM_CYAN, WIDTH_IDLE, HEIGHT_IDLE, RADIUS_PILL_IDLE, "Ready", "Dictate, ready. Activate to start dictation.", False),
    "recording":    StateStyle(SYSTEM_ROSE, WIDTH_RECORDING, HEIGHT_RECORDING, RADIUS_PILL_RECORDING, "Listening", "Dictate, listening. Click or press hotkey to stop.", True),
    "preview":      StateStyle(SYSTEM_ROSE, WIDTH_PREVIEW, HEIGHT_PREVIEW, RADIUS_PILL_RECORDING, "Listening", "Dictate, listening. Click or press hotkey to stop.", True),
    "transcribing": StateStyle(SYSTEM_PURPLE, WIDTH_TRANSCRIBING, HEIGHT_TRANSCRIBING, RADIUS_PILL_TRANSCRIBING, "Processing", "Dictate, processing speech…", True),
    "injecting":    StateStyle(SYSTEM_GREEN, WIDTH_INJECTING, HEIGHT_INJECTING, RADIUS_PILL_INJECTING, "Inserted", "Dictate, text inserted successfully.", True),
    "loading":      StateStyle(SYSTEM_GRAY, WIDTH_LOADING, HEIGHT_LOADING, RADIUS_PILL_IDLE, "Loading", "Dictate, loading speech model…", False),
    "error":        StateStyle(SYSTEM_RED, WIDTH_ERROR, HEIGHT_ERROR, RADIUS_PILL_IDLE, "Needs attention", "Dictate, needs attention. Click to retry.", False),
}


def pick(pair: tuple[str, str], dark: bool) -> str:
    """Select the light/dark value from a semantic token pair."""
    return pair[1] if dark else pair[0]


def get_font(size: int = 12, weight: QFont.Weight = QFont.Weight.Normal, letter_spacing: float = 0.0) -> QFont:
    """Get an Apple/Windows compliant typography font with Segoe UI Variable / SF Pro fallback."""
    font = QFont()
    font.setFamilies([
        "Segoe UI Variable Text",
        "Segoe UI Variable Display",
        "Segoe UI",
        "SF Pro Display",
        "SF Pro Text",
        "SF Pro",
        "-apple-system",
        "Inter",
        "sans-serif",
    ])
    font.setPixelSize(size)
    font.setWeight(weight)
    if letter_spacing != 0.0:
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100.0 + letter_spacing * 100.0)
    return font


def get_dialog_stylesheet(dark: bool = True) -> str:
    """Universal Apple/Windows QSS stylesheet for the Content Layer (standard flat/grouped materials)."""
    bg = pick(SURFACE_BG, dark)
    card = pick(SURFACE_CARD, dark)
    elevated = pick(SURFACE_ELEVATED, dark)
    hover = pick(SURFACE_HOVER, dark)
    text = pick(TEXT_PRIMARY, dark)
    secondary = pick(TEXT_SECONDARY, dark)
    muted = pick(TEXT_MUTED, dark)
    accent = pick(SYSTEM_BLUE, dark)
    focus_ring = pick(BORDER_FOCUS, dark)
    border = pick(BORDER_STRONG, dark)
    border_subtle = pick(BORDER_SUBTLE, dark)

    return f"""
    QDialog {{
        background-color: {bg};
        color: {text};
        font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
    }}
    QWidget {{
        color: {text};
        font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
    }}
    QLabel {{
        color: {text};
        font-size: 13px;
    }}
    QGroupBox {{
        background-color: {card};
        border: 1px solid {border_subtle};
        border-radius: 12px;
        margin-top: 18px;
        padding-top: 20px;
        padding-bottom: 14px;
        padding-left: 16px;
        padding-right: 16px;
        font-weight: 600;
        font-size: 12px;
        color: {secondary};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding-left: 10px;
        padding-right: 10px;
        padding-top: 2px;
        color: {accent};
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.04em;
    }}
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
        background-color: {elevated};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        padding: 7px 12px;
        color: {text};
        font-size: 13px;
        min-height: 20px;
        selection-background-color: {accent};
        selection-color: #FFFFFF;
    }}
    QLineEdit:hover, QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover {{
        border-color: {border};
    }}
    QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
        border: 1.5px solid {focus_ring};
        background-color: {card};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {card};
        border: 1px solid {border};
        border-radius: 8px;
        selection-background-color: {hover};
        selection-color: {text};
        padding: 4px;
        outline: none;
    }}
    QPushButton {{
        background-color: {elevated};
        color: {text};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 12px;
        font-weight: 600;
        min-height: 18px;
    }}
    QPushButton:hover {{
        background-color: {hover};
        border-color: {border};
    }}
    QPushButton:pressed {{
        background-color: {border};
    }}
    QPushButton:focus {{
        border: 2px solid {focus_ring};
    }}
    QPushButton#primaryButton {{
        background-color: {accent};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 20px;
    }}
    QPushButton#primaryButton:hover {{
        background-color: #0066D6;
    }}
    QPushButton#primaryButton:pressed {{
        background-color: #0052B3;
    }}
    QPushButton#primaryButton:focus {{
        border: 2px solid #FFFFFF;
    }}
    QCheckBox {{
        spacing: 10px;
        font-size: 13px;
        color: {text};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1.5px solid {border};
        background-color: {elevated};
    }}
    QCheckBox::indicator:hover {{
        border-color: {accent};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border-color: {accent};
    }}
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 6px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        min-height: 24px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QToolTip {{
        background-color: {card};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}
    QMenu {{
        background-color: {card};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 20px 6px 12px;
        border-radius: 6px;
        color: {text};
        font-size: 13px;
    }}
    QMenu::item:selected {{
        background-color: {hover};
        color: {accent};
    }}
    QMenu::separator {{
        height: 1px;
        background: {border_subtle};
        margin: 4px 6px;
    }}
    """
