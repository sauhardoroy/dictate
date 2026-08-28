"""
material_theme.py — Material 3 Monochrome Design System for Dictate

This module is the single source of truth for color tokens, typography,
shape, elevation, and motion used across `onboarding.py`, `settings_dialog.py`,
and other standard Material UI screens in Dictate.
"""

from dataclasses import dataclass, field
from typing import Dict


# --------------------------------------------------------------------------
# 1. COLOR TOKENS
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Tokens:
    mode: str

    # Surfaces (tonal elevation ladder)
    surface_dim: str
    surface: str
    surface_bright: str
    surface_container_lowest: str
    surface_container_low: str
    surface_container: str
    surface_container_high: str
    surface_container_highest: str

    # Content
    on_surface: str
    on_surface_variant: str
    on_surface_muted: str

    # Structure
    outline: str
    outline_variant: str

    # "Primary" — monochrome high-contrast tone
    primary: str
    on_primary: str
    primary_container: str
    on_primary_container: str

    # Semantic (kept desaturated / grayscale-adjacent)
    success: str
    on_success: str
    error: str
    on_error: str

    # Overlay + shadow
    scrim: str
    shadow: str

    @staticmethod
    def dark() -> "Tokens":
        return Tokens(
            mode="dark",
            surface_dim="#0A0A0B",
            surface="#111113",
            surface_bright="#3A3A3D",
            surface_container_lowest="#08080A",
            surface_container_low="#161619",
            surface_container="#1C1C20",
            surface_container_high="#232327",
            surface_container_highest="#2E2E33",
            on_surface="#F2F1F4",
            on_surface_variant="#B9B8BF",
            on_surface_muted="#8A8990",
            outline="#3E3D43",
            outline_variant="#28282C",
            primary="#F2F1F4",
            on_primary="#141416",
            primary_container="#2E2E33",
            on_primary_container="#F2F1F4",
            success="#9FD6A8",
            on_success="#0F1F12",
            error="#E5A2A2",
            on_error="#2A0E0E",
            scrim="rgba(0, 0, 0, 0.55)",
            shadow="rgba(0, 0, 0, 0.45)",
        )

    @staticmethod
    def light() -> "Tokens":
        return Tokens(
            mode="light",
            surface_dim="#DEDEE1",
            surface="#F7F7F8",
            surface_bright="#FFFFFF",
            surface_container_lowest="#FFFFFF",
            surface_container_low="#F1F1F3",
            surface_container="#EAEAEC",
            surface_container_high="#E3E3E6",
            surface_container_highest="#DBDBDF",
            on_surface="#1B1B1E",
            on_surface_variant="#48474E",
            on_surface_muted="#77767D",
            outline="#C9C8CE",
            outline_variant="#DEDDE2",
            primary="#1B1B1E",
            on_primary="#FAFAFA",
            primary_container="#DBDBDF",
            on_primary_container="#1B1B1E",
            success="#2E6B3A",
            on_success="#FFFFFF",
            error="#8E3B3B",
            on_error="#FFFFFF",
            scrim="rgba(0, 0, 0, 0.32)",
            shadow="rgba(0, 0, 0, 0.16)",
        )


# --------------------------------------------------------------------------
# 2. TYPOGRAPHY SCALE
# --------------------------------------------------------------------------

FONT_FAMILY = '"Segoe UI Variable Display", "Segoe UI", "Inter", sans-serif'

TYPE_SCALE: Dict[str, Dict] = {
    "display":    {"size": 30, "weight": 600, "line": 38, "tracking": -0.2},
    "headline":   {"size": 22, "weight": 600, "line": 28, "tracking": -0.1},
    "title":      {"size": 16, "weight": 600, "line": 22, "tracking": 0.0},
    "title_sm":   {"size": 14, "weight": 600, "line": 20, "tracking": 0.0},
    "body":       {"size": 13, "weight": 400, "line": 20, "tracking": 0.1},
    "body_sm":    {"size": 12, "weight": 400, "line": 18, "tracking": 0.15},
    "label":      {"size": 12, "weight": 600, "line": 16, "tracking": 0.4},
    "label_caps": {"size": 11, "weight": 700, "line": 14, "tracking": 1.2},
}


# --------------------------------------------------------------------------
# 3. SHAPE & ELEVATION
# --------------------------------------------------------------------------

class Shape:
    NONE = 0
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    FULL = 999  # pill / fully-rounded


class Elevation:
    LEVEL_0 = "surface"
    LEVEL_1 = "surface_container_low"
    LEVEL_2 = "surface_container"
    LEVEL_3 = "surface_container_high"
    LEVEL_4 = "surface_container_highest"


MOTION = {
    "fast": 120,      # ms — hover/press feedback
    "standard": 220,  # ms — tab switches, step transitions
    "slow": 320,      # ms — dialog transitions
}


# --------------------------------------------------------------------------
# 4. QSS BUILDER
# --------------------------------------------------------------------------

def build_qss(t: Tokens) -> str:
    f = FONT_FAMILY
    ts = TYPE_SCALE

    return f"""
    /* ============ GLOBAL ============ */
    * {{
        font-family: {f};
        outline: none;
    }}

    QWidget {{
        background: transparent;
        color: {t.on_surface};
    }}

    QWidget#root, QDialog {{
        background: {t.surface};
        color: {t.on_surface};
    }}

    QScrollArea, QAbstractScrollArea::viewport {{
        background: transparent;
        border: none;
    }}

    QLabel {{
        color: {t.on_surface};
        background: transparent;
    }}

    QLabel[role="headline"] {{
        font-size: {ts['headline']['size']}px;
        font-weight: {ts['headline']['weight']};
    }}
    QLabel[role="title"] {{
        font-size: {ts['title']['size']}px;
        font-weight: {ts['title']['weight']};
    }}
    QLabel[role="body"] {{
        font-size: {ts['body']['size']}px;
        color: {t.on_surface_variant};
    }}
    QLabel[role="body_sm"] {{
        font-size: {ts['body_sm']['size']}px;
        color: {t.on_surface_muted};
    }}
    QLabel[role="label_caps"] {{
        font-size: {ts['label_caps']['size']}px;
        font-weight: {ts['label_caps']['weight']};
        color: {t.on_surface_muted};
    }}

    /* ============ CARDS / PLATTERS ============ */
    QFrame[role="card"] {{
        background: {t.surface_container_low};
        border: 1px solid {t.outline_variant};
        border-radius: {Shape.LG}px;
    }}
    QFrame[role="row"] {{
        background: transparent;
        border: none;
    }}
    QFrame[role="hairline"] {{
        background: {t.outline_variant};
        max-height: 1px;
        min-height: 1px;
        border: none;
    }}

    /* ============ BUTTONS ============ */
    QPushButton {{
        border-radius: {Shape.FULL}px;
        padding: 8px 20px;
        font-size: {ts['title_sm']['size']}px;
        font-weight: {ts['title_sm']['weight']};
        border: 1px solid transparent;
    }}

    QPushButton[variant="primary"], QPushButton#primaryButton {{
        background: {t.primary};
        color: {t.on_primary};
    }}
    QPushButton[variant="primary"]:hover, QPushButton#primaryButton:hover {{
        background: {t.on_surface_variant};
    }}
    QPushButton[variant="primary"]:pressed, QPushButton#primaryButton:pressed {{
        background: {t.on_surface_muted};
    }}
    QPushButton[variant="primary"]:disabled, QPushButton#primaryButton:disabled {{
        background: {t.surface_container_high};
        color: {t.on_surface_muted};
    }}

    QPushButton[variant="secondary"] {{
        background: transparent;
        color: {t.on_surface};
        border: 1px solid {t.outline};
    }}
    QPushButton[variant="secondary"]:hover {{
        background: {t.surface_container_high};
    }}
    QPushButton[variant="secondary"]:pressed {{
        background: {t.surface_container_highest};
    }}

    QPushButton[variant="text"] {{
        background: transparent;
        color: {t.on_surface_variant};
        border: none;
        padding: 8px 12px;
    }}
    QPushButton[variant="text"]:hover {{
        color: {t.on_surface};
    }}

    QPushButton[variant="key-capture"] {{
        background: {t.surface_container_high};
        color: {t.on_surface};
        border: 1px solid {t.outline};
        border-radius: {Shape.SM}px;
        padding: 6px 14px;
        font-family: "Cascadia Code", "Consolas", monospace;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }}
    QPushButton[variant="key-capture"]:hover {{
        border-color: {t.on_surface_variant};
    }}
    QPushButton[variant="key-capture"][recording="true"] {{
        background: {t.surface_container_highest};
        border: 1px solid {t.on_surface};
        color: {t.on_surface};
    }}

    /* ============ NAV RAIL (onboarding) ============ */
    QWidget#navRail {{
        background: {t.surface_container_lowest};
        border-right: 1px solid {t.outline_variant};
    }}

    QPushButton[role="navstep"] {{
        text-align: left;
        border-radius: {Shape.MD}px;
        padding: 10px 12px;
        font-size: {ts['body']['size']}px;
        font-weight: 500;
        color: {t.on_surface_muted};
        background: transparent;
        border: none;
    }}
    QPushButton[role="navstep"][state="active"] {{
        color: {t.on_surface};
        background: {t.surface_container_high};
        font-weight: 600;
    }}
    QPushButton[role="navstep"][state="done"] {{
        color: {t.on_surface_variant};
    }}
    QPushButton[role="navstep"]:hover {{
        background: {t.surface_container};
    }}

    /* ============ TABS (settings) ============ */
    QWidget#segmentedBar {{
        background: {t.surface_container_low};
        border: 1px solid {t.outline_variant};
        border-radius: {Shape.FULL}px;
    }}
    QPushButton[role="segment"] {{
        background: transparent;
        color: {t.on_surface_variant};
        border: none;
        border-radius: {Shape.FULL}px;
        padding: 8px 18px;
        font-size: {ts['label']['size']}px;
        font-weight: 600;
    }}
    QPushButton[role="segment"][state="active"] {{
        background: {t.primary};
        color: {t.on_primary};
    }}
    QPushButton[role="segment"]:hover:!checked {{
        color: {t.on_surface};
    }}

    /* ============ INPUTS ============ */
    QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {{
        background: {t.surface_container_high};
        border: 1px solid {t.outline};
        border-radius: {Shape.SM}px;
        padding: 7px 10px;
        color: {t.on_surface};
        font-size: {ts['body']['size']}px;
        selection-background-color: {t.on_surface_variant};
    }}
    QComboBox:hover, QLineEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover {{
        border-color: {t.on_surface_variant};
    }}
    QComboBox:focus, QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
        border: 1.5px solid {t.on_surface};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background: {t.surface_container_high};
        border: 1px solid {t.outline};
        border-radius: {Shape.SM}px;
        selection-background-color: {t.surface_container_highest};
        color: {t.on_surface};
        outline: none;
        padding: 4px;
    }}

    /* ============ CHECKBOX ============ */
    QCheckBox {{
        color: {t.on_surface};
        font-size: {ts['body']['size']}px;
        spacing: 10px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: {Shape.XS}px;
        border: 1.5px solid {t.outline};
        background-color: {t.surface_container_high};
    }}
    QCheckBox::indicator:hover {{
        border-color: {t.on_surface_variant};
    }}
    QCheckBox::indicator:checked {{
        background-color: {t.primary};
        border: 1.5px solid {t.primary};
        image: none;
    }}
    QCheckBox::indicator:checked:hover {{
        background-color: {t.on_surface_variant};
        border-color: {t.on_surface_variant};
    }}

    /* ============ SCROLLBAR ============ */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t.outline};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t.on_surface_muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* ============ STATUS PILL ============ */
    QLabel[role="pill"] {{
        background: {t.surface_container_high};
        color: {t.on_surface_variant};
        border: 1px solid {t.outline_variant};
        border-radius: {Shape.FULL}px;
        padding: 4px 12px;
        font-size: {ts['label']['size']}px;
        font-weight: 600;
    }}
    QLabel[role="pill"][tone="success"] {{
        color: {t.on_surface};
        border-color: {t.on_surface_muted};
    }}

    /* ============ TOOLTIP ============ */
    QToolTip {{
        background: {t.surface_container_highest};
        color: {t.on_surface};
        border: 1px solid {t.outline};
        padding: 6px 8px;
        border-radius: {Shape.XS}px;
    }}
    """


def elevation_color(t: Tokens, level: str) -> str:
    """Resolve an Elevation.LEVEL_* constant to a concrete hex on `t`."""
    return getattr(t, level)
