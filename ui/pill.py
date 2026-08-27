"""The floating always-on-top Shape-Shifting Apple Liquid Glass Pill widget.

Integrates a two-pass real-time shader pipeline:
- Pass 1: Screen-space backdrop buffer capture using Windows GDI / QScreen with WDA_EXCLUDEFROMCAPTURE
- Pass 2: Liquid glass fragment shader with Snell's law refraction, edge lensing, Cauchy chromatic dispersion,
  Blinn-Phong multi-light specular glints, dynamic screen-center tracking, custom corner radius, and 2x Retina HD subpixel supersampling.
- Pass 3: Unified Spotify-style recording widget with pure neutral obsidian glass:
  - Top 1/3: Microphone glyph + 5-bar dynamic fluid waveform equalizer in Ice Cyan / Rose.
  - Bottom 2/3: 3-Card Carousel Pipeline (100% transparent glass):
    - Max 3 cards visible at any time.
    - New words come in focus from the right (Slot 2).
    - Older words glide left into intermediate focus (Slot 1), then left out of focus (Slot 0).
    - Exiting words smoothly slide and fade out to the left (Slot -1).
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
    QRadialGradient,
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

    MAX_VISIBLE_CARDS = 3

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

        # 3-Card Carousel Pipeline state: list of dicts {"word": str, "from_slot": float, "to_slot": float}
        self._cards: list[dict] = []
        self._card_anim_progress: float = 1.0

        self._bg_pixmap = None
        self._liquid_image = None

        style = theme.STATES["idle"]
        self._width = float(style.width)
        self._height = float(style.height)
        self.resize(style.width, style.height)

        # 2D Geometry Morphing Animation (Animates width & height smoothly from center)
        self._morph_start_w = self._width
        self._morph_target_w = self._width
        self._morph_start_h = self._height
        self._morph_target_h = self._height

        self._morph_anim = QVariantAnimation(self)
        self._morph_anim.valueChanged.connect(self._on_morph_progress)
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

        # 3-Card Carousel shift animation: right-to-left focus glide & exit
        self._card_anim = QVariantAnimation(self)
        self._card_anim.setDuration(160)
        self._card_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._card_anim.valueChanged.connect(self._on_card_anim_tick)
        self._card_anim.finished.connect(self._on_card_anim_finished)

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
        """Pass 2: Evaluate liquid glass fragment shader over captured backdrop buffer with screen-center lighting, custom corner radius & 2x HD supersampling."""
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
            # Vector pointing from pill towards screen center
            screen_center_delta = (screen_cx - pill_cx, screen_cy - pill_cy)
        else:
            screen_center_delta = None

        dpr = max(1.0, float(self.devicePixelRatioF() or 1.0))
        is_rec = self._state in ("recording", "preview")
        corner_r = theme.CORNER_RADIUS_RECORDING if is_rec else theme.CORNER_RADIUS_IDLE
        black_tint = 0.40 if is_rec else 0.0
        # Pure neutral obsidian glass for recording background (zero red tint bleed)
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

    # ---- 3-Card Carousel Pipeline (Right Focus -> Left Exit) ----------------

    def update_preview(self, text: str):
        """Update live transcript words: max 3 cards enter in focus from the right and exit out from the left."""
        words = [w.strip() for w in text.strip().split() if w.strip()]
        if not words:
            return

        new_word = words[-1]
        # Skip if the new word is already the in-focus target card
        if self._cards and self._cards[-1]["word"] == new_word and self._cards[-1]["to_slot"] == 2.0:
            return

        # Settle any current in-flight animation before starting next shift
        if self._card_anim.state() == QVariantAnimation.State.Running:
            for c in self._cards:
                c["from_slot"] = c["to_slot"]
            self._cards = [c for c in self._cards if c["to_slot"] >= 0.0]

        # Shift all existing cards left by 1 slot (2 -> 1, 1 -> 0, 0 -> -1 Exit)
        for c in self._cards:
            c["from_slot"] = c["to_slot"]
            c["to_slot"] -= 1.0

        # Push the incoming new card from the right (Slot 3 -> Slot 2 Focus)
        self._cards.append({
            "word": new_word,
            "from_slot": 3.0,
            "to_slot": 2.0
        })

        # Remove cards that have already moved beyond exit threshold
        self._cards = [c for c in self._cards if c["to_slot"] >= -1.0]

        # Trigger fast smooth shift animation
        self._card_anim.stop()
        self._card_anim.setStartValue(0.0)
        self._card_anim.setEndValue(1.0)
        self._card_anim.start()

        if self._state not in ("recording", "preview"):
            self.set_state("recording", "Listening…")
        else:
            self._execute_shader_pass()
            self.update()

    def clear_preview(self):
        """Reset carousel cards and stop animations."""
        self._cards.clear()
        self._card_anim.stop()
        self._card_anim_progress = 1.0
        self.update()

    def _on_card_anim_tick(self, value):
        self._card_anim_progress = float(value)
        self.update()

    def _on_card_anim_finished(self):
        for c in self._cards:
            c["from_slot"] = c["to_slot"]
        # Drop exited cards (slot <= -1.0) and enforce max 3 cards
        self._cards = [c for c in self._cards if c["to_slot"] >= 0.0]
        self._cards = self._cards[-self.MAX_VISIBLE_CARDS:]
        self._card_anim_progress = 1.0
        self.update()

    # ---- State Machine & 2D Symmetrical Morphing ---------------------------

    def set_state(self, state: str, detail: str = ""):
        if state not in theme.STATES:
            state = "idle"
        prev_style = theme.STATES.get(self._state, theme.STATES["idle"])
        style = theme.STATES[state]
        self._state = state

        if state in ("recording", "preview"):
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

        # Clear cards when leaving recording / preview
        if state not in ("recording", "preview"):
            self.clear_preview()

        target_w = style.width
        target_h = style.height
        if target_w != int(self._width) or target_h != int(self._height):
            self._start_morph(target_w, target_h)

        if state in ("transcribing", "loading"):
            if self._pulse_anim.state() != QVariantAnimation.State.Running:
                self._pulse_anim.start()
        else:
            self._pulse_anim.stop()
            self._pulse = 1.0

        if state in ("recording", "preview"):
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

    def _start_morph(self, target_width: int, target_height: int):
        self._morph_anim.stop()
        self._morph_start_w = self._width
        self._morph_target_w = float(target_width)
        self._morph_start_h = self._height
        self._morph_target_h = float(target_height)

        growing = (target_width > self._width) or (target_height > self._height)
        self._morph_anim.setDuration(theme.MORPH_DURATION_MS if growing else theme.EXIT_DURATION_MS)
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
        self._ripple_phase += 0.025 * RIPPLE_SPEED
        self._execute_shader_pass()
        self.update()

    def set_level(self, rms: float):
        """Update live input audio level for the dynamic fluid waveform bars."""
        scaled = max(0.0, min(1.0, float(rms) * 14.0))
        self._target_level = scaled

    # ---- Painting: Liquid Glass Composition & Unified Spotify-Style Layout -

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
            radius = theme.CORNER_RADIUS_RECORDING if self._state in ("recording", "preview") else min(h / 2.0, w / 2.0)
            p.setPen(QPen(QColor(255, 255, 255, 60), 1.0))
            p.setBrush(QColor(15, 23, 42, 220) if self._dark else QColor(255, 255, 255, 200))
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        # 2. RENDER FOREGROUND CONTENT
        self._paint_state_content(p, accent, rect)

        p.end()

    def _paint_state_content(self, p: QPainter, accent: QColor, rect: QRectF):
        cx = rect.center().x()
        cy = rect.center().y()
        w = rect.width()
        h = rect.height()
        state = self._state

        if state in ("recording", "preview"):
            # UNIFIED SPOTIFY-STYLE LAYOUT:
            # -------------------------------------------------------------
            # Top 1/3 (y: 0 to ~38): Microphone + 5-Bar Dynamic Waveform
            # -------------------------------------------------------------
            top_cy = 20.0

            # 1. Glowing Microphone Icon on left
            mic_cx = 28.0
            mic_color = QColor(accent)
            mic_color.setAlphaF(min(1.0, 0.92 + 0.08 * math.sin(time.time() * 6)))
            self._draw_mic_glyph(p, mic_color, mic_cx, top_cy, scale=0.76)

            # 2. 5-Bar Dynamic Fluid Waveform Equalizer (reacts to audio level)
            waveform_cx = w / 2.0
            p.setPen(Qt.PenStyle.NoPen)
            num_bars = 5
            spacing = 9.0
            start_bx = waveform_cx - (num_bars - 1) * spacing / 2.0
            t = time.time() * 8

            for i in range(num_bars):
                bx = start_bx + i * spacing
                phase = math.sin(t + i * 1.2) * 0.35 + 0.65
                bar_h = 4.0 + (18.0 * self._level * phase)
                bar_h = max(3.5, min(22.0, bar_h))

                bar_color = QColor(accent)
                if i in (1, 3):
                    bar_color = bar_color.lighter(120)
                bar_color.setAlphaF(0.92 + 0.08 * (bar_h / 22.0))
                p.setBrush(bar_color)
                p.drawRoundedRect(QRectF(bx - 1.5, top_cy - bar_h / 2.0, 3.0, bar_h), 1.5, 1.5)

            # 3. Right Status Indicator Dot
            status_dot_cx = w - 28.0
            p.setBrush(mic_color)
            p.drawEllipse(QPointF(status_dot_cx, top_cy), 2.5, 2.5)

            # 4. Subtle Hairline Separator between Top 1/3 and Bottom 2/3
            sep_y = 37.0
            sep_grad = QLinearGradient(24.0, sep_y, w - 24.0, sep_y)
            sep_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            sep_grad.setColorAt(0.5, QColor(255, 255, 255, 30 if self._dark else 18))
            sep_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setPen(QPen(QBrush(sep_grad), 1.0))
            p.drawLine(QPointF(24.0, sep_y), QPointF(w - 24.0, sep_y))

            # -------------------------------------------------------------
            # Bottom 2/3 (y: 38 to 102): 3-Card Carousel Pipeline
            # -------------------------------------------------------------
            self._paint_card_carousel(p, accent, rect)

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

    def _paint_card_carousel(self, p: QPainter, accent: QColor, rect: QRectF):
        """Renders at max 3 cards: entering in focus from the right and exiting out from the left (100% transparent glass)."""
        w = rect.width()
        h = rect.height()
        deck_cy = 68.0

        if not self._cards:
            p.save()
            font_prompt = QFont("Segoe UI Variable Text", 9, QFont.Weight.Medium)
            font_prompt.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            p.setFont(font_prompt)
            p.setPen(QColor(148, 163, 184, 140) if self._dark else QColor(100, 116, 139, 140))
            prompt_rect = QRectF(16.0, 40.0, w - 32.0, h - 46.0)
            p.drawText(prompt_rect, Qt.AlignmentFlag.AlignCenter, "Listening… speak naturally")
            p.restore()
            return

        font_past = QFont("Segoe UI Variable Text", 9, QFont.Weight.Normal)
        font_past.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        fm_past = QFontMetrics(font_past)

        font_main = QFont("Segoe UI Variable Text", 10, QFont.Weight.Bold)
        font_main.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        fm_main = QFontMetrics(font_main)

        # Clip deck area to pill interior
        deck_clip_rect = QRectF(14.0, 38.0, w - 28.0, h - 42.0)
        p.save()
        clip_path = QPainterPath()
        clip_path.addRect(deck_clip_rect)
        p.setClipPath(clip_path)

        left_margin = 22.0
        right_margin = w - 22.0
        t_prog = self._card_anim_progress

        for card in self._cards:
            word = card["word"]
            # Current fractional slot position along the pipeline
            s = card["from_slot"] + (card["to_slot"] - card["from_slot"]) * t_prog

            # Slot geometry anchors:
            # Slot -1.0: Exited off left
            # Slot  0.0: Left / Oldest visible card
            # Slot  1.0: Middle / Intermediate card
            # Slot  2.0: Right / IN FOCUS current active card
            # Slot  3.0: Incoming off right

            cw_focus = max(86.0, fm_main.horizontalAdvance(word) + 26.0)
            cw_mid = max(58.0, fm_past.horizontalAdvance(word) + 18.0)
            cw_left = max(48.0, fm_past.horizontalAdvance(word) + 14.0)

            cx_focus = right_margin - cw_focus
            cx_left = left_margin
            cx_mid = left_margin + (right_margin - left_margin - cw_mid) * 0.44

            # Piece-wise interpolation across pipeline slots
            if s <= 0.0:
                frac = max(0.0, min(1.0, s + 1.0))
                cx = -70.0 + (cx_left - (-70.0)) * frac
                cw = 44.0 + (cw_left - 44.0) * frac
                ch = 20.0 + (24.0 - 20.0) * frac
                alpha = int(0 + (190 - 0) * frac)
                border_a = int(0 + (45 - 0) * frac)
                scale = 0.75 + (0.85 - 0.75) * frac
                font = font_past
                is_focus = False

                # Slot 0 -> Slot -1: Lightest grey fading out
                bg_r = 95.0
                bg_g = 105.0
                bg_b = 125.0
                bg_a = int(170.0 * frac)
            elif s <= 1.0:
                frac = s
                cx = cx_left + (cx_mid - cx_left) * frac
                cw = cw_left + (cw_mid - cw_left) * frac
                ch = 24.0 + (28.0 - 24.0) * frac
                alpha = int(190 + (225 - 190) * frac)
                border_a = int(45 + (85 - 45) * frac)
                scale = 0.85 + (0.93 - 0.85) * frac
                font = font_past
                is_focus = False

                # Slot 0 (Lightest grey) -> Slot 1 (Second darkest)
                bg_r = 95.0 + (45.0 - 95.0) * frac
                bg_g = 105.0 + (52.0 - 105.0) * frac
                bg_b = 125.0 + (68.0 - 125.0) * frac
                bg_a = int(170.0 + (200.0 - 170.0) * frac)
            elif s <= 2.0:
                frac = s - 1.0
                cx = cx_mid + (cx_focus - cx_mid) * frac
                cw = cw_mid + (cw_focus - cw_mid) * frac
                ch = 28.0 + (34.0 - 28.0) * frac
                alpha = int(225 + (255 - 225) * frac)
                border_a = int(85 + (210 - 85) * frac)
                scale = 0.93 + (1.0 - 0.93) * frac
                font = font_main if frac > 0.4 else font_past
                is_focus = (frac > 0.6)

                # Slot 1 (Second darkest) -> Slot 2 (Darkest active card)
                bg_r = 45.0 + (15.0 - 45.0) * frac
                bg_g = 52.0 + (20.0 - 52.0) * frac
                bg_b = 68.0 + (30.0 - 68.0) * frac
                bg_a = int(200.0 + (235.0 - 200.0) * frac)
            else:
                frac = s - 2.0
                cx = cx_focus + ((w + 40.0) - cx_focus) * frac
                cw = cw_focus
                ch = 34.0
                alpha = int(255 * max(0.0, 1.0 - frac))
                border_a = int(210 * max(0.0, 1.0 - frac))
                scale = 1.0
                font = font_main
                is_focus = True

                # Slot 3 (Incoming) -> Slot 2 (Darkest active card)
                bg_r = 15.0
                bg_g = 20.0
                bg_b = 30.0
                bg_a = int(235.0 * max(0.0, 1.0 - frac))

            if alpha <= 0 or bg_a <= 0:
                continue

            bg_color = QColor(int(bg_r), int(bg_g), int(bg_b), bg_a)
            cy = deck_cy - ch / 2.0
            card_rect = QRectF(cx, cy, cw, ch)
            self._draw_single_glass_card(p, card_rect, word, font, scale, alpha, border_a, bg_color, is_focus)

        p.restore()

    def _draw_single_glass_card(self, p: QPainter, card_rect: QRectF, word: str, font: QFont,
                                scale: float, alpha: int, border_a: int, bg_color: QColor, is_focus: bool):
        """Helper to render a glass card element with progressive grayscale background shading."""
        card_cx = card_rect.center().x()
        card_cy = card_rect.center().y()
        radius = 8.5 if is_focus else 7.0

        p.save()
        p.setFont(font)

        # Scale transformation around card center
        p.translate(card_cx, card_cy)
        p.scale(scale, scale)
        p.translate(-card_cx, -card_cy)

        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, radius, radius)

        # 1. Grayscale Shaded Background Fill (Darkest on active -> Lighter greys on past cards)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg_color)
        p.drawPath(card_path)

        # 2. Glass Hairline Rim Border
        if self._dark:
            border_color = QColor(255, 255, 255, border_a)
            text_color = QColor(255, 255, 255, alpha)
        else:
            border_color = QColor(0, 0, 0, border_a)
            text_color = QColor(255, 255, 255, alpha) if is_focus else QColor(15, 23, 42, alpha)

        border_width = 1.2 if is_focus else 1.0
        p.setPen(QPen(border_color, border_width))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(card_path)

        # 3. Liquid-Crystal Typography
        p.setPen(text_color)
        p.drawText(card_rect, Qt.AlignmentFlag.AlignCenter, word)

        p.restore()

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
