"""The floating always-on-top Shape-Shifting Apple Liquid Glass Pill widget.

Integrates a two-pass real-time shader pipeline adhering to Apple HIG & Liquid Glass:
- Pass 1: Screen-space backdrop buffer capture using Windows GDI / QScreen with WDA_EXCLUDEFROMCAPTURE
- Pass 2: Liquid glass fragment shader with Snell's law refraction, edge lensing, Cauchy chromatic dispersion,
  Blinn-Phong multi-light specular glints, dynamic screen-center tracking, custom corner radius, and HD subpixel supersampling.
- Pass 3: Single Contiguous Glass Capsule in the Functional Layer:
  - Listening state:
    - Top row: Microphone glyph + 5-bar dynamic fluid waveform equalizer in Ice Cyan / Rose + Stop indicator.
    - Bottom row: Vibrant, high-contrast live transcript with subtle horizontal fade at edges.
  - Processing state: Compact glass capsule with pulsing breathing dots and "Processing speech…".
  - Inserted state: Emerald checkmark + "Inserted" confirmation.
  - Idle state: Signature circular glass orb with centered microphone glyph.
"""
import ctypes
from ctypes import wintypes
import math
import sys
import time

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
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from ui import theme
from ui.liquid_glass_shader import RIPPLE_SPEED, shader_engine

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011

user32 = None
GetWindowLong = None
SetWindowLong = None

if sys.platform == "win32":
    try:
        user32 = ctypes.windll.user32
        GetWindowLong = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        SetWindowLong = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
        GetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int]
        GetWindowLong.restype = ctypes.c_ssize_t
        SetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        SetWindowLong.restype = ctypes.c_ssize_t

        if hasattr(user32, "SetWindowDisplayAffinity"):
            user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
            user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
    except Exception:
        user32 = None


def _is_windows_dark_mode() -> bool:
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        except Exception:
            return True
    elif sys.platform == "darwin":
        try:
            hints = QApplication.styleHints()
            if hasattr(hints, "colorScheme"):
                return hints.colorScheme() == Qt.ColorScheme.Dark
        except Exception:
            pass
    return True


class Pill(QWidget):
    toggle_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    history_requested = pyqtSignal()
    copy_last_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    position_changed = pyqtSignal(int, int)
    geometry_changed = pyqtSignal()

    def __init__(self, x: int = None, y: int = None):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._dark = _is_windows_dark_mode()
        self._state = "idle"
        self._detail = ""
        self._press_pos = None
        self._press_origin = None
        self._dragged = False
        self._level = 0.0
        self._target_level = 0.0
        self._hovered = False
        self._shake_offset = 0
        self._pulse = 1.0
        self._ripple_phase = 0.0
        self._live_transcript = ""

        self._bg_pixmap = None
        self._liquid_image = None
        self._last_rendered_pos = None
        self._last_rendered_size = None
        self._last_rendered_state = None
        self._last_rendered_dark = None
        self._last_rendered_hover = None
        self._backdrop_dirty = True

        style = theme.STATES["idle"]
        self._width = float(style.width)
        self._height = float(style.height)
        self.resize(style.width, style.height)

        # 2D Symmetrical Geometry Morphing Animation
        self._morph_start_w = self._width
        self._morph_target_w = self._width
        self._morph_start_h = self._height
        self._morph_target_h = self._height

        self._morph_anim = QVariantAnimation(self)
        self._morph_anim.valueChanged.connect(self._on_morph_progress)
        easing = QEasingCurve(QEasingCurve.Type.OutBack)
        easing.setOvershoot(theme.MORPH_OVERSHOOT)
        self._morph_easing = easing

        # Pulse animation for processing/loading
        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setStartValue(0.40)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setDuration(theme.DURATION_PULSE)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.valueChanged.connect(self._on_pulse_value)

        # Shake animation for error
        self._shake_anim = QVariantAnimation(self)
        self._shake_anim.setDuration(theme.SHAKE_DURATION_MS)
        self._shake_anim.setKeyValueAt(0.0, 0)
        self._shake_anim.setKeyValueAt(0.2, -theme.SHAKE_DISTANCE_PX)
        self._shake_anim.setKeyValueAt(0.4, theme.SHAKE_DISTANCE_PX)
        self._shake_anim.setKeyValueAt(0.6, -theme.SHAKE_DISTANCE_PX)
        self._shake_anim.setKeyValueAt(0.8, theme.SHAKE_DISTANCE_PX)
        self._shake_anim.setKeyValueAt(1.0, 0)
        self._shake_anim.valueChanged.connect(self._on_shake_value)

        # Visualizer tick timer
        self._vis_timer = QTimer(self)
        self._vis_timer.setInterval(16)
        self._vis_timer.timeout.connect(self._on_vis_tick)

        # Real-time backdrop grab timer
        self._bg_timer = QTimer(self)
        self._bg_timer.setInterval(1000)
        self._bg_timer.timeout.connect(self._update_background_grab)

        # Set accessible name & description
        self.setAccessibleName("Dictate")
        self.setAccessibleDescription(style.accessible_name)

        # Restore saved position or default to center-bottom of screen
        if x is not None and y is not None and self._is_position_visible(x, y):
            self.move(x, y)
        else:
            primary = QApplication.primaryScreen()
            geo = primary.availableGeometry() if primary else QRect(0, 0, 1920, 1080)
            def_x = geo.x() + (geo.width() - self.width()) // 2
            def_y = geo.y() + geo.height() - self.height() - 60
            self.move(def_x, def_y)

        self.show()
        self._apply_native_flags()
        QTimer.singleShot(50, lambda: self._update_background_grab(force=True))
        self._bg_timer.start()

    def _is_position_visible(self, x: int, y: int) -> bool:
        pill_rect = QRect(x, y, self.width(), self.height())
        for screen in QApplication.screens():
            if screen.availableGeometry().intersects(pill_rect):
                return True
        return False

    def moveEvent(self, event):
        super().moveEvent(event)
        self._backdrop_dirty = True
        self._update_background_grab()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_native_flags()
        self._backdrop_dirty = True
        self._update_background_grab(force=True)

    def _apply_native_flags(self):
        try:
            hwnd = int(self.winId())
            if hwnd:
                cur = GetWindowLong(hwnd, GWL_EXSTYLE)
                SetWindowLong(hwnd, GWL_EXSTYLE, cur | WS_EX_NOACTIVATE)
                if hasattr(user32, "SetWindowDisplayAffinity"):
                    user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def _update_background_grab(self, force: bool = False):
        """Pass 1: Capture screen-space backdrop directly under pill coordinates."""
        if self.isMinimized() or not self.isVisible():
            return

        cur_pos = (self.x(), self.y())
        cur_size = (max(10, round(self._width)), max(10, round(self._height)))
        is_dynamic = self._state in ("recording", "preview") or self._dragged

        # Dirty check: skip heavy screen capture and shader rendering when stationary and unchanged
        if not force and not is_dynamic and not self._backdrop_dirty:
            if (cur_pos == self._last_rendered_pos and
                cur_size == self._last_rendered_size and
                self._state == self._last_rendered_state and
                self._dark == self._last_rendered_dark and
                self._hovered == self._last_rendered_hover and
                self._liquid_image is not None):
                return

        try:
            screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
            if screen:
                w, h = cur_size
                self._bg_pixmap = screen.grabWindow(0, self.x(), self.y(), w, h)
                self._execute_shader_pass()
                self._last_rendered_pos = cur_pos
                self._last_rendered_size = cur_size
                self._last_rendered_state = self._state
                self._last_rendered_dark = self._dark
                self._last_rendered_hover = self._hovered
                self._backdrop_dirty = False
                self.update()
        except Exception:
            pass

    def _execute_shader_pass(self):
        """Pass 2: Evaluate liquid glass fragment shader over captured backdrop buffer."""
        w = max(10, round(self._width))
        h = max(10, round(self._height))

        style = theme.STATES.get(self._state, theme.STATES["idle"])
        accent = QColor(theme.pick(style.accent, self._dark))

        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            screen_cx = geo.x() + geo.width() / 2.0
            screen_cy = geo.y() + geo.height() / 2.0
            pill_cx = self.x() + self.width() / 2.0
            pill_cy = self.y() + self.height() / 2.0
            screen_center_delta = (screen_cx - pill_cx, screen_cy - pill_cy)
        else:
            screen_center_delta = None

        dpr = max(1.0, float(self.devicePixelRatioF() or 1.0))
        is_rec = self._state in ("recording", "preview")
        corner_r = style.corner_radius
        black_tint = 0.35 if is_rec else 0.0
        accent_shader = None if is_rec else accent

        self._liquid_image = shader_engine.render(
            self._bg_pixmap, w, h,
            dark=self._dark,
            accent_color=accent_shader,
            ripple_phase=self._ripple_phase,
            screen_center_delta=screen_center_delta,
            supersample_factor=int(round(dpr * 2)),
            corner_radius=corner_r,
            black_tint=black_tint,
        )

    # ---- Live Transcript Handling ------------------------------------------

    def update_preview(self, text: str):
        """Update live transcript string for the listening pill."""
        trimmed = text.strip()
        if trimmed == self._live_transcript:
            return
        self._live_transcript = trimmed
        if self._state not in ("recording", "preview"):
            self.set_state("recording", "Listening…")
        else:
            self.update()

    def clear_preview(self):
        """Reset live transcript text."""
        self._live_transcript = ""
        self.update()

    # ---- State Machine & 2D Symmetrical Morphing ---------------------------

    def set_state(self, state: str, detail: str = ""):
        if state not in theme.STATES:
            state = "idle"
        prev_style = theme.STATES.get(self._state, theme.STATES["idle"])
        style = theme.STATES[state]
        self._state = state
        self._detail = detail

        # Update accessible metadata
        self.setAccessibleDescription(f"{style.accessible_name}" + (f" ({detail})" if detail else ""))

        # Tooltips with clear state vocabulary
        if state in ("recording", "preview"):
            tip = "Dictate — Listening…\nClick pill or press hotkey to stop"
            if detail:
                tip += f"\n{detail}"
            self.setToolTip(tip)
        elif state == "idle":
            tip = "Dictate — Ready\nClick pill or press hotkey to record"
            if detail:
                tip += f"\n{detail}"
            self.setToolTip(tip)
        else:
            self.setToolTip(f"Dictate — {style.label}" + (f"\n{detail}" if detail else ""))

        # Clear transcript when exiting recording
        if state not in ("recording", "preview"):
            self.clear_preview()

        # Trigger 2D Morph if dimensions changed
        target_w = style.width
        target_h = style.height
        if target_w != int(self._width) or target_h != int(self._height):
            self._start_morph(target_w, target_h)

        # Pulse animation for transcribing/loading
        if state in ("transcribing", "loading"):
            if self._pulse_anim.state() != QVariantAnimation.State.Running:
                self._pulse_anim.start()
        else:
            self._pulse_anim.stop()
            self._pulse = 1.0

        # Visualizer and backdrop refresh timer throttling
        if state in ("recording", "preview"):
            self._bg_timer.setInterval(theme.BACKDROP_UPDATE_MS)
            if not self._vis_timer.isActive():
                self._vis_timer.start()
        else:
            self._bg_timer.setInterval(1000)
            if self._vis_timer.isActive():
                self._vis_timer.stop()
            self._level = 0.0

        # Shake on error
        if state == "error" and prev_style is not style:
            self._shake_anim.stop()
            self._shake_anim.start()

        self._backdrop_dirty = True
        self._update_background_grab()
        self.update()

    def _start_morph(self, target_width: int, target_height: int):
        self._morph_anim.stop()
        self._morph_start_w = self._width
        self._morph_target_w = float(target_width)
        self._morph_start_h = self._height
        self._morph_target_h = float(target_height)

        growing = (target_width > self._width) or (target_height > self._height)
        self._morph_anim.setDuration(theme.DURATION_MORPH if growing else theme.DURATION_EXIT)
        self._morph_anim.setEasingCurve(self._morph_easing if growing else QEasingCurve.Type.OutCubic)
        self._morph_anim.setStartValue(0.0)
        self._morph_anim.setEndValue(1.0)
        self._morph_anim.start()

    def _on_morph_progress(self, progress: float):
        p = float(progress)
        self._width = self._morph_start_w + (self._morph_target_w - self._morph_start_w) * p
        self._height = self._morph_start_h + (self._morph_target_h - self._morph_start_h) * p

        center = self.geometry().center()
        w = max(10, round(self._width))
        h = max(10, round(self._height))
        rect = QRect(0, 0, w, h)
        rect.moveCenter(center)
        self.setGeometry(rect)
        self.geometry_changed.emit()
        self._execute_shader_pass()
        self.update()

    def _on_pulse_value(self, value):
        self._pulse = float(value)
        self.update()

    def _on_shake_value(self, value):
        prev = self._shake_offset
        self._shake_offset = int(value)
        delta = self._shake_offset - prev
        if delta:
            self.move(self.x() + delta, self.y())

    def _on_vis_tick(self):
        self._level += (self._target_level - self._level) * theme.METER_SMOOTHING
        self.update()

    def set_level(self, rms: float):
        """Update live input audio level for the 5-bar dynamic fluid waveform."""
        scaled = max(0.0, min(1.0, float(rms) * 12.0))
        self._target_level = scaled

    # ---- Painting: Single Glass Capsule Composition ------------------------

    def paintEvent(self, _event):
        style = theme.STATES.get(self._state, theme.STATES["idle"])
        accent = QColor(theme.pick(style.accent, self._dark))

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        rect = QRectF(0.0, 0.0, w, h)

        # 1. RENDER RETINA HD LIQUID GLASS SHADER PASS
        if self._liquid_image and not self._liquid_image.isNull():
            p.drawImage(rect, self._liquid_image)
        else:
            radius = style.corner_radius
            p.setPen(QPen(QColor(255, 255, 255, 50), 1.0))
            p.setBrush(QColor(15, 23, 42, 220) if self._dark else QColor(255, 255, 255, 210))
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        # 2. RENDER FOREGROUND CONTENT (Direct vibrant typography, no nested glass)
        self._paint_state_content(p, accent, rect)

        p.end()

    def _paint_state_content(self, p: QPainter, accent: QColor, rect: QRectF):
        cx = rect.center().x()
        cy = rect.center().y()
        w = rect.width()
        h = rect.height()
        state = self._state

        if state in ("recording", "preview"):
            # SINGLE LIQUID GLASS CAPSULE:
            # -------------------------------------------------------------
            # Top Row: Microphone + 5-Bar Waveform + Stop Dot
            # -------------------------------------------------------------
            top_cy = 22.0

            # 1. Glowing Microphone Icon on left
            mic_cx = 28.0
            mic_color = QColor(accent)
            mic_color.setAlphaF(min(1.0, 0.90 + 0.10 * math.sin(time.time() * 5)))
            self._draw_mic_glyph(p, mic_color, mic_cx, top_cy, scale=0.76)

            # 2. 5-Bar Dynamic Fluid Waveform Equalizer (reacts to live voice level)
            waveform_cx = w / 2.0
            p.setPen(Qt.PenStyle.NoPen)
            num_bars = 5
            spacing = 8.5
            start_bx = waveform_cx - (num_bars - 1) * spacing / 2.0
            t = time.time() * 7

            for i in range(num_bars):
                bx = start_bx + i * spacing
                phase = math.sin(t + i * 1.2) * 0.35 + 0.65
                bar_h = 3.5 + (16.0 * self._level * phase)
                bar_h = max(3.0, min(18.0, bar_h))

                bar_color = QColor(accent)
                if i in (1, 3):
                    bar_color = bar_color.lighter(115)
                bar_color.setAlphaF(0.90 + 0.10 * (bar_h / 18.0))
                p.setBrush(bar_color)
                p.drawRoundedRect(QRectF(bx - 1.5, top_cy - bar_h / 2.0, 3.0, bar_h), 1.5, 1.5)

            # 3. Right Status Indicator Dot
            status_dot_cx = w - 28.0
            p.setBrush(mic_color)
            p.drawEllipse(QPointF(status_dot_cx, top_cy), 2.5, 2.5)

            # 4. Subtle Hairline Separator
            sep_y = 36.0
            sep_grad = QLinearGradient(20.0, sep_y, w - 20.0, sep_y)
            sep_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            sep_grad.setColorAt(0.5, QColor(255, 255, 255, 30 if self._dark else 20))
            sep_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setPen(QPen(QBrush(sep_grad), 1.0))
            p.drawLine(QPointF(20.0, sep_y), QPointF(w - 20.0, sep_y))

            # -------------------------------------------------------------
            # Bottom Area (y: 38 to 74): High-Contrast Live Transcript Text
            # -------------------------------------------------------------
            p.save()
            text_rect = QRectF(18.0, 38.0, w - 36.0, 30.0)
            clip_path = QPainterPath()
            clip_path.addRect(text_rect)
            p.setClipPath(clip_path)

            if self._live_transcript:
                font_live = theme.get_font(12, QFont.Weight.DemiBold)
                p.setFont(font_live)
                fm = QFontMetrics(font_live)
                text_w = fm.horizontalAdvance(self._live_transcript)

                # Right-align live speech so latest spoken words remain in view
                if text_w > (w - 40.0):
                    draw_x = (w - 20.0) - text_w
                else:
                    draw_x = (w - text_w) / 2.0

                p.setPen(QColor("#FFFFFF" if self._dark else "#0F172A"))
                p.drawText(QRectF(draw_x, 38.0, text_w + 10.0, 30.0), Qt.AlignmentFlag.AlignVCenter, self._live_transcript)
            else:
                font_hint = theme.get_font(11, QFont.Weight.Medium)
                p.setFont(font_hint)
                p.setPen(QColor(148, 163, 184, 170) if self._dark else QColor(100, 116, 139, 170))
                p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Listening… speak naturally")

            p.restore()

        elif state == "transcribing":
            # Compact Pill with 3 Pulsing Breathing Dots + Label
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            dot_start_x = cx - 36.0
            t = time.time() * 5
            for i in range(3):
                wave = math.sin(t + i * 1.1) * 0.5 + 0.5
                r = 2.0 + 1.2 * wave
                dot_color = QColor(accent)
                dot_color.setAlphaF(0.50 + 0.50 * wave)
                p.setBrush(dot_color)
                p.drawEllipse(QPointF(dot_start_x + i * 8.0, cy), r, r)

            # Processing Label
            p.setFont(theme.get_font(11, QFont.Weight.DemiBold))
            p.setPen(QColor("#FFFFFF" if self._dark else "#0F172A"))
            p.drawText(QRectF(cx - 8.0, 0, w / 2.0 + 8.0, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Processing")

        elif state == "injecting":
            # Emerald Checkmark + "Inserted" Label
            p.setPen(QPen(accent, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            check_x = cx - 28.0
            p.drawLine(QPointF(check_x - 4.5, cy), QPointF(check_x - 1.0, cy + 3.5))
            p.drawLine(QPointF(check_x - 1.0, cy + 3.5), QPointF(check_x + 5.0, cy - 3.5))

            # Inserted Label
            p.setFont(theme.get_font(11, QFont.Weight.DemiBold))
            p.setPen(QColor("#FFFFFF" if self._dark else "#0F172A"))
            p.drawText(QRectF(cx - 14.0, 0, w / 2.0 + 14.0, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Inserted")

        elif state == "loading":
            # Minimalist Rotating Arc
            p.setPen(QPen(accent, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            arc_rect = QRectF(cx - 7.0, cy - 7.0, 14.0, 14.0)
            start_angle = int((time.time() * 240) % 360) * 16
            p.drawArc(arc_rect, start_angle, 220 * 16)

        elif state == "error":
            # Exclamation Glyph
            p.setPen(QPen(accent, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx, cy - 6.0), QPointF(cx, cy + 1.0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            p.drawEllipse(QPointF(cx, cy + 5.0), 1.5, 1.5)

        else:
            # Idle: Centered Sleek Microphone Glyph
            color = QColor(accent)
            color.setAlphaF(0.98 if self._hovered else 0.90)
            self._draw_mic_glyph(p, color, cx, cy, scale=1.0)

    def _draw_mic_glyph(self, p: QPainter, color: QColor, cx: float, cy: float, scale: float = 1.0):
        p.save()
        p.translate(cx, cy)
        p.scale(scale, scale)
        p.setPen(QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Microphone capsule body
        p.drawRoundedRect(QRectF(-3.5, -7.5, 7.0, 10.0), 3.5, 3.5)
        # Stand arc
        p.drawArc(QRectF(-6.0, -3.5, 12.0, 8.5), 180 * 16, 180 * 16)
        # Vertical stem and base
        p.drawLine(QPointF(0.0, 5.0), QPointF(0.0, 8.5))
        p.drawLine(QPointF(-3.5, 8.5), QPointF(3.5, 8.5))
        p.restore()

    # ---- Mouse & Gesture Interaction ---------------------------------------

    def enterEvent(self, event):
        super().enterEvent(event)
        self._hovered = True
        self._backdrop_dirty = True
        self._update_background_grab()
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hovered = False
        self._backdrop_dirty = True
        self._update_background_grab()
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self._menu(e.globalPosition().toPoint())
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.globalPosition().toPoint()
            self._press_origin = self.pos()
            self._dragged = False

    def mouseMoveEvent(self, e):
        if self._press_pos is not None:
            delta = e.globalPosition().toPoint() - self._press_pos
            if delta.manhattanLength() > 8:
                self._dragged = True
                self.move(self._press_origin + delta)
                self._update_background_grab()
                self.geometry_changed.emit()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._dragged:
                self.position_changed.emit(self.x(), self.y())
                self._update_background_grab()
            else:
                self.toggle_requested.emit()
        self._press_pos = None
        self._dragged = False

    def _menu(self, global_pos: QPoint):
        m = QMenu(self)
        m.setStyleSheet(theme.get_dialog_stylesheet(self._dark))
        m.addAction("Copy Last Transcript", self.copy_last_requested.emit)
        m.addAction("Transcript History…", self.history_requested.emit)
        m.addSeparator()
        m.addAction("Settings…", self.settings_requested.emit)
        m.addSeparator()
        m.addAction("Quit Dictate", self.quit_requested.emit)
        m.exec(global_pos)
