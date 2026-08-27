"""Design tokens and animation parameters for Dictate's Shape-Shifting Liquid Glass UI.

==============================================================================
TUNABLE PARAMETERS FOR PILL GEOMETRY, MOTION & ANIMATION TIMINGS
(Modify any of the values below to customize the animation behavior)
==============================================================================
"""
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 1. PILL GEOMETRY & MORPHING DIMENSIONS
# ---------------------------------------------------------------------------
PILL_HEIGHT = 60           # Default/baseline height in logical pixels

# Geometry of each state in logical pixels (width, height):
WIDTH_IDLE = 60
HEIGHT_IDLE = 60
CORNER_RADIUS_IDLE = 30.0

WIDTH_RECORDING = 310      # Unified width (Spotify-style widget with top 1/3 waves + bottom 2/3 cards)
HEIGHT_RECORDING = 102      # Increased height for spacious top 1/3 waveforms + bottom 2/3 solitaire deck
CORNER_RADIUS_RECORDING = 20.0  # Same corner radius as the 60x60 circular idle state

WIDTH_PREVIEW = 310        # Same as recording
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
# 2. MOTION & ANIMATION TIMINGS
# ---------------------------------------------------------------------------
MORPH_DURATION_MS = 300    # Duration in milliseconds to morph into a larger state (e.g. Recording)
EXIT_DURATION_MS = 300     # Duration in milliseconds to morph back to smaller state (e.g. Idle)
MORPH_OVERSHOOT = 0.8     # QEasingCurve.OutBack overshoot (1.0 = smooth cubic, 1.25 = snappy bouncy)

PULSE_DURATION_MS = 800    # Breathing cycle duration for Transcribing/Loading states (ms)
SHAKE_DURATION_MS = 300    # Error shake animation duration (ms)
SHAKE_DISTANCE_PX = 5      # Maximum horizontal displacement during error shake (px)

METER_SMOOTHING = 0.30     # Audio level exponential interpolation factor (0.0 = slow, 1.0 = instant)
BACKDROP_UPDATE_MS = 15    # Background screen sampling interval in milliseconds (30ms = ~33 FPS)

# ---------------------------------------------------------------------------
# 3. COLOR PALETTES & STATE STYLES (Deeper, darker, contrasty icon tones)
# ---------------------------------------------------------------------------
SYSTEM_RED = ("#B91C1C", "#DC2626")       # Darker bold crimson
SYSTEM_GREEN = ("#15803D", "#16A34A")     # Darker rich forest emerald
SYSTEM_TEAL = ("#0369A1", "#0284C7")      # Darker deep sapphire cyan (Idle state)
SYSTEM_PURPLE = ("#6D28D9", "#7C3AED")    # Darker royal amethyst violet (Transcribing state)
SYSTEM_CYAN = ("#0284C7", "#38BDF8")      # Sleek Apple Ice Cyan / Sapphire (Recording state)
SYSTEM_PINK = ("#BE123C", "#E11D48")      # Rose

SYSTEM_GRAY = ("#475569", "#64748B")      # Darker slate
SYSTEM_GRAY2 = ("#334155", "#475569")
SYSTEM_GRAY3 = ("#1E293B", "#334155")
SYSTEM_GRAY4 = ("#0F172A", "#1E293B")
SYSTEM_GRAY5 = ("#E5E5EA", "#1E293B")
SYSTEM_GRAY6 = ("#F2F2F7", "#0F172A")

WHITE = "#FFFFFF"
BLACK = "#000000"

TEXT_PRIMARY = ("#1D1D1F", "#F8FAFC")
TEXT_SECONDARY = ("#6E6E73", "#94A3B8")
TEXT_MUTED = ("#8E8E93", "#64748B")

SURFACE_BG = ("#F8FAFC", "#090D16")
SURFACE_CARD = ("#FFFFFF", "#131B2E")
SURFACE_ELEVATED = ("#F1F5F9", "#1E293B")
SURFACE_HOVER = ("#E2E8F0", "#293548")

BORDER_SUBTLE = ("rgba(0,0,0,0.08)", "rgba(255,255,255,0.08)")
BORDER_FOCUS = ("#0284C7", "#0284C7")


@dataclass(frozen=True)
class StateStyle:
    accent: tuple[str, str]     # (light, dark)
    width: int                  # target pill width in logical px at this state
    height: int                 # target pill height in logical px at this state
    label: str                  # accessible/tooltip text
    morphs: bool                # whether this state triggers a shape/size morph


STATES: dict[str, StateStyle] = {
    "idle":         StateStyle(SYSTEM_TEAL, WIDTH_IDLE, HEIGHT_IDLE, "Dictate", False),
    "recording":    StateStyle(SYSTEM_PINK, WIDTH_RECORDING, HEIGHT_RECORDING, "Listening", True),
    "preview":      StateStyle(SYSTEM_GRAY2 , WIDTH_PREVIEW, HEIGHT_PREVIEW, "Listening…", True),
    "transcribing": StateStyle(SYSTEM_PURPLE, WIDTH_TRANSCRIBING, HEIGHT_TRANSCRIBING, "Thinking", True),
    "injecting":    StateStyle(SYSTEM_GREEN, WIDTH_INJECTING, HEIGHT_INJECTING, "Pasted", True),
    "loading":      StateStyle(SYSTEM_GRAY, WIDTH_LOADING, HEIGHT_LOADING, "Loading", False),
    "error":        StateStyle(SYSTEM_RED, WIDTH_ERROR, HEIGHT_ERROR, "Error", False),
}


def pick(pair: tuple[str, str], dark: bool) -> str:
    """Select the light/dark value from a semantic token pair."""
    return pair[1] if dark else pair[0]


def get_dialog_stylesheet(dark: bool = True) -> str:
    """Unified, sleek modern QSS stylesheet for all Dictate dialogs."""
    bg = pick(SURFACE_BG, dark)
    card = pick(SURFACE_CARD, dark)
    elevated = pick(SURFACE_ELEVATED, dark)
    hover = pick(SURFACE_HOVER, dark)
    text = pick(TEXT_PRIMARY, dark)
    muted = pick(TEXT_MUTED, dark)
    secondary = pick(TEXT_SECONDARY, dark)
    accent = pick(SYSTEM_TEAL, dark)
    border = "#334155" if dark else "#E2E8F0"

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
    QGroupBox {{
        background-color: {card};
        border: 1px solid {border};
        border-radius: 10px;
        margin-top: 14px;
        padding-top: 16px;
        padding-bottom: 12px;
        padding-left: 12px;
        padding-right: 12px;
        font-weight: bold;
        font-size: 12px;
        color: {accent};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding-left: 10px;
        padding-right: 10px;
        padding-top: 2px;
        color: {accent};
    }}
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
        background-color: {elevated};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 10px;
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
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {card};
        border: 1px solid {border};
        selection-background-color: {hover};
        selection-color: {accent};
        padding: 4px;
        outline: none;
    }}
    QPushButton {{
        background-color: {elevated};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 14px;
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
        background-color: {accent};
        color: #FFFFFF;
        border: 1px solid {accent};
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background-color: #0369A1;
        border-color: #0369A1;
    }}
    QCheckBox {{
        spacing: 8px;
        font-size: 12px;
        color: {text};
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {border};
        background-color: {elevated};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border-color: {accent};
        image: none;
    }}
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 6px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        min-height: 20px;
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
    """
