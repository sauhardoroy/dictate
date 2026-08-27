"""The floating always-on-top Shape-Shifting Apple Liquid Glass Pill widget.

Integrates a two-pass real-time shader pipeline:
- Pass 1: Screen-space backdrop buffer capture using Windows GDI / QScreen with WDA_EXCLUDEFROMCAPTURE
- Pass 2: Liquid glass fragment shader with Snell's law refraction, edge lensing, Cauchy chromatic dispersion,
  Blinn-Phong multi-light specular glints, dynamic screen-center tracking, and 2x Retina HD subpixel supersampling.
"""
import ctypes
from ctypes import wintypes
import math
import time

from PyQt6.QtCore import QEasingCurve, QPoint, QPointF, QRect, QRectF, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
import sys
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from ui import theme
from ui.liquid_glass_shader import shader_engine, RIPPLE_SPEED

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

        self._bg_pixmap = None
        self._liquid_image = None

        style = theme.STATES["idle"]
        self._width = float(style.width)
        self.setFixedHeight(theme.PILL_HEIGHT)
        self.resize(style.width, theme.PILL_HEIGHT)

        # Smooth morphing animation (Silky cubic interpolation)
        self._morph_anim = QVariantAnimation(self)
        self._morph_anim.valueChanged.connect(self._on_morph_value)
        easing = QEasingCurve(QEasingCurve.Type.OutBack)
        easing.setOvershoot(theme.MORPH_OVERSHOOT)
        self._morph_easing = easing

        # Pulse animation for thinking/loading
        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setStartValue(0.35)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setDuration(theme.PULSE_DURATION_MS)
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

        # Visualizer frame timer (Ultra-smooth 120 FPS animation refresh)
        self._vis_timer = QTimer(self)
        self._vis_timer.setInterval(8)
        self._vis_timer.timeout.connect(self._on_vis_tick)

        # Real-time backdrop grab timer (captures desktop behind pill for live refraction)
        self._bg_timer = QTimer(self)
        self._bg_timer.setInterval(theme.BACKDROP_UPDATE_MS)
        self._bg_timer.timeout.connect(self._update_background_grab)

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
        QTimer.singleShot(50, self._update_background_grab)
        self._bg_timer.start()

    def _is_position_visible(self, x: int, y: int) -> bool:
        pill_rect = QRect(x, y, self.width(), self.height())
        for screen in QApplication.screens():
            if screen.availableGeometry().intersects(pill_rect):
                return True
        return False

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_native_flags()

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

    def _update_background_grab(self):
        """Pass 1: Capture screen-space backdrop directly under pill coordinates."""
        if self.isMinimized() or not self.isVisible():
            return
        try:
            screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
            if screen:
                w, h = max(10, self.width()), max(10, self.height())
                self._bg_pixmap = screen.grabWindow(0, self.x(), self.y(), w, h)
                self._execute_shader_pass()
                self.update()
        except Exception:
            pass

    def _execute_shader_pass(self):
        """Pass 2: Evaluate liquid glass fragment shader over captured backdrop buffer with screen-center lighting & 2x HD supersampling."""
        w, h = max(10, round(self._width)), theme.PILL_HEIGHT
        style = theme.STATES.get(self._state, theme.STATES["idle"])
        accent = QColor(theme.pick(style.accent, self._dark))

        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            screen_cx = geo.x() + geo.width() / 2.0
            screen_cy = geo.y() + geo.height() / 2.0
            pill_cx = self.x() + self.width() / 2.0
            pill_cy = self.y() + self.height() / 2.0
            # Vector pointing from pill towards screen center
            screen_center_delta = (screen_cx - pill_cx, screen_cy - pill_cy)
        else:
            screen_center_delta = None

        dpr = max(1.0, float(self.devicePixelRatioF() or 1.0))
        self._liquid_image = shader_engine.render(
            self._bg_pixmap, w, h,
            dark=self._dark,
            accent_color=accent,
            ripple_phase=self._ripple_phase,
            screen_center_delta=screen_center_delta,
            supersample_factor=int(round(dpr * 2))
        )

    def set_state(self, state: str, detail: str = ""):
        if state not in theme.STATES:
            state = "idle"
        prev_style = theme.STATES.get(self._state, theme.STATES["idle"])
        style = theme.STATES[state]
        self._state = state
        if state == "recording":
            tip = "Dictate — Listening…\nClick pill to stop & transcribe"
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

        if style.width != int(self._width):
            self._start_morph(style.width)

        if state in ("transcribing", "loading"):
            if self._pulse_anim.state() != QVariantAnimation.State.Running:
                self._pulse_anim.start()
        else:
            self._pulse_anim.stop()
            self._pulse = 1.0

        if state == "recording":
            if not self._vis_timer.isActive():
                self._vis_timer.start()
        else:
            if self._vis_timer.isActive():
                self._vis_timer.stop()
            self._level = 0.0

        if state == "error" and prev_style is not style:
            self._shake_anim.stop()
            self._shake_anim.start()

        self._execute_shader_pass()
        self.update()

    def _start_morph(self, target_width: int):
        self._morph_anim.stop()
        self._morph_anim.setStartValue(self._width)
        self._morph_anim.setEndValue(float(target_width))
        growing = target_width > self._width
        self._morph_anim.setDuration(theme.MORPH_DURATION_MS if growing else theme.EXIT_DURATION_MS)
        self._morph_anim.setEasingCurve(self._morph_easing if growing else QEasingCurve.Type.OutCubic)
        self._morph_anim.start()

    def _on_morph_value(self, value):
        self._width = float(value)
        center = self.geometry().center()
        w = max(1, round(self._width))
        rect = QRect(0, 0, w, theme.PILL_HEIGHT)
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
        self._ripple_phase += 0.025 * RIPPLE_SPEED
        self._execute_shader_pass()
        self.update()

    def set_level(self, rms: float):
        """Update live input audio level for the 5-bar waveform."""
        scaled = max(0.0, min(1.0, float(rms) * 14.0))
        self._target_level = scaled

    # ---- Painting: Liquid Glass Shader Composition & Vector State Glyphs ----

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
            radius = min(h / 2.0, w / 2.0)
            p.setPen(QPen(QColor(255, 255, 255, 60), 1.0))
            p.setBrush(QColor(30, 41, 59, 180) if self._dark else QColor(255, 255, 255, 200))
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        # 2. RENDER HIGH-CONTRAST FOREGROUND STATE GLYPHS / EQUALIZER
        self._paint_state_content(p, accent, rect)

        p.end()

    def _paint_state_content(self, p: QPainter, accent: QColor, rect: QRectF):
        cx = rect.center().x()
        cy = rect.center().y()
        state = self._state

        if state == "recording":
            # Glowing Left Microphone
            mic_cx = rect.left() + 20
            mic_color = QColor(accent)
            mic_color.setAlphaF(min(1.0, 0.92 + 0.08 * math.sin(time.time() * 6)))
            self._draw_mic_glyph(p, mic_color, mic_cx, cy, scale=0.85)

            # 5-Bar Dynamic Fluid Waveform Equalizer (Silky Smooth Subpixel Float Bars)
            waveform_x = rect.left() + 42
            p.setPen(Qt.PenStyle.NoPen)
            num_bars = 5
            spacing = 11.0
            t = time.time() * 8

            for i in range(num_bars):
                bx = waveform_x + i * spacing
                phase = math.sin(t + i * 1.2) * 0.35 + 0.65
                h = 4.0 + (20.0 * self._level * phase)
                h = max(3.0, min(24.0, h))

                bar_color = QColor(accent)
                if i in (1, 3):
                    bar_color = bar_color.lighter(115)
                bar_color.setAlphaF(0.92 + 0.08 * (h / 24.0))
                p.setBrush(bar_color)
                p.drawRoundedRect(QRectF(bx - 1.5, cy - h / 2.0, 3.0, h), 1.5, 1.5)

        elif state == "transcribing":
            # 3 Orbiting / Breathing Pulsing Wave Dots
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            dot_offsets = (-9.0, 0.0, 9.0)
            t = time.time() * 6
            for i, dx in enumerate(dot_offsets):
                wave = math.sin(t + i * 1.2) * 0.5 + 0.5
                r = 2.0 + 1.8 * wave
                dot_color = QColor(accent)
                dot_color.setAlphaF(0.55 + 0.45 * wave)
                p.setBrush(dot_color)
                p.drawEllipse(QPointF(cx + dx, cy), r, r)

        elif state == "injecting":
            # Emerald Checkmark
            p.setPen(QPen(accent, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(cx - 5.5, cy + 0.5), QPointF(cx - 1.5, cy + 4.5))
            p.drawLine(QPointF(cx - 1.5, cy + 4.5), QPointF(cx + 6.0, cy - 4.5))

        elif state == "loading":
            # Minimalist Rotating Arc
            p.setPen(QPen(accent, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            arc_rect = QRectF(cx - 7.0, cy - 7.0, 14.0, 14.0)
            start_angle = int((time.time() * 240) % 360) * 16
            p.drawArc(arc_rect, start_angle, 220 * 16)

        elif state == "error":
            # Exclamation Mark
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
        self._execute_shader_pass()
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hovered = False
        self._execute_shader_pass()
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
        m.addAction("Copy last transcript", self.copy_last_requested.emit)
        m.addAction("Transcript history…", self.history_requested.emit)
        m.addSeparator()
        m.addAction("Settings…", self.settings_requested.emit)
        m.addSeparator()
        m.addAction("Quit", self.quit_requested.emit)
        m.exec(global_pos)
