"""First-run onboarding for Dictate.

Liquid Glass layer discipline (Apple HIG & Stitch Liquid Glass System):
  - Transparent frosted glass background with dual-tone depth:
    the left navigation rail is a lighter frosted glass shade, while the
    right content panel is a darker frosted glass shade.
  - Glass (``shader_engine``) is reserved for the FUNCTIONAL layer —
    the primary CTA button and the active sidebar nav item.
  - The hero illustration is CONTENT the person looks at, not a control,
    so it renders as a frosted vibrant-tinted badge with concentric pulse
    rings and waveform visualizers rather than functional glass.
  - Only one glass surface is ever visible per region (no stacking), and
    every glass surface uses the Regular variant.
  - ``reduced_transparency`` / ``reduced_motion`` mirror the system
    accessibility settings that automatically modify Liquid Glass: the
    former swaps glass for an opaque fill, the latter freezes ripple/
    highlight motion and skips toggle easing.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import math
import sys
from typing import Callable

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from ui import theme
from ui.liquid_glass_shader import RIPPLE_SPEED, shader_engine
from ui.settings_dialog import KeyCaptureButton


def _font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    return theme.get_font(size, weight)


def _circle_path(cx: float, cy: float, r: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QPointF(cx, cy), r, r)
    return path


def _draw_sf_symbol(painter: QPainter, name: str, cx: float, cy: float, size: float, color: QColor, weight: float = 2.0, filled: bool = False) -> None:
    """Render Apple SF Symbols with standard layout sizing and semantic weight properties."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scale = size / 30.0

    if name in ("welcome", "house", "mic"):
        # SF Symbol: mic / microphone glyph
        path = QPainterPath()
        path.addRoundedRect(QRectF(cx - 4.5 * scale, cy - 12.0 * scale, 9.0 * scale, 16.0 * scale), 4.5 * scale, 4.5 * scale)
        # Arc
        arc = QPainterPath()
        arc.arcMoveTo(QRectF(cx - 9.0 * scale, cy - 6.0 * scale, 18.0 * scale, 16.0 * scale), 0)
        arc.arcTo(QRectF(cx - 9.0 * scale, cy - 6.0 * scale, 18.0 * scale, 16.0 * scale), 0, -180)

        painter.setBrush(color if filled else Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, weight * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(arc)
        painter.drawLine(QPointF(cx, cy + 10.0 * scale), QPointF(cx, cy + 15.0 * scale))
        painter.drawLine(QPointF(cx - 6.0 * scale, cy + 15.0 * scale), QPointF(cx + 6.0 * scale, cy + 15.0 * scale))

    elif name in ("setup", "gear", "settings"):
        # SF Symbol: gearshape.fill / gearshape
        teeth = 6
        r_out = 12.5 * scale
        r_in = 9.0 * scale
        r_hole = 4.2 * scale
        path = QPainterPath()
        for i in range(teeth * 2):
            angle = i * (math.pi / teeth)
            r = r_out if (i % 2 == 0) else r_in
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        path.closeSubpath()

        if filled:
            hole = QPainterPath()
            hole.addEllipse(QPointF(cx, cy), r_hole, r_hole)
            path = path.subtracted(hole)
            painter.fillPath(path, color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, weight, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
            painter.drawEllipse(QPointF(cx, cy), r_hole, r_hole)

    elif name in ("ready", "play", "get_started", "rocket"):
        # SF Symbol: play.fill / rocket
        path = QPainterPath()
        w_half = 9.5 * scale
        h_half = 11.5 * scale
        path.moveTo(cx - w_half + 2.0 * scale, cy - h_half)
        path.lineTo(cx + w_half + 1.0 * scale, cy)
        path.lineTo(cx - w_half + 2.0 * scale, cy + h_half)
        path.closeSubpath()

        if filled:
            painter.fillPath(path, color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, weight, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)

    elif name == "check":
        # SF Symbol: checkmark
        path = QPainterPath()
        path.moveTo(cx - 6.0 * scale, cy)
        path.lineTo(cx - 2.0 * scale, cy + 5.0 * scale)
        path.lineTo(cx + 7.0 * scale, cy - 6.0 * scale)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, weight * 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

    elif name == "shield":
        # SF Symbol: shield.check
        path = QPainterPath()
        path.moveTo(cx, cy - 10.0 * scale)
        path.lineTo(cx + 8.0 * scale, cy - 6.0 * scale)
        path.lineTo(cx + 8.0 * scale, cy + 2.0 * scale)
        path.quadTo(cx + 7.0 * scale, cy + 9.0 * scale, cx, cy + 12.0 * scale)
        path.quadTo(cx - 7.0 * scale, cy + 9.0 * scale, cx - 8.0 * scale, cy + 2.0 * scale)
        path.lineTo(cx - 8.0 * scale, cy - 6.0 * scale)
        path.closeSubpath()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, weight, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

    painter.restore()


def _apply_backdrop_blur(hwnd: int, dark: bool = False) -> None:
    """Enable Windows native DWM BlurBehind for authentic frosted glass translucency."""
    if sys.platform != "win32" or not hwnd:
        return
    try:
        dwmapi = ctypes.windll.dwmapi
        val = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass

    try:
        user32 = ctypes.windll.user32
        SetWindowCompositionAttribute = getattr(user32, "SetWindowCompositionAttribute", None)
        if SetWindowCompositionAttribute:
            class ACCENT_POLICY(ctypes.Structure):
                _fields_ = [
                    ("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_int),
                    ("AnimationId", ctypes.c_int),
                ]

            class WINCOMPATTRDATA(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.c_void_p),
                    ("SizeOfData", ctypes.c_size_t),
                ]

            accent = ACCENT_POLICY()
            accent.AccentState = 3  # ACCENT_ENABLE_BLURBEHIND
            accent.AccentFlags = 0
            accent.GradientColor = 0
            accent.AnimationId = 0

            data = WINCOMPATTRDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = ctypes.cast(ctypes.byref(accent), ctypes.c_void_p)
            data.SizeOfData = ctypes.sizeof(accent)
            SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except Exception:
        pass


def _glass_backdrop(size: QSize, dark: bool, accent: QColor) -> QPixmap:
    """Create a quiet backdrop for the shared refractive shader."""
    pixmap = QPixmap(size)
    bg_hex = theme.pick(theme.SURFACE_CARD, dark)
    pixmap.fill(QColor(bg_hex))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    wash = QColor(accent)
    wash.setAlpha(28 if dark else 20)
    painter.setBrush(wash)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(-size.width() * 0.15, -size.height() * 0.6, size.width() * 1.1, size.height() * 1.5))
    painter.end()
    return pixmap


class OnboardingShell(QFrame):
    """Frosted glass container frame with lighter left sidebar rail and darker right content panel."""

    def __init__(self, rail_width: int = 210, dark: bool = False, reduced_transparency: bool = False, parent=None):
        super().__init__(parent)
        self.rail_width = rail_width
        self.dark = dark
        self.reduced_transparency = reduced_transparency
        self.radius = 24.0
        self.left_alpha = 95 if dark else 115
        self.right_alpha = 120 if dark else 85
        self.highlight_alpha = 28 if dark else 140
        self.border_alpha = 35 if dark else 180
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = float(self.radius)

        outer_path = QPainterPath()
        outer_path.addRoundedRect(rect, radius, radius)

        p.save()
        p.setClipPath(outer_path)

        rw = float(self.rail_width)
        w = rect.width()
        h = rect.height()

        left_rect = QRectF(rect.left(), rect.top(), rw, h)
        right_rect = QRectF(rect.left() + rw, rect.top(), w - rw, h)

        if self.reduced_transparency:
            left_color = QColor(theme.pick(theme.SURFACE_ELEVATED, self.dark))
            right_color = QColor(theme.pick(theme.SURFACE_BG, self.dark))
            divider_color = QColor(theme.pick(theme.BORDER_SUBTLE, self.dark))
            border_color = QColor(255, 255, 255, 35) if self.dark else QColor(0, 0, 0, 25)
        else:
            if self.dark:
                left_color = QColor(42, 58, 86, int(self.left_alpha))
                right_color = QColor(10, 16, 28, int(self.right_alpha))
                divider_color = QColor(255, 255, 255, 20)
                border_color = QColor(255, 255, 255, int(self.border_alpha))
            else:
                left_color = QColor(255, 255, 255, int(self.left_alpha))
                right_color = QColor(215, 224, 236, int(self.right_alpha))
                divider_color = QColor(0, 0, 0, 15)
                border_color = QColor(255, 255, 255, int(self.border_alpha))

        # 1. Fill Left Panel (lighter shade)
        p.fillRect(left_rect, left_color)

        # 2. Fill Right Panel (darker shade)
        p.fillRect(right_rect, right_color)

        # 3. Vertical Divider Line
        p.setPen(QPen(divider_color, 1.0))
        p.drawLine(QPointF(rect.left() + rw, rect.top()), QPointF(rect.left() + rw, rect.bottom()))

        # 4. Subtle Top Inner Specular Highlight Rim
        if not self.reduced_transparency and self.highlight_alpha > 0:
            highlight = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top() + 14)
            highlight.setColorAt(0.0, QColor(255, 255, 255, int(self.highlight_alpha)))
            highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillRect(QRectF(rect.left(), rect.top(), w, 14), highlight)

        p.restore()

        # 5. Crisp Outer Glass Rim Border
        p.setPen(QPen(border_color, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(outer_path)

        # Delicate shadow hairline on light mode
        if not self.dark and not self.reduced_transparency:
            p.setPen(QPen(QColor(0, 0, 0, 16), 1.0))
            p.drawPath(outer_path)


class LiquidGlassButton(QPushButton):
    """A restrained control rendered with the shared refraction shader."""

    def __init__(self, text: str, *, primary=False, accent_token=theme.SYSTEM_TEAL, dark=False,
                 reduced_transparency=False, reduced_motion=False, parent=None):
        super().__init__(text, parent)
        self.primary, self.accent_token, self.dark = primary, accent_token, dark
        self.reduced_transparency, self.reduced_motion = reduced_transparency, reduced_motion
        self._hover = self._pressed = False
        self._image = QImage()
        self.setFixedHeight(40)
        self.setMinimumWidth(110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(_font(10, QFont.Weight.DemiBold))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _render(self):
        w = int(self.width() - 2)
        h = int(self.height() - 2)
        if w < 8 or h < 8:
            return
        if self.reduced_transparency:
            self._image = QImage()
            return
        accent = QColor(theme.pick(self.accent_token, self.dark))
        if self._hover:
            accent = accent.lighter(108)
        if self._pressed:
            accent = accent.darker(108)
        phase = 0 if self.reduced_motion else (0.18 if self._hover else 0)
        corner_r = h / 2.0
        self._image = shader_engine.render(
            _glass_backdrop(QSize(w, h), self.dark, accent),
            w,
            h,
            dark=self.dark,
            accent_color=accent,
            ripple_phase=phase,
            supersample_factor=2,
            corner_radius=corner_r,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render()

    def enterEvent(self, event):
        self._hover = True
        self._render()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = self._pressed = False
        self._render()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = event.button() == Qt.MouseButton.LeftButton
        self._render()
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self._render()
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        accent = QColor(theme.pick(self.accent_token, self.dark))

        p.save()
        p.setClipPath(path)
        if self.primary:
            if not self._image.isNull():
                p.drawImage(rect, self._image)
                accent_wash = QColor(accent)
                accent_wash.setAlpha(190 if self.dark else 210)
                p.fillPath(path, accent_wash)
            else:
                p.fillPath(path, accent)
            p.restore()
            p.setPen(QPen(QColor(255, 255, 255, 120), 1))
            p.drawPath(path)
            color = QColor("#00201C") if not self.dark else QColor("#FFFFFF")
        else:
            p.restore()
            fill = QColor(255, 255, 255, 26 if self.dark else 150)
            if self._hover:
                fill.setAlpha(fill.alpha() + 24)
            p.fillPath(path, fill)
            p.setPen(QPen(QColor(255, 255, 255, 70) if self.dark else QColor(0, 0, 20, 24), 1))
            p.drawPath(path)
            color = QColor(theme.pick(theme.TEXT_PRIMARY, self.dark))

        if self.hasFocus():
            p.setPen(QPen(QColor(theme.pick(theme.BORDER_FOCUS, self.dark)), 2))
            p.drawPath(path)
        p.setFont(self.font())
        p.setPen(color)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())


class AppleToggle(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, dark=False, reduced_motion=False, parent=None):
        super().__init__(parent)
        self.dark, self._checked, self._position, self.reduced_motion = dark, checked, float(checked), reduced_motion
        self.setFixedSize(48, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._animation = QVariantAnimation(self, duration=0 if reduced_motion else 180)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._animate)

    def _animate(self, value):
        self._position = float(value)
        self.update()

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if checked == self._checked:
            return
        self._checked = checked
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(float(checked))
        self._animation.start()
        self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.setChecked(not self._checked)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.pick(theme.SYSTEM_TEAL, self.dark)) if self._checked else QColor(120, 120, 128, 90))
        p.drawRoundedRect(track, 14, 14)
        x = track.left() + 3 + self._position * (track.width() - 28)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, track.top() + 3, 22, 22))


@dataclass(frozen=True)
class HeroAsset:
    """A page hero contract. Use ``widget_factory`` for an animated SVG widget later."""
    name: str
    accent_token: tuple[str, str]
    svg_path: str | None = None
    widget_factory: Callable[[QWidget], QWidget] | None = None


DEFAULT_HEROES = {
    "welcome": HeroAsset("welcome", theme.SYSTEM_TEAL),
    "setup": HeroAsset("setup", theme.SYSTEM_PURPLE),
    "ready": HeroAsset("ready", theme.SYSTEM_GREEN),
}


class HeroStage(QWidget):
    """Stitch Liquid Glass Content Platter with concentric animated wave rings and 3D glowing orb."""

    def __init__(self, asset: HeroAsset, dark=False, reduced_transparency=False, reduced_motion=False, parent=None):
        super().__init__(parent)
        self.asset, self.dark, self._phase, self._external_widget = asset, dark, 0.0, None
        self.reduced_transparency, self.reduced_motion = reduced_transparency, reduced_motion
        self.card_alpha = 14 if dark else 80
        self.orb_size = 88.0
        self.setFixedHeight(180)
        self._timer = QTimer(self, interval=33)
        self._timer.timeout.connect(self._tick)
        if not self.reduced_motion:
            self._timer.start()
        self.set_hero_asset(asset)

    def set_hero_asset(self, asset: HeroAsset):
        self.asset = asset
        if self._external_widget:
            self._external_widget.deleteLater()
            self._external_widget = None
        if asset.widget_factory:
            self._external_widget = asset.widget_factory(self)
            self._external_widget.setGeometry(self.rect())
            self._external_widget.show()
        elif asset.svg_path:
            svg = QSvgWidget(asset.svg_path, self)
            if svg.renderer().isValid():
                self._external_widget = svg
                self._external_widget.setGeometry(self.rect())
                self._external_widget.show()
            else:
                svg.deleteLater()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._external_widget:
            self._external_widget.setGeometry(self.rect())

    def _tick(self):
        self._phase = (self._phase + 0.012 * RIPPLE_SPEED) % 1.0
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 20, 20)

        # 1. Concentric Frosted Platter Fill
        if self.reduced_transparency:
            p.fillPath(path, QColor(theme.pick(theme.SURFACE_ELEVATED, self.dark)))
        else:
            card_fill = QColor(255, 255, 255, int(self.card_alpha))
            p.fillPath(path, card_fill)

        accent = QColor(theme.pick(self.asset.accent_token, self.dark))
        cx, cy = rect.center().x(), rect.center().y()
        orb = float(self.orb_size)

        # 2. Concentric Radiating Wave Rings
        if not self.reduced_motion:
            for i in range(3):
                ring_phase = (self._phase + i * 0.33) % 1.0
                ring_r = (orb / 2.0) + ring_phase * 48.0
                ring_alpha = int((1.0 - ring_phase) * 55)
                if ring_alpha > 0:
                    p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), ring_alpha), 1.2))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        # 3. Horizontal Decorative Waveform Bars (Welcome Stage)
        if self.asset.name == "welcome":
            p.setPen(Qt.PenStyle.NoPen)
            wave_c = QColor(accent)
            wave_c.setAlpha(90 if self.dark else 130)
            p.setBrush(wave_c)
            offsets = [(-68, 16), (-58, 30), (-48, 22), (48, 22), (58, 30), (68, 16)]
            for dx, bar_h in offsets:
                p.drawRoundedRect(QRectF(cx + dx - 1.5, cy - bar_h / 2, 3, bar_h), 1.5, 1.5)

        # 4. Central 3D Glowing Liquid Orb
        orb_rect = QRectF(cx - orb / 2, cy - orb / 2, orb, orb)
        p.save()
        p.setClipPath(_circle_path(cx, cy, orb / 2))

        # Radial 3D depth gradient
        rad = QRadialGradient(cx - orb * 0.2, cy - orb * 0.2, orb * 0.7)
        rad.setColorAt(0.0, accent.lighter(130))
        rad.setColorAt(0.7, accent)
        rad.setColorAt(1.0, accent.darker(150))
        p.setBrush(rad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(orb_rect)

        # Specular light glint sweep
        glint_x = cx - orb * 0.22 + (0 if self.reduced_motion else orb * 0.12 * (1 - abs(self._phase * 2 - 1)))
        glint = QColor(255, 255, 255, 80 if self.dark else 120)
        p.setBrush(glint)
        p.drawEllipse(QPointF(glint_x, cy - orb * 0.22), orb * 0.40, orb * 0.28)
        p.restore()

        # 5. Crisp SF Symbol Center Icon
        icon_color = QColor("#00201C") if not self.dark else QColor("#FFFFFF")
        _draw_sf_symbol(p, self.asset.name, cx, cy, 34.0, icon_color, weight=2.4, filled=True)

        # 6. Platter Specular Border
        card_border = QColor(255, 255, 255, 24 if self.dark else 160)
        p.setPen(QPen(card_border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)


class SidebarNavItem(QWidget):
    clicked = pyqtSignal(int)

    def __init__(self, index: int, title: str, dark=False, reduced_transparency=False, reduced_motion=False, parent=None):
        super().__init__(parent)
        self.index, self.title, self.dark = index, title, dark
        self.reduced_transparency, self.reduced_motion = reduced_transparency, reduced_motion
        self._active = False
        self._completed = False
        self._hover = False
        self._image = QImage()
        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _render(self):
        w = max(10, int(self.width() - 4))
        h = max(10, int(self.height() - 4))
        if self.reduced_transparency:
            self._image = QImage()
            return
        accent = QColor(theme.pick(theme.SYSTEM_TEAL, self.dark))
        phase = 0 if self.reduced_motion else (0.22 if self._hover else 0.12)
        corner_r = 12.0
        self._image = shader_engine.render(
            _glass_backdrop(QSize(w, h), self.dark, accent),
            w,
            h,
            dark=self.dark,
            accent_color=accent,
            ripple_phase=phase,
            supersample_factor=2,
            corner_radius=corner_r,
        )

    def set_active(self, active: bool, completed: bool = False):
        self._active = active
        self._completed = completed
        if active:
            self._render()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._active:
            self._render()

    def enterEvent(self, event):
        self._hover = True
        if self._active:
            self._render()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        if self._active:
            self._render()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Space):
            self.clicked.emit(self.index)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        accent = QColor(theme.pick(theme.SYSTEM_TEAL, self.dark))

        if self._active:
            if self.reduced_transparency:
                p.fillPath(path, accent)
            else:
                p.save()
                p.setClipPath(path)
                if not self._image.isNull():
                    p.drawImage(rect, self._image)
                    accent_tint = QColor(accent)
                    accent_tint.setAlpha(45 if self.dark else 35)
                    p.fillPath(path, accent_tint)
                else:
                    active_fill = QColor(accent)
                    active_fill.setAlpha(42 if self.dark else 35)
                    p.fillPath(path, active_fill)

                # Vertical Indicator Accent Bar on the Left Edge
                ind_bar = QRectF(rect.left(), rect.top() + 6, 3.5, rect.height() - 12)
                p.fillRect(ind_bar, accent)
                p.restore()

            # Specular Liquid Glass perimeter rim
            p.setPen(QPen(QColor(255, 255, 255, 115 if self.dark else 150), 1))
            p.drawPath(path)
        elif self._hover:
            hover_fill = QColor(255, 255, 255, 16 if self.dark else 70)
            p.fillPath(path, hover_fill)

        if self._active and self.reduced_transparency:
            dot_color, text_color = QColor("#FFFFFF"), QColor("#FFFFFF")
        elif self._active:
            dot_color = text_color = accent
        elif self._completed:
            dot_color = accent
            text_color = QColor(theme.pick(theme.TEXT_PRIMARY, self.dark))
        else:
            dot_color = text_color = QColor(theme.pick(theme.TEXT_SECONDARY, self.dark))

        # Icon: Checkmark if completed, or SF Symbol glyph
        icon_cx = rect.left() + 18
        icon_cy = rect.center().y()
        if self._completed and not self._active:
            _draw_sf_symbol(p, "check", icon_cx, icon_cy, 13.0, dot_color, weight=2.0)
        else:
            symbol_name = "welcome" if self.index == 0 else ("setup" if self.index == 1 else "ready")
            _draw_sf_symbol(p, symbol_name, icon_cx, icon_cy, 14.0, dot_color, weight=1.8, filled=True)

        p.setFont(_font(10, QFont.Weight.DemiBold if self._active else QFont.Weight.Medium))
        p.setPen(text_color)
        p.drawText(QRectF(rect.left() + 34, rect.top(), rect.width() - 40, rect.height()), Qt.AlignmentFlag.AlignVCenter, self.title)


class OnboardingDialog(QDialog):
    """Three-stage first-run flow with Stitch Liquid Glass background."""

    class DialogCode:
        Accepted = 1
        Rejected = 0

    def __init__(self, trigger_key="ctrl+shift+p", model_id="", dark=False, parent=None, hero_assets=None,
                 reduced_transparency=False, reduced_motion=False):
        super().__init__(parent)
        self.trigger_key, self.model_id, self.dark = trigger_key, model_id, dark
        self.reduced_transparency, self.reduced_motion = reduced_transparency, reduced_motion
        self.hero_assets = {**DEFAULT_HEROES, **(hero_assets or {})}
        self._drag_pos = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(920, 600)
        self._build()
        self._go_to_scene(0)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            hwnd = int(self.winId())
            if hwnd and not self.reduced_transparency:
                _apply_backdrop_blur(hwnd, self.dark)
        except Exception:
            pass

    def _label(self, text, size=10, weight=QFont.Weight.Normal, muted=False):
        label = QLabel(text)
        label.setFont(_font(size, weight))
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {theme.pick(theme.TEXT_SECONDARY if muted else theme.TEXT_PRIMARY, self.dark)}; background: transparent;")
        return label

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        rail_width = 210
        self.shell = OnboardingShell(
            rail_width=rail_width,
            dark=self.dark,
            reduced_transparency=self.reduced_transparency,
            parent=self,
        )
        self.shell.setObjectName("onboardingShell")
        outer.addWidget(self.shell)

        root = QHBoxLayout(self.shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left Rail Panel (lighter frosted glass shade)
        rail = QWidget()
        rail.setFixedWidth(rail_width)
        rail.setStyleSheet("background: transparent;")
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(18, 28, 18, 24)
        rail_layout.setSpacing(6)

        # Brand Header with glowing voice orb
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_row.setContentsMargins(6, 0, 6, 14)

        icon_box = QFrame()
        icon_box.setFixedSize(34, 34)
        icon_box.setStyleSheet(f"""
            background: rgba({ '45, 212, 191, 0.15' if self.dark else '45, 212, 191, 0.25' });
            border: 1px solid rgba(45, 212, 191, 0.4);
            border-radius: 17px;
        """)
        icon_box_layout = QVBoxLayout(icon_box)
        icon_box_layout.setContentsMargins(0, 0, 0, 0)
        mic_icon = QLabel()
        mic_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mic_icon.setFont(_font(11, QFont.Weight.Bold))
        mic_icon.setText("🎙")
        icon_box_layout.addWidget(mic_icon)
        brand_row.addWidget(icon_box)

        brand = self._label("Dictate", 13, QFont.Weight.Bold)
        brand.setStyleSheet(f"color: {theme.pick(theme.SYSTEM_TEAL, self.dark)}; background: transparent;")
        brand_row.addWidget(brand)
        brand_row.addStretch()
        rail_layout.addLayout(brand_row)

        # Section Label
        sec_lbl = QLabel("ONBOARDING")
        sec_lbl.setFont(_font(8, QFont.Weight.Bold))
        sec_lbl.setStyleSheet(f"color: {theme.pick(theme.TEXT_SECONDARY, self.dark)}; letter-spacing: 1px; padding-left: 8px; margin-bottom: 2px; background: transparent;")
        rail_layout.addWidget(sec_lbl)

        rt, rm = self.reduced_transparency, self.reduced_motion
        self.nav_items = [
            SidebarNavItem(0, "Welcome", self.dark, rt, rm),
            SidebarNavItem(1, "Setup", self.dark, rt, rm),
            SidebarNavItem(2, "Get Started", self.dark, rt, rm),
        ]
        for item in self.nav_items:
            item.clicked.connect(self._go_to_scene)
            rail_layout.addWidget(item)

        rail_layout.addStretch()
        root.addWidget(rail)

        # Right Content Panel (darker frosted glass shade)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(44, 32, 44, 28)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.stack.addWidget(self._welcome())
        self.stack.addWidget(self._setup())
        self.stack.addWidget(self._ready())
        content_layout.addWidget(self.stack)

        root.addWidget(content)

    def _page(self, hero_name: str, title: str, subtitle: str):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(HeroStage(self.hero_assets[hero_name], self.dark, self.reduced_transparency, self.reduced_motion))
        layout.addSpacing(22)
        layout.addWidget(self._label(title, 21, QFont.Weight.Bold))
        layout.addSpacing(6)
        layout.addWidget(self._label(subtitle, 10, muted=True))
        return page, layout

    def _actions(self, layout: QVBoxLayout, back: int | None, forward: str, handler: Callable):
        layout.addStretch()
        row = QHBoxLayout()
        if back is not None:
            button = LiquidGlassButton("← Back", dark=self.dark, reduced_transparency=self.reduced_transparency, reduced_motion=self.reduced_motion)
            button.clicked.connect(lambda: self._go_to_scene(back))
            row.addWidget(button)
        row.addStretch()
        primary = LiquidGlassButton(f"{forward} →", primary=True, dark=self.dark, reduced_transparency=self.reduced_transparency, reduced_motion=self.reduced_motion)
        primary.clicked.connect(handler)
        row.addWidget(primary)
        layout.addLayout(row)

    def _welcome(self):
        page, layout = self._page("welcome", "Dictate, wherever you write.", "Hold a shortcut, speak, and Dictate places clean text at your cursor.")
        layout.addSpacing(16)

        # Privacy Pill Badge
        badge = QFrame()
        badge.setStyleSheet(f"""
            background: rgba({'255, 255, 255, 0.05' if self.dark else '0, 0, 0, 0.04'});
            border: 1px solid rgba({'255, 255, 255, 0.12' if self.dark else '0, 0, 0, 0.08'});
            border-radius: 14px;
            padding: 4px 12px;
        """)
        b_layout = QHBoxLayout(badge)
        b_layout.setContentsMargins(10, 4, 10, 4)
        b_layout.setSpacing(8)

        icon_lbl = QLabel("🛡")
        icon_lbl.setFont(_font(9, QFont.Weight.Normal))
        b_layout.addWidget(icon_lbl)

        txt_lbl = QLabel("Speech recognition stays on your device · 100% Offline")
        txt_lbl.setFont(_font(9, QFont.Weight.Medium))
        txt_lbl.setStyleSheet(f"color: {theme.pick(theme.TEXT_SECONDARY, self.dark)}; background: transparent;")
        b_layout.addWidget(txt_lbl)
        b_layout.addStretch()

        layout.addWidget(badge)
        self._actions(layout, None, "Continue", lambda: self._go_to_scene(1))
        return page

    def _setup_card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setStyleSheet(f"""
            background: rgba({'255, 255, 255, 0.04' if self.dark else '255, 255, 255, 0.70'});
            border: 1px solid rgba({'255, 255, 255, 0.12' if self.dark else '0, 0, 0, 0.08'});
            border-radius: 14px;
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(10)
        return card, card_layout

    def _setup(self):
        page, layout = self._page("setup", "A few essentials.", "Set the shortcut you’ll use to start dictating.")
        layout.addSpacing(14)

        card, c_layout = self._setup_card()

        # Row 1: Shortcut Capture
        r1 = QHBoxLayout()
        r1_text = QVBoxLayout()
        r1_text.setSpacing(2)
        r1_text.addWidget(self._label("Dictation shortcut", 10, QFont.Weight.DemiBold))
        r1_text.addWidget(self._label("Available in any app", 9, muted=True))
        r1.addLayout(r1_text)
        r1.addStretch()

        self.btn_capture = KeyCaptureButton(self.trigger_key)
        self.btn_capture.setFixedWidth(140)
        r1.addWidget(self.btn_capture)
        c_layout.addLayout(r1)

        # Hairline divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: rgba({'255, 255, 255, 0.08' if self.dark else '0, 0, 0, 0.06'});")
        c_layout.addWidget(div)

        # Row 2: Speech Model & Offline Ready Badge
        r2 = QHBoxLayout()
        r2_text = QVBoxLayout()
        r2_text.setSpacing(2)
        r2_text.addWidget(self._label("Local speech model", 10, QFont.Weight.DemiBold))
        r2_text.addWidget(self._label("Ready for offline transcription · Privacy first", 9, muted=True))
        r2.addLayout(r2_text)
        r2.addStretch()

        status_pill = QFrame()
        status_pill.setStyleSheet("""
            background: rgba(45, 212, 191, 0.12);
            border: 1px solid rgba(45, 212, 191, 0.35);
            border-radius: 12px;
            padding: 3px 10px;
        """)
        sp_layout = QHBoxLayout(status_pill)
        sp_layout.setContentsMargins(8, 2, 8, 2)
        sp_layout.setSpacing(6)
        dot = QLabel("●")
        dot.setFont(_font(7, QFont.Weight.Bold))
        dot.setStyleSheet("color: #2DD4BF; background: transparent;")
        sp_layout.addWidget(dot)
        stxt = QLabel("OFFLINE READY")
        stxt.setFont(_font(8, QFont.Weight.Bold))
        stxt.setStyleSheet("color: #2DD4BF; letter-spacing: 0.5px; background: transparent;")
        sp_layout.addWidget(stxt)
        r2.addWidget(status_pill)
        c_layout.addLayout(r2)

        layout.addWidget(card)
        self._actions(layout, 0, "Continue", lambda: self._go_to_scene(2))
        return page

    def _ready(self):
        page, layout = self._page("ready", "Ready when you are.", "Focus a text field, hold your shortcut, then speak naturally.")
        layout.addSpacing(14)

        card, c_layout = self._setup_card()

        # Row: AI Polish Toggle
        r1 = QHBoxLayout()
        r1_text = QVBoxLayout()
        r1_text.setSpacing(2)
        r1_text.addWidget(self._label("Polish transcripts (Optional)", 10, QFont.Weight.DemiBold))
        r1_text.addWidget(self._label("Remove filler words and tidy punctuation.", 9, muted=True))
        r1.addLayout(r1_text)
        r1.addStretch()

        self.toggle_ai = AppleToggle(False, self.dark, self.reduced_motion)
        r1.addWidget(self.toggle_ai)
        c_layout.addLayout(r1)

        # Footnote
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: rgba({'255, 255, 255, 0.08' if self.dark else '0, 0, 0, 0.06'});")
        c_layout.addWidget(div)

        footnote_row = QHBoxLayout()
        footnote_row.setSpacing(6)
        lock_lbl = QLabel("🔒")
        lock_lbl.setFont(_font(8))
        footnote_row.addWidget(lock_lbl)
        note_lbl = QLabel("Your speech is transcribed 100% locally. Cloud polish is strictly optional.")
        note_lbl.setFont(_font(8, QFont.Weight.Normal))
        note_lbl.setStyleSheet(f"color: {theme.pick(theme.TEXT_SECONDARY, self.dark)}; background: transparent;")
        footnote_row.addWidget(note_lbl)
        footnote_row.addStretch()
        c_layout.addLayout(footnote_row)

        layout.addWidget(card)
        self._actions(layout, 1, "Start Dictating", self.accept)
        return page

    def _go_to_scene(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, item in enumerate(self.nav_items):
            item.set_active(active=(i == index), completed=(i < index))

    def values(self):
        return {"trigger_key": getattr(self.btn_capture, "key", self.trigger_key), "ai_polish": self.toggle_ai.isChecked()}

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)