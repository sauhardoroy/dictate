"""Design tokens, typography, and animation parameters adhering to Apple's Human Interface Guidelines.

==============================================================================
APPLE LIQUID GLASS DESIGN SYSTEM TOKENS & PARAMETERS
==============================================================================
"""
from dataclasses import dataclass
from PyQt6.QtGui import QFont

# ---------------------------------------------------------------------------
# 1. PILL GEOMETRY & MORPHING DIMENSIONS (Apple Dynamic Island / HUD)
# ---------------------------------------------------------------------------
PILL_HEIGHT = 60           # Default baseline height in logical pixels

WIDTH_IDLE = 60
HEIGHT_IDLE = 60
CORNER_RADIUS_IDLE = 30.0

WIDTH_RECORDING = 310      # Expanded state for top waveforms + bottom 3-card carousel
HEIGHT_RECORDING = 102
CORNER_RADIUS_RECORDING = 20.0

WIDTH_PREVIEW = 310
HEIGHT_PREVIEW = 102

WIDTH_TRANSCRIBING = 60
HEIGHT_TRANSCRIBING = 60

WIDTH_INJECTING = 60
HEIGHT_INJECTING = 60

WIDTH_LOADING = 60
HEIGHT_LOADING = 60

WIDTH_ERROR = 60
HEIGHT_ERROR = 60

# ---------------------------------------------------------------------------
# 2. MOTION, SPRING CURVES & ANIMATION TIMINGS
# ---------------------------------------------------------------------------
MORPH_DURATION_MS = 280    # Snappy spring morphing duration
EXIT_DURATION_MS = 260     # Fast clean collapse back to idle orb
MORPH_OVERSHOOT = 0.85     # QEasingCurve.OutBack (natural organic rebound)

PULSE_DURATION_MS = 750    # Smooth breathing cycle for Transcribing/Loading
SHAKE_DURATION_MS = 280    # Error shake duration
SHAKE_DISTANCE_PX = 5      # Horizontal displacement during error shake

METER_SMOOTHING = 0.30     # Audio level exponential interpolation factor
BACKDROP_UPDATE_MS = 15    # Background screen sampling interval (~60 FPS)

# ---------------------------------------------------------------------------
# 3. APPLE SYSTEM ACCENTS & TINTS (Light / Dark Pairs)
# ---------------------------------------------------------------------------
SYSTEM_BLUE = ("#007AFF", "#0A84FF")       # Primary actions & links
SYSTEM_CYAN = ("#0284C7", "#38BDF8")       # Idle & ready state (Ice Sapphire)
SYSTEM_GREEN = ("#34C759", "#30D158")      # Injected & success (Emerald)
SYSTEM_ROSE = ("#E11D48", "#FB7185")       # Recording / listening (Rose)
SYSTEM_PINK = SYSTEM_ROSE
SYSTEM_PURPLE = ("#7C3AED", "#A855F7")     # Thinking / AI polish (Royal Amethyst)
SYSTEM_RED = ("#DC2626", "#F87171")        # Error & cancel
SYSTEM_TEAL = SYSTEM_CYAN

# Monochrome / Slate scales
SYSTEM_GRAY = ("#8E8E93", "#64748B")
SYSTEM_GRAY2 = ("#636366", "#475569")
SYSTEM_GRAY3 = ("#48484A", "#334155")
SYSTEM_GRAY4 = ("#3A3A3C", "#1E293B")
SYSTEM_GRAY5 = ("#2C2C2E", "#0F172A")
SYSTEM_GRAY6 = ("#1C1C1E", "#090D16")

WHITE = "#FFFFFF"
BLACK = "#000000"

# ---------------------------------------------------------------------------
# 4. APPLE VIBRANCY TYPOGRAPHY & SURFACES (Light / Dark Pairs)
# ---------------------------------------------------------------------------
# Apple Label Hierarchy (Luminance & Contrast)
TEXT_PRIMARY = ("#1D1D1F", "#F8FAFC")      # 100% contrast: Titles, active words, primary labels
TEXT_SECONDARY = ("#6E6E73", "#94A3B8")    # 70% vibrancy: Subtitles, keycaps, secondary metadata
TEXT_MUTED = ("#8E8E93", "#64748B")        # 45% vibrancy: Inactive words, timestamps, hints
TEXT_TERTIARY = TEXT_MUTED
TEXT_QUATERNARY = ("#C7C7CC", "#334155")   # 20% vibrancy: Hairlines, subtle dividers

# Structural Surfaces & Glass Backings
SURFACE_CANVAS = ("#F2F2F7", "#000000")    # System canvas
SURFACE_BG = ("#F8FAFC", "#090D16")        # Dialog window background
SURFACE_CARD = ("#FFFFFF", "#131B2E")      # Inset grouped cards
SURFACE_ELEVATED = ("#F1F5F9", "#1E293B")  # Elevated planks & inputs
SURFACE_HOVER = ("#E2E8F0", "#293548")     # Interactive hover state

BORDER_SUBTLE = ("rgba(0,0,0,0.06)", "rgba(255,255,255,0.08)")
BORDER_FOCUS = ("#007AFF", "#38BDF8")

# ---------------------------------------------------------------------------
# 5. LIQUID GLASS OPTICAL PARAMETERS
# ---------------------------------------------------------------------------
GLASS_IOR = 1.25                           # Index of refraction
GLASS_DISPERSION = 0.20                    # Cauchy chromatic dispersion
GLASS_SPECULAR_POW = 8.0                   # Blinn-Phong shininess exponent
GLASS_FRESNEL_POW = 4.5                    # Grazing edge rim reflectance


@dataclass(frozen=True)
class StateStyle:
    accent: tuple[str, str]     # (light, dark)
    width: int                  # target pill width in logical px
    height: int                 # target pill height in logical px
    label: str                  # accessible / tooltip text
    morphs: bool                # whether this state triggers a morph


STATES: dict[str, StateStyle] = {
    "idle":         StateStyle(SYSTEM_CYAN, WIDTH_IDLE, HEIGHT_IDLE, "Dictate", False),
    "recording":    StateStyle(SYSTEM_ROSE, WIDTH_RECORDING, HEIGHT_RECORDING, "Listening", True),
    "preview":      StateStyle(SYSTEM_GRAY2, WIDTH_PREVIEW, HEIGHT_PREVIEW, "Listening…", True),
    "transcribing": StateStyle(SYSTEM_PURPLE, WIDTH_TRANSCRIBING, HEIGHT_TRANSCRIBING, "Thinking", True),
    "injecting":    StateStyle(SYSTEM_GREEN, WIDTH_INJECTING, HEIGHT_INJECTING, "Pasted", True),
    "loading":      StateStyle(SYSTEM_GRAY, WIDTH_LOADING, HEIGHT_LOADING, "Loading", False),
    "error":        StateStyle(SYSTEM_RED, WIDTH_ERROR, HEIGHT_ERROR, "Error", False),
}


def pick(pair: tuple[str, str], dark: bool) -> str:
    """Select the light/dark value from a semantic token pair."""
    return pair[1] if dark else pair[0]


def get_font(size: int = 12, weight: QFont.Weight = QFont.Weight.Normal, letter_spacing: float = 0.0) -> QFont:
    """Get an Apple-compliant typography font with SF Pro Display / Text fallback."""
    font = QFont()
    font.setFamilies([
        "SF Pro Display",
        "SF Pro Text",
        "SF Pro",
        "Segoe UI Variable Text",
        "Segoe UI Variable Display",
        "Segoe UI",
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
    """Unified Apple macOS-style QSS stylesheet with frosted glass styling and grouped planks."""
    bg = pick(SURFACE_BG, dark)
    card = pick(SURFACE_CARD, dark)
    elevated = pick(SURFACE_ELEVATED, dark)
    hover = pick(SURFACE_HOVER, dark)
    text = pick(TEXT_PRIMARY, dark)
    muted = pick(TEXT_MUTED, dark)
    accent = pick(SYSTEM_CYAN, dark)
    border = "#334155" if dark else "#E2E8F0"
    border_subtle = "rgba(255, 255, 255, 0.08)" if dark else "rgba(0, 0, 0, 0.06)"

    return f"""
    QDialog {{
        background-color: {bg};
        color: {text};
        font-family: -apple-system, 'SF Pro Display', 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    }}
    QWidget {{
        color: {text};
        font-family: -apple-system, 'SF Pro Display', 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    }}
    QGroupBox {{
        background-color: {card};
        border: 1px solid {border_subtle};
        border-radius: 10px;
        margin-top: 14px;
        padding-top: 16px;
        padding-bottom: 12px;
        padding-left: 14px;
        padding-right: 14px;
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 0.05em;
        color: {accent};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding-left: 10px;
        padding-right: 10px;
        padding-top: 2px;
        color: {accent};
        text-transform: uppercase;
    }}
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
        background-color: {elevated};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        padding: 7px 12px;
        color: {text};
        font-size: 12px;
        selection-background-color: {accent};
    }}
    QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
        border: 1px solid {accent};
        background-color: {card};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {card};
        border: 1px solid {border};
        border-radius: 8px;
        selection-background-color: {hover};
        selection-color: {accent};
        padding: 4px;
        outline: none;
    }}
    QPushButton {{
        background-color: {elevated};
        color: {text};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        padding: 7px 16px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {hover};
        border-color: {accent};
    }}
    QPushButton:pressed {{
        background-color: {border};
    }}
    QPushButton#primaryButton {{
        background-color: #0284C7;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background-color: #0369A1;
    }}
    QCheckBox {{
        spacing: 10px;
        font-size: 12px;
        color: {text};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid {border};
        background-color: {elevated};
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
        font-size: 11px;
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
        font-size: 12px;
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
