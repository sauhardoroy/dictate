"""Frosted Glass Style Onboarding Wizard for Dictate.

Implements a modern, frameless, frosted acrylic aesthetic with:
- Multi-layer canvas with ambient gradient bleed-through & backdrop diffusion
- Procedural film grain noise overlay for authentic matte frosted texture
- 1px top-lit inner rim hairlines and diffuse multi-layer drop shadows
- Left sidebar rail with diffuse circular active indicators
- Modular asset slot system with SVG/PNG loader & procedural vector fallbacks
- Hero mic orb with radiating concentric glow rings and live horizontal waveform
- Status strip with iOS-style toggle and frosted context bar chips
- Tactile glass buttons with 0.97x press physics
"""

import math
import os
import sys
import numpy as np

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui import theme

# ---------------------------------------------------------------------------
# 1. DESIGN TOKENS & MATERIAL CONSTANTS
# ---------------------------------------------------------------------------
# Frosted Palette & Tints
ACCENT_BLUE = QColor("#38BDF8")      # Sky blue highlight
ACCENT_CYAN = QColor("#0284C7")      # Sapphire cyan
ACCENT_PURPLE = QColor("#818CF8")    # Indigo / Violet
ACCENT_PINK = QColor("#E11D48")      # Ruby rose
ACCENT_GREEN = QColor("#10B981")     # Emerald mint
ACCENT_AMBER = QColor("#F59E0B")     # Warm glow

TEXT_PRIMARY = QColor("#F8FAFC")     # High-contrast crisp white
TEXT_SECONDARY = QColor("#94A3B8")   # Diffused cool slate
TEXT_MUTED = QColor("#64748B")       # Subtle caption text

GLASS_BG_LIGHT = QColor(255, 255, 255, 130)
GLASS_BG_DARK = QColor(15, 23, 42, 160)
GLASS_PANEL_BG = QColor(10, 15, 30, 190)
GLASS_RAIL_BG = QColor(6, 10, 20, 210)
GLASS_SUBPANEL_BG = QColor(8, 12, 24, 220)

BORDER_RIM_TOP = QColor(255, 255, 255, 55)
BORDER_RIM_BOTTOM = QColor(255, 255, 255, 12)
BORDER_SUBTLE = QColor(255, 255, 255, 25)

WINDOW_WIDTH = 780
WINDOW_HEIGHT = 520
SHADOW_MARGIN = 20

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "onboarding")

# ---------------------------------------------------------------------------
# 2. PROCEDURAL FILM GRAIN NOISE GENERATOR (ANTI-BANDING & ACRYLIC TEXTURE)
# ---------------------------------------------------------------------------
_CACHED_NOISE_PIXMAP: QPixmap | None = None


def get_noise_pixmap(width: int = 256, height: int = 256, opacity: float = 0.03) -> QPixmap:
    """Generate or retrieve a cached monochrome film grain noise texture."""
    global _CACHED_NOISE_PIXMAP
    if _CACHED_NOISE_PIXMAP is not None:
        return _CACHED_NOISE_PIXMAP

    np.random.seed(42)
    noise = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    alpha = int(opacity * 255)

    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[:, :, 0] = noise
    rgba[:, :, 1] = noise
    rgba[:, :, 2] = noise
    rgba[:, :, 3] = alpha

    img = QImage(rgba.data, width, height, width * 4, QImage.Format.Format_RGBA8888)
    _CACHED_NOISE_PIXMAP = QPixmap.fromImage(img.copy())
    return _CACHED_NOISE_PIXMAP


# ---------------------------------------------------------------------------
# 3. MODULAR ASSET COMPONENT WITH VECTOR FALLBACK RENDERING
# ---------------------------------------------------------------------------
class GlassBadge(QWidget):
    """Universal modular asset slot component.
    
    Dynamically loads SVG/PNG assets from assets/onboarding/<slot_name>
    or gracefully falls back to procedural QPainterPath vector glyphs.
    """

    def __init__(
        self,
        slot_name: str,
        fallback_glyph: str = "mic",
        accent_color: QColor | None = None,
        size: int = 64,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.slot_name = slot_name
        self.fallback_glyph = fallback_glyph
        self.accent_color = accent_color or ACCENT_BLUE
        self._size = size
        self.setFixedSize(size, size)

        self._svg_renderer: QSvgRenderer | None = None
        self._pixmap: QPixmap | None = None
        self._load_asset()

    def _load_asset(self):
        """Try loading SVG/PNG from asset directories."""
        candidates = [
            os.path.join(ASSETS_DIR, f"{self.slot_name}.svg"),
            os.path.join(ASSETS_DIR, f"{self.slot_name}.png"),
            os.path.join(ASSETS_DIR, f"{self.fallback_glyph}.svg"),
            os.path.join(ASSETS_DIR, f"{self.fallback_glyph}.png"),
        ]
        for path in candidates:
            if os.path.exists(path):
                if path.endswith(".svg"):
                    self._svg_renderer = QSvgRenderer(path)
                    return
                elif path.endswith(".png"):
                    self._pixmap = QPixmap(path)
                    return

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        rect = QRectF(0, 0, w, h)

        # Ambient glass badge backing
        p.setPen(Qt.PenStyle.NoPen)
        glow_grad = QRadialGradient(w / 2, h / 2, w / 2)
        glow_grad.setColorAt(0.0, QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 50))
        glow_grad.setColorAt(0.7, QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 15))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow_grad))
        p.drawEllipse(rect)

        # If asset exists, render it
        if self._svg_renderer and self._svg_renderer.isValid():
            pad = w * 0.1
            target = QRectF(pad, pad, w - pad * 2, h - pad * 2)
            self._svg_renderer.render(p, target)
            p.end()
            return
        elif self._pixmap and not self._pixmap.isNull():
            pad = int(w * 0.1)
            target = QRect(pad, pad, w - pad * 2, h - pad * 2)
            p.drawPixmap(target, self._pixmap.scaled(target.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            p.end()
            return

        # Fallback Procedural Vector Glyph
        self._paint_procedural_fallback(p, w, h)
        p.end()

    def _paint_procedural_fallback(self, p: QPainter, w: int, h: int):
        glyph = self.fallback_glyph.lower()
        cx, cy = w / 2, h / 2

        # Outer rim
        rim_pen = QPen(QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 180), 1.5)
        p.setPen(rim_pen)
        p.setBrush(QBrush(QColor(15, 23, 42, 180)))
        p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), w * 0.25, h * 0.25)

        pen = QPen(self.accent_color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        if "mic" in glyph:
            # Microphone capsule & stand
            p.setBrush(QBrush(QColor(255, 255, 255, 220)))
            p.drawRoundedRect(QRectF(cx - w * 0.12, cy - h * 0.25, w * 0.24, h * 0.36), w * 0.1, w * 0.1)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx - w * 0.22, cy - h * 0.18, w * 0.44, h * 0.36), 0, -180 * 16)
            p.drawLine(QPointF(cx, cy + h * 0.18), QPointF(cx, cy + h * 0.30))
            p.drawLine(QPointF(cx - w * 0.15, cy + h * 0.30), QPointF(cx + w * 0.15, cy + h * 0.30))

        elif "key" in glyph or "step1" in glyph:
            # Keyboard icon
            p.drawRoundedRect(QRectF(cx - w * 0.35, cy - h * 0.22, w * 0.7, h * 0.44), 6, 6)
            p.drawLine(QPointF(cx - w * 0.2, cy - h * 0.08), QPointF(cx - w * 0.1, cy - h * 0.08))
            p.drawLine(QPointF(cx, cy - h * 0.08), QPointF(cx + w * 0.1, cy - h * 0.08))
            p.drawLine(QPointF(cx - w * 0.22, cy + h * 0.08), QPointF(cx + w * 0.22, cy + h * 0.08))

        elif "speak" in glyph or "wave" in glyph or "step2" in glyph:
            # Audio soundwave / speech
            p.drawLine(QPointF(cx - w * 0.25, cy), QPointF(cx - w * 0.25, cy))
            p.drawLine(QPointF(cx - w * 0.12, cy - h * 0.2), QPointF(cx - w * 0.12, cy + h * 0.2))
            p.drawLine(QPointF(cx, cy - h * 0.3), QPointF(cx, cy + h * 0.3))
            p.drawLine(QPointF(cx + w * 0.12, cy - h * 0.2), QPointF(cx + w * 0.12, cy + h * 0.2))
            p.drawLine(QPointF(cx + w * 0.25, cy), QPointF(cx + w * 0.25, cy))

        elif "check" in glyph or "ready" in glyph or "step3" in glyph or "paste" in glyph:
            # Checkmark with sparkles
            path = QPainterPath()
            path.moveTo(cx - w * 0.22, cy)
            path.lineTo(cx - w * 0.05, cy + h * 0.18)
            path.lineTo(cx + w * 0.25, cy - h * 0.18)
            p.drawPath(path)

        elif "pill" in glyph:
            # Floating pill capsule
            p.drawRoundedRect(QRectF(cx - w * 0.35, cy - h * 0.18, w * 0.7, h * 0.36), h * 0.18, h * 0.18)
            p.setBrush(QBrush(TEXT_PRIMARY))
            p.drawEllipse(QRectF(cx - w * 0.22, cy - h * 0.08, w * 0.16, h * 0.16))

        elif "setting" in glyph:
            # Cogwheel
            p.drawEllipse(QRectF(cx - w * 0.22, cy - h * 0.22, w * 0.44, h * 0.44))
            p.drawEllipse(QRectF(cx - w * 0.08, cy - h * 0.08, w * 0.16, h * 0.16))

        elif "model" in glyph or "cpu" in glyph:
            # Neural processor chip
            p.drawRoundedRect(QRectF(cx - w * 0.24, cy - h * 0.24, w * 0.48, h * 0.48), 4, 4)
            p.drawRect(QRectF(cx - w * 0.12, cy - h * 0.12, w * 0.24, h * 0.24))

        else:
            # Default star/orb
            p.drawEllipse(QRectF(cx - w * 0.2, cy - h * 0.2, w * 0.4, h * 0.4))


FrostedIcon = GlassBadge


# ---------------------------------------------------------------------------
# 4. TACTILE GLASS BUTTON WITH 0.97X PRESS PHYSICS
# ---------------------------------------------------------------------------
class GlassButton(QPushButton):
    """Tactile frosted glass button with hover glow & press scale physics."""

    def __init__(
        self,
        text: str = "",
        primary: bool = False,
        accent_color: QColor | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(text, parent)
        self.primary = primary
        self.accent_color = accent_color or ACCENT_CYAN
        self._is_pressed = False
        self._is_hovered = False
        self._scale = 1.0

        self.setFixedHeight(38)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.valueChanged.connect(self._on_anim_scale)

    def _on_anim_scale(self, val):
        self._scale = float(val)
        self.update()

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            self._anim.stop()
            self._anim.setStartValue(self._scale)
            self._anim.setEndValue(0.97)
            self._anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = False
            self._anim.stop()
            self._anim.setStartValue(self._scale)
            self._anim.setEndValue(1.0)
            self._anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        # Apply tactile scale transform centered on button
        p.save()
        p.translate(cx, cy)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)

        rect = QRectF(1, 1, w - 2, h - 2)
        radius = 10.0

        if self.primary:
            # Primary gradient fill
            grad = QLinearGradient(0, 0, w, h)
            if self._is_hovered:
                grad.setColorAt(0.0, QColor("#0284C7"))
                grad.setColorAt(1.0, QColor("#38BDF8"))
            else:
                grad.setColorAt(0.0, QColor("#0369A1"))
                grad.setColorAt(1.0, QColor("#0284C7"))
            p.setBrush(QBrush(grad))

            # Rim highlight
            p.setPen(QPen(QColor(255, 255, 255, 80), 1.0))
            p.drawRoundedRect(rect, radius, radius)
            text_color = TEXT_PRIMARY
        else:
            # Secondary frosted fill
            if self._is_hovered:
                p.setBrush(QBrush(QColor(255, 255, 255, 28)))
                p.setPen(QPen(QColor(255, 255, 255, 50), 1.0))
            else:
                p.setBrush(QBrush(QColor(255, 255, 255, 14)))
                p.setPen(QPen(QColor(255, 255, 255, 25), 1.0))
            p.drawRoundedRect(rect, radius, radius)
            text_color = TEXT_PRIMARY if self._is_hovered else TEXT_SECONDARY

        # Button Text
        p.setPen(text_color)
        p.setFont(self.font())
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        p.restore()
        p.end()


# ---------------------------------------------------------------------------
# 5. FROSTED GLASS CONTAINER PANEL
# ---------------------------------------------------------------------------
class GlassPanel(QFrame):
    """Frosted acrylic container panel with ambient bleed-through and 1px top-lit inner rim highlight."""

    def __init__(
        self,
        radius: float = 16.0,
        bg_color: QColor | None = None,
        is_outer_shell: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.radius = radius
        self.bg_color = bg_color or GLASS_PANEL_BG
        self.is_outer_shell = is_outer_shell
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        rounded_path = self._rounded_path(rect, self.radius)

        p.setClipPath(rounded_path)

        if self.is_outer_shell:
            # 1. Base Canvas Ambient Multi-Stop Gradient Bleed-Through
            # Upper cool sapphire/indigo glow
            upper_grad = QRadialGradient(w * 0.25, 0, w * 0.7)
            upper_grad.setColorAt(0.0, QColor("#1E3A8A"))
            upper_grad.setColorAt(0.5, QColor("#1E1B4B"))
            upper_grad.setColorAt(1.0, QColor("#090D16"))
            p.setBrush(QBrush(upper_grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(0, 0, w, h)

            # Lower warm magenta / amber bleed
            lower_grad = QRadialGradient(w * 0.85, h * 0.9, w * 0.55)
            lower_grad.setColorAt(0.0, QColor(190, 24, 93, 100))
            lower_grad.setColorAt(0.6, QColor(76, 29, 149, 70))
            lower_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(lower_grad))
            p.drawRect(0, 0, w, h)

        # 2. Material Tinting (Diffuse Frosted Layer)
        p.setBrush(QBrush(self.bg_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, w, h)

        # 3. Procedural Film Grain Noise Texture (Acrylic Matte Finish)
        noise = get_noise_pixmap()
        p.drawTiledPixmap(QRect(0, 0, w, h), noise)

        # 4. 1px Top-Lit Inner Rim Highlight (Simulates top-down ambient light)
        rim_grad = QLinearGradient(0, 0, 0, h)
        rim_grad.setColorAt(0.0, BORDER_RIM_TOP)
        rim_grad.setColorAt(0.2, BORDER_SUBTLE)
        rim_grad.setColorAt(1.0, BORDER_RIM_BOTTOM)

        p.setPen(QPen(rim_grad, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, self.radius, self.radius)
        p.end()

    def _rounded_path(self, rect: QRectF, radius: float) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path


# ---------------------------------------------------------------------------
# 6. FROSTED PROGRESS BAR (ANIMATED SHIMMER)
# ---------------------------------------------------------------------------
class GlassProgressBar(QWidget):
    """Frosted progress bar with animated shimmering light sweep."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._value = 0
        self._shimmer = 0.0
        self.setFixedHeight(12)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(30)

    def _on_tick(self):
        self._shimmer = (self._shimmer + 0.03) % 1.0
        self.update()

    def setValue(self, val: int):
        self._value = max(0, min(100, val))
        self.update()

    def value(self) -> int:
        return self._value

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        radius = h / 2.0

        # Background track
        p.setBrush(QBrush(QColor(15, 23, 42, 200)))
        p.setPen(QPen(BORDER_SUBTLE, 1.0))
        p.drawRoundedRect(rect, radius, radius)

        # Progress fill
        if self._value > 0:
            fill_w = (w - 2.0) * (self._value / 100.0)
            fill_rect = QRectF(1.0, 1.0, max(fill_w, h - 2.0), h - 2.0)

            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, ACCENT_CYAN)
            grad.setColorAt(0.7, ACCENT_BLUE)
            grad.setColorAt(1.0, ACCENT_PURPLE)

            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(fill_rect, radius - 1.0, radius - 1.0)

            # Animated shimmer highlight
            shimmer_x = fill_w * self._shimmer
            shim_grad = QLinearGradient(shimmer_x - 20, 0, shimmer_x + 20, 0)
            shim_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            shim_grad.setColorAt(0.5, QColor(255, 255, 255, 140))
            shim_grad.setColorAt(1.0, QColor(255, 255, 255, 0))

            p.setBrush(QBrush(shim_grad))
            p.setClipRect(fill_rect)
            p.drawRect(fill_rect)
        p.end()


# ---------------------------------------------------------------------------
# 7. SIDEBAR RAIL (FROSTED GLASS NAVIGATION)
# ---------------------------------------------------------------------------
class SidebarRail(QWidget):
    """Narrow vertical sidebar with deep frosted glass material and soft diffuse indicator."""

    item_selected = pyqtSignal(int)

    NAV_ITEMS = [
        ("●", "REC", "Welcome"),
        ("⚡", "Flow", "How It Works"),
        ("💡", "Tips", "Helpful Tips"),
        ("⬇", "Model", "Offline AI"),
        ("⚙", "Ready", "Ready to Dictate"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_index = 0
        self.setFixedWidth(145)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_current_index(self, index: int):
        if self._current_index != index:
            self._current_index = max(0, min(len(self.NAV_ITEMS) - 1, index))
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item_h = 44
            top_pad = 20
            y = event.pos().y() - top_pad
            if y >= 0:
                idx = y // item_h
                if 0 <= idx < len(self.NAV_ITEMS):
                    self.set_current_index(idx)
                    self.item_selected.emit(idx)
        super().mousePressEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        radius = 16.0

        # Deep Frosted Glass Background
        p.setBrush(QBrush(GLASS_RAIL_BG))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, radius, radius)

        # 1px rim highlight
        rim = QLinearGradient(0, 0, 0, h)
        rim.setColorAt(0.0, BORDER_RIM_TOP)
        rim.setColorAt(1.0, BORDER_RIM_BOTTOM)
        p.setPen(QPen(rim, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, radius, radius)

        # Render nav rows
        top_pad = 20
        item_h = 44

        for i, (symbol, label, _) in enumerate(self.NAV_ITEMS):
            y = top_pad + i * item_h
            is_active = (i == self._current_index)

            if is_active:
                # Soft diffuse filled circular indicator
                glow_center = QPointF(24, y + item_h / 2.0)
                glow = QRadialGradient(glow_center, 18)
                glow.setColorAt(0.0, QColor(56, 189, 248, 180))
                glow.setColorAt(0.4, QColor(99, 102, 241, 90))
                glow.setColorAt(1.0, QColor(0, 0, 0, 0))

                p.setBrush(QBrush(glow))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(glow_center, 16, 16)

                # Solid center pip
                p.setBrush(QBrush(ACCENT_BLUE))
                p.drawEllipse(glow_center, 4, 4)

                # Text in crisp white
                p.setPen(TEXT_PRIMARY)
                p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            else:
                # Inactive symbol
                p.setPen(TEXT_MUTED)
                p.setFont(QFont("Segoe UI", 9))
                p.drawText(QRectF(16, y, 16, item_h), Qt.AlignmentFlag.AlignCenter, symbol)

                # Inactive label
                p.setPen(TEXT_SECONDARY)
                p.setFont(QFont("Segoe UI", 9))

            p.drawText(QRectF(44, y, w - 50, item_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
        p.end()


# ---------------------------------------------------------------------------
# 8. IOS-STYLE TOGGLE SWITCH
# ---------------------------------------------------------------------------
class IOSToggle(QWidget):
    """iOS-style smooth animated toggle switch tinted blue when active."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._checked = checked
        self._thumb_x = 1.0 if checked else 0.0
        self.setFixedSize(38, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.valueChanged.connect(self._on_anim_thumb)

    def _on_anim_thumb(self, val):
        self._thumb_x = float(val)
        self.update()

    def setChecked(self, val: bool):
        if self._checked != val:
            self._checked = val
            self._anim.stop()
            self._anim.setStartValue(self._thumb_x)
            self._anim.setEndValue(1.0 if val else 0.0)
            self._anim.start()
            self.toggled.emit(val)

    def isChecked(self) -> bool:
        return self._checked

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2.0

        # Background capsule
        if self._checked:
            bg = QColor("#0284C7")
        else:
            bg = QColor(51, 65, 85, 180)

        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)

        # Sliding White Thumb
        thumb_diam = h - 6
        thumb_min_x = 3
        thumb_max_x = w - thumb_diam - 3
        cur_x = thumb_min_x + (thumb_max_x - thumb_min_x) * self._thumb_x

        p.setBrush(QBrush(TEXT_PRIMARY))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cur_x, 3, thumb_diam, thumb_diam))
        p.end()


# ---------------------------------------------------------------------------
# 9. HERO CONTROL & LIVE SUB-PANEL (WAVEFORM MIC ORB + STATUS STRIP)
# ---------------------------------------------------------------------------
class WaveformMicOrb(QWidget):
    """Circular matte glass hero orb with live horizontal waveform & concentric glow rings."""

    def __init__(self, model_id: str = "Parakeet TDT 0.6B", parent: QWidget | None = None):
        super().__init__(parent)
        self.model_id = model_id
        self.setFixedHeight(180)
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_wave_tick)
        self._timer.start(30)

    def _on_wave_tick(self):
        self._phase += 0.08
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0 - 10

        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        radius = 14.0

        # Darker Frosted Glass Sub-Panel
        p.setBrush(QBrush(GLASS_SUBPANEL_BG))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, radius, radius)

        # 1px rim highlight
        rim = QLinearGradient(0, 0, 0, h)
        rim.setColorAt(0.0, BORDER_RIM_TOP)
        rim.setColorAt(1.0, BORDER_RIM_BOTTOM)
        p.setPen(QPen(rim, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, radius, radius)

        # 1. Concentric radiating glow rings
        for r, alpha in [(62, 25), (48, 50), (36, 90)]:
            ring_grad = QRadialGradient(cx, cy, r)
            ring_grad.setColorAt(0.0, QColor(56, 189, 248, alpha))
            ring_grad.setColorAt(0.8, QColor(99, 102, 241, alpha // 2))
            ring_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(ring_grad))
            p.setPen(QPen(QColor(56, 189, 248, alpha), 1.0))
            p.drawEllipse(QPointF(cx, cy), r, r)

        # 2. Live horizontal waveform (soft blue bars taller in center, fading at edges)
        num_bars = 23
        bar_w = 3.5
        spacing = 9.0
        total_w = num_bars * spacing
        start_x = cx - total_w / 2.0

        for i in range(num_bars):
            bx = start_x + i * spacing
            dist_from_center = abs(i - (num_bars // 2)) / (num_bars // 2)
            envelope = math.exp(-3.0 * dist_from_center * dist_from_center)
            wave_h = 10 + 35 * envelope * (0.6 + 0.4 * math.sin(self._phase + i * 0.4))

            # Fade edge bars
            alpha = int(240 * envelope)
            bar_color = QColor(56, 189, 248, max(40, alpha))

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(bar_color))
            p.drawRoundedRect(QRectF(bx, cy - wave_h / 2.0, bar_w, wave_h), 1.5, 1.5)

        # 3. Centered Matte Glass Orb
        orb_r = 26
        orb_grad = QRadialGradient(cx, cy, orb_r)
        orb_grad.setColorAt(0.0, QColor(2, 132, 199, 240))
        orb_grad.setColorAt(0.8, QColor(30, 27, 75, 220))
        orb_grad.setColorAt(1.0, QColor(15, 23, 42, 255))
        p.setBrush(QBrush(orb_grad))
        p.setPen(QPen(QColor(255, 255, 255, 120), 1.5))
        p.drawEllipse(QPointF(cx, cy), orb_r, orb_r)

        # Center White Microphone Glyph
        p.setPen(QPen(TEXT_PRIMARY, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QBrush(TEXT_PRIMARY))
        p.drawRoundedRect(QRectF(cx - 4, cy - 10, 8, 12), 4, 4)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 7, cy - 6, 14, 12), 0, -180 * 16)
        p.drawLine(QPointF(cx, cy + 6), QPointF(cx, cy + 11))
        p.drawLine(QPointF(cx - 4, cy + 11), QPointF(cx + 4, cy + 11))

        # 4. Small Tag Pill (Top-Right)
        tag_rect = QRectF(w - 110, 12, 96, 20)
        p.setBrush(QBrush(QColor(255, 255, 255, 18)))
        p.setPen(QPen(BORDER_SUBTLE, 1.0))
        p.drawRoundedRect(tag_rect, 10, 10)
        p.setPen(TEXT_SECONDARY)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, "Frosted Engine")

        # 5. Status Strip Text (Bottom-Left)
        p.setPen(TEXT_MUTED)
        p.setFont(QFont("Segoe UI", 8))
        status_text = f"Listening  |  Input: Internal Mic  |  Local Model: {self.model_id.replace('-', ' ').title()}"
        p.drawText(QRectF(16, h - 28, w - 160, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, status_text)
        p.end()


# ---------------------------------------------------------------------------
# 10. STORYBOARD PAGES IMPLEMENTATION
# ---------------------------------------------------------------------------
def _create_welcome_page() -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(32, 24, 32, 24)
    layout.setSpacing(14)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    layout.addStretch()

    # Modular Asset Slot: welcome_hero
    badge = GlassBadge("welcome_hero", "mic", ACCENT_BLUE, size=72)
    layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignCenter)

    # Heading
    h1 = QLabel("Welcome to Dictate")
    h1.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
    h1.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
    h1.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(h1)

    # One line copy
    body = QLabel("Your private, fast, offline voice typing assistant.\nSpeak naturally anywhere and your speech appears instantly.")
    body.setFont(QFont("Segoe UI", 10))
    body.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; line-height: 1.4;")
    body.setAlignment(Qt.AlignmentFlag.AlignCenter)
    body.setWordWrap(True)
    layout.addWidget(body)

    # Frosted Pill Badge: 100% Offline
    offline_pill = QLabel("🔒 100% Offline • Zero Telemetry • Local Inference")
    offline_pill.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    offline_pill.setStyleSheet(f"""
        color: {ACCENT_GREEN.name()};
        background-color: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 12px;
        padding: 5px 14px;
    """)
    offline_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(offline_pill, 0, Qt.AlignmentFlag.AlignCenter)

    layout.addStretch()
    return page


def _create_how_it_works_page(trigger_key: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 16, 24, 16)
    layout.setSpacing(14)

    h1 = QLabel("How It Works")
    h1.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    h1.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
    h1.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(h1)

    # 3-step horizontal flow with connecting frosted threads
    cards_row = QHBoxLayout()
    cards_row.setSpacing(12)

    steps_data = [
        ("step1_icon", "step1", ACCENT_BLUE, "STEP 1", f"Hold [{trigger_key.upper()}]", "Press & hold your hotkey to start speaking"),
        ("step2_icon", "step2", ACCENT_PINK, "STEP 2", "Speak Naturally", "Talk naturally — the floating pill visualizes sound"),
        ("step3_icon", "step3", ACCENT_GREEN, "STEP 3", "Text Pastes", "Your transcribed speech appears in your active app"),
    ]

    for slot, fallback, color, step_tag, title, desc in steps_data:
        card = GlassPanel(radius=12.0, bg_color=QColor(15, 23, 42, 170))
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 16, 14, 16)
        c_layout.setSpacing(8)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        b = GlassBadge(slot, fallback, color, size=48)
        c_layout.addWidget(b, 0, Qt.AlignmentFlag.AlignCenter)

        tag = QLabel(step_tag)
        tag.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        tag.setStyleSheet(f"color: {color.name()}; background: rgba(255,255,255,0.06); border-radius: 6px; padding: 2px 6px;")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(tag, 0, Qt.AlignmentFlag.AlignCenter)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        t.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(t)

        d = QLabel(desc)
        d.setFont(QFont("Segoe UI", 8))
        d.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setWordWrap(True)
        c_layout.addWidget(d)

        cards_row.addWidget(card, 1)

    layout.addLayout(cards_row)
    return page


def _create_tips_page() -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(28, 16, 28, 16)
    layout.setSpacing(10)

    h1 = QLabel("Helpful Tips")
    h1.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    h1.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
    layout.addWidget(h1)

    tips_data = [
        ("tips_icon_pill", "pill", ACCENT_BLUE, "Shape-Shifting Pill", "The floating indicator morphs into a microphone or waveform. Drag it anywhere."),
        ("tips_icon_settings", "setting", ACCENT_PURPLE, "Settings & History", "Right-click the pill or tray icon to open Settings or search your past dictations."),
        ("tips_icon_vad", "wave", ACCENT_GREEN, "Smart Auto-Stop", "Dictate automatically detects silence when you pause and finishes your sentence."),
        ("tips_icon_escape", "ready", ACCENT_PINK, "Instant Cancel", "Press Escape to cancel dictation at any moment without pasting text."),
    ]

    list_panel = GlassPanel(radius=12.0, bg_color=QColor(15, 23, 42, 170))
    p_layout = QVBoxLayout(list_panel)
    p_layout.setContentsMargins(16, 12, 16, 12)
    p_layout.setSpacing(10)

    for i, (slot, fallback, color, title, desc) in enumerate(tips_data):
        row = QHBoxLayout()
        row.setSpacing(12)

        badge = GlassBadge(slot, fallback, color, size=32)
        row.addWidget(badge)

        t_layout = QVBoxLayout()
        t_layout.setSpacing(1)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        t.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
        t_layout.addWidget(t)

        d = QLabel(desc)
        d.setFont(QFont("Segoe UI", 8))
        d.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        d.setWordWrap(True)
        t_layout.addWidget(d)

        row.addLayout(t_layout, 1)
        p_layout.addLayout(row)

        if i < len(tips_data) - 1:
            # Inset divider line
            div = QFrame()
            div.setFrameShape(QFrame.Shape.HLine)
            div.setStyleSheet("background: rgba(255, 255, 255, 0.08); max-height: 1px;")
            p_layout.addWidget(div)

    layout.addWidget(list_panel)
    return page


def _create_model_page(model_id: str) -> tuple[QWidget, GlassProgressBar]:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(32, 20, 32, 20)
    layout.setSpacing(12)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    layout.addStretch()

    # Modular slot: model_badge
    badge = GlassBadge("model_badge", "model", ACCENT_PURPLE, size=64)
    layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignCenter)

    h1 = QLabel("Offline Speech Model")
    h1.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    h1.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
    layout.addWidget(h1, 0, Qt.AlignmentFlag.AlignCenter)

    desc = QLabel("Preparing high-accuracy neural model for zero-latency local speech recognition.")
    desc.setFont(QFont("Segoe UI", 9))
    desc.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc, 0, Qt.AlignmentFlag.AlignCenter)

    # Frosted Progress Bar
    pbar = GlassProgressBar()
    pbar.setFixedWidth(360)
    layout.addWidget(pbar, 0, Qt.AlignmentFlag.AlignCenter)

    # Status Line
    status_lbl = QLabel(f"Preparing | Model: {model_id.replace('-', ' ').title()} | ~250MB")
    status_lbl.setFont(QFont("Segoe UI", 8))
    status_lbl.setStyleSheet(f"color: {TEXT_MUTED.name()};")
    status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(status_lbl, 0, Qt.AlignmentFlag.AlignCenter)

    layout.addStretch()
    return page, pbar


def _create_ready_page(trigger_key: str, model_id: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 10, 20, 10)
    layout.setSpacing(10)

    # Hero Control & Waveform Sub-Panel
    orb_panel = WaveformMicOrb(model_id=model_id)

    # iOS Toggle Container bottom-right in sub-panel
    sub_overlay = QHBoxLayout(orb_panel)
    sub_overlay.setContentsMargins(16, 12, 16, 12)
    sub_overlay.addStretch()

    toggle_box = QVBoxLayout()
    toggle_box.addStretch()
    t_row = QHBoxLayout()
    t_lbl = QLabel("AI Cleanup")
    t_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
    t_lbl.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
    toggle = IOSToggle(checked=True)
    t_row.addWidget(t_lbl)
    t_row.addWidget(toggle)
    toggle_box.addLayout(t_row)
    sub_overlay.addLayout(toggle_box)

    layout.addWidget(orb_panel)

    # Bottom Context Bar with Glass Chips
    ctx_bar = GlassPanel(radius=10.0, bg_color=QColor(15, 23, 42, 180))
    ctx_bar.setFixedHeight(40)
    c_layout = QHBoxLayout(ctx_bar)
    c_layout.setContentsMargins(10, 4, 10, 4)
    c_layout.setSpacing(6)

    chips = [
        "↺",
        "Correct: design → style?",
        "Format: List",
        "Add: Emoji",
    ]

    for chip in chips:
        btn = QPushButton(chip)
        btn.setFont(QFont("Segoe UI", 8))
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_PRIMARY.name()};
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.16);
            }}
        """)
        c_layout.addWidget(btn)

    c_layout.addStretch()

    ctx_lbl = QLabel("Context Bar")
    ctx_lbl.setFont(QFont("Segoe UI", 8))
    ctx_lbl.setStyleSheet(f"color: {TEXT_MUTED.name()};")
    c_layout.addWidget(ctx_lbl)

    layout.addWidget(ctx_bar)
    return page


# ---------------------------------------------------------------------------
# 11. MAIN ONBOARDING DIALOG
# ---------------------------------------------------------------------------
class OnboardingDialog(QDialog):
    """The master Frosted Glass Onboarding Wizard Dialog for Dictate."""

    _model_ready = pyqtSignal()

    def __init__(
        self,
        trigger_key: str = "ctrl+shift+p",
        model_id: str = "parakeet-tdt-0.6b-v3",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.trigger_key = trigger_key
        self.model_id = model_id
        self._drag_pos: QPoint | None = None

        # Frameless, translucent window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(WINDOW_WIDTH + SHADOW_MARGIN * 2, WINDOW_HEIGHT + SHADOW_MARGIN * 2)

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN)

        # Outer Glass Shell
        self.shell = GlassPanel(radius=20.0, bg_color=GLASS_BG_DARK, is_outer_shell=True)
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(14, 10, 14, 14)
        shell_layout.setSpacing(10)

        # 1. Subtle, Borderless Header Region
        header = QHBoxLayout()
        header.setContentsMargins(10, 4, 10, 0)

        # App title centered
        title_lbl = QLabel("Dictate  •  Voice Type")
        title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        title_lbl.setStyleSheet("color: #CBD5E1; letter-spacing: 0.5px;")
        header.addStretch()
        header.addWidget(title_lbl)
        header.addStretch()

        # Frameless Close Button
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFont(QFont("Segoe UI", 9))
        btn_close.setStyleSheet("""
            QPushButton {
                color: #64748B;
                background: transparent;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                color: #F8FAFC;
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)

        shell_layout.addLayout(header)

        # 2. Main Content Split: Left Sidebar Rail + Right Diffused Main Pane
        body_split = QHBoxLayout()
        body_split.setSpacing(12)

        # Left Rail
        self.sidebar = SidebarRail()
        self.sidebar.item_selected.connect(self._on_sidebar_select)
        body_split.addWidget(self.sidebar)

        # Right Main Pane (Large Diffused Glass Panel)
        self.main_pane = GlassPanel(radius=16.0, bg_color=GLASS_PANEL_BG)
        main_pane_layout = QVBoxLayout(self.main_pane)
        main_pane_layout.setContentsMargins(12, 12, 12, 12)
        main_pane_layout.setSpacing(0)

        self.stack = QStackedWidget()

        # Step 0: Welcome
        self.p_welcome = _create_welcome_page()
        self.stack.addWidget(self.p_welcome)

        # Step 1: How It Works
        self.p_how = _create_how_it_works_page(self.trigger_key)
        self.stack.addWidget(self.p_how)

        # Step 2: Tips
        self.p_tips = _create_tips_page()
        self.stack.addWidget(self.p_tips)

        # Step 3: Model Download
        self.p_model, self.pbar = _create_model_page(self.model_id)
        self.stack.addWidget(self.p_model)

        # Step 4: Ready
        self.p_ready = _create_ready_page(self.trigger_key, self.model_id)
        self.stack.addWidget(self.p_ready)

        main_pane_layout.addWidget(self.stack, 1)

        # 3. Bottom Navigation Controls
        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(10, 8, 10, 4)

        # Step indicator dots
        self.dots = _DotIndicator(self.stack.count())
        nav_bar.addWidget(self.dots)
        nav_bar.addStretch()

        self.btn_back = GlassButton("Back", primary=False)
        self.btn_back.setFixedWidth(90)
        self.btn_back.clicked.connect(self._go_back)
        nav_bar.addWidget(self.btn_back)

        self.btn_next = GlassButton("Next", primary=True)
        self.btn_next.setFixedWidth(130)
        self.btn_next.clicked.connect(self._go_next)
        nav_bar.addWidget(self.btn_next)

        main_pane_layout.addLayout(nav_bar)
        body_split.addWidget(self.main_pane, 1)

        shell_layout.addLayout(body_split, 1)
        root.addWidget(self.shell)

        self._update_navigation_state()

        # Progress simulation timer for model download step
        self._prog_timer = QTimer(self)
        self._prog_val = 0
        self._prog_timer.timeout.connect(self._sim_progress)

    def _on_sidebar_select(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self._update_navigation_state()

    def _sim_progress(self):
        if self._prog_val < 100:
            self._prog_val += 4
            self.pbar.setValue(self._prog_val)
        else:
            self._prog_timer.stop()
            self._model_ready.emit()

    def _update_navigation_state(self):
        idx = self.stack.currentIndex()
        last = self.stack.count() - 1

        self.sidebar.set_current_index(idx)
        self.dots.set_current(idx)

        # Hide Back on first step
        self.btn_back.setVisible(idx > 0)
        self.btn_next.setText("Start Dictating" if idx == last else "Next")

        if idx == 3 and self._prog_val == 0:
            self._prog_timer.start(50)

    def _go_next(self):
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            self._update_navigation_state()
        else:
            self.accept()

    def _go_back(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_navigation_state()

    # Window Dragging Handling
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# 12. PAGINATION DOT INDICATOR
# ---------------------------------------------------------------------------
class _DotIndicator(QWidget):
    """Frosted pagination dot indicator."""

    def __init__(self, count: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._count = count
        self._current = 0
        self.setFixedHeight(18)
        self.setFixedWidth(count * 16 + 10)

    def set_current(self, index: int):
        self._current = index
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        dot_size = 6.0
        spacing = 14.0
        x = 4.0
        cy = self.height() / 2.0

        for i in range(self._count):
            if i == self._current:
                p.setBrush(QBrush(ACCENT_BLUE))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(x, cy - dot_size / 2.0, 16.0, dot_size), 3.0, 3.0)
                x += 22.0
            else:
                p.setBrush(QBrush(QColor(100, 116, 139, 120)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(x + dot_size / 2.0, cy), dot_size / 2.0, dot_size / 2.0)
                x += spacing
        p.end()
