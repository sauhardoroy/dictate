"""The floating always-on-top Shape-Shifting Monochrome Material Pill widget.

A flat, matte, minimalist heads-up display adhering to Dictate's Material 3
Monochrome design language:
- Flat matte fill (t.surface_container_high) + 1px hairline border (t.outline).
- Pure shape and motion over color: all states (idle, transcribing, inserted, loading)
  use monochrome tonal hierarchy, with desaturated signal_recording / signal_error
  reserved exclusively for the live recording indicator dot and error state.
- Symmetrical 2D size morphing re-timed on material_theme.MOTION standard (220ms, OutCubic).
- Zero focus-stealing (WS_EX_NOACTIVATE) and capture exclusion (WDA_EXCLUDEFROMCAPTURE).
"""
from __future__ import annotations

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
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from ui.material_theme import (
    FONT_FAMILY,
    HUD_STATES,
    MOTION,
    Tokens,
    build_qss,
    get_tokens,
    is_system_dark_mode,
)

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


# Visualizer smoothing constant
METER_SMOOTHING = 0.35
SHAKE_DURATION_MS = 240
SHAKE_DISTANCE_PX = 3


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

        self._dark = is_system_dark_mode()
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
        self._live_transcript = ""

        style = HUD_STATES["idle"]
        self._width = float(style.width)
        self._height = float(style.height)
        self.resize(style.width, style.height)

        # 2D Geometry Morphing Animation
        self._morph_start_w = self._width
        self._morph_target_w = self._width
        self._morph_start_h = self._height
        self._morph_target_h = self._height

        self._morph_anim = QVariantAnimation(self)
        self._morph_anim.valueChanged.connect(self._on_morph_progress)
        self._morph_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Pulse animation for transcribing/loading
        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setStartValue(0.40)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setDuration(800)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.valueChanged.connect(self._on_pulse_value)

        # Shake animation for error
        self._shake_anim = QVariantAnimation(self)
        self._shake_anim.setDuration(SHAKE_DURATION_MS)
        self._shake_anim.setKeyValueAt(0.0, 0)
        self._shake_anim.setKeyValueAt(0.2, -SHAKE_DISTANCE_PX)
        self._shake_anim.setKeyValueAt(0.4, SHAKE_DISTANCE_PX)
        self._shake_anim.setKeyValueAt(0.6, -SHAKE_DISTANCE_PX)
        self._shake_anim.setKeyValueAt(0.8, SHAKE_DISTANCE_PX)
        self._shake_anim.setKeyValueAt(1.0, 0)
        self._shake_anim.valueChanged.connect(self._on_shake_value)

        # Visualizer tick timer
        self._vis_timer = QTimer(self)
        self._vis_timer.setInterval(16)
        self._vis_timer.timeout.connect(self._on_vis_tick)

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

    # ---- State Machine & Morphing ------------------------------------------

    def set_state(self, state: str, detail: str = ""):
        if state not in HUD_STATES:
            state = "idle"
        prev_style = HUD_STATES.get(self._state, HUD_STATES["idle"])
        style = HUD_STATES[state]
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

        # Trigger Morph if dimensions changed
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

        # Visualizer tick timer
        if state in ("recording", "preview"):
            if not self._vis_timer.isActive():
                self._vis_timer.start()
        else:
            if self._vis_timer.isActive():
                self._vis_timer.stop()
            self._level = 0.0

        # Shake on error
        if state == "error" and prev_style is not style:
            self._shake_anim.stop()
            self._shake_anim.start()

        self.update()

    def _start_morph(self, target_width: int, target_height: int):
        self._morph_anim.stop()
        self._morph_start_w = self._width
        self._morph_target_w = float(target_width)
        self._morph_start_h = self._height
        self._morph_target_h = float(target_height)

        growing = (target_width > self._width) or (target_height > self._height)
        self._morph_anim.setDuration(MOTION["standard"] if growing else MOTION["fast"])
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
        self._level += (self._target_level - self._level) * METER_SMOOTHING
        self.update()

    def set_level(self, rms: float):
        """Update live input audio level for the 5-bar dynamic fluid waveform."""
        scaled = max(0.0, min(1.0, float(rms) * 12.0))
        self._target_level = scaled

    # ---- Painting: Flat Matte Monochrome Pill -----------------------------

    def paintEvent(self, _event):
        t = get_tokens(self._dark)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        rect = QRectF(0.0, 0.0, float(w), float(h))
        corner_radius = min(float(w), float(h)) / 2.0

        # Pass 1: Flat Matte Surface Fill + Hairline Outline
        p.setPen(QPen(QColor(t.outline), 1.0))
        p.setBrush(QColor(t.surface_container_high))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), corner_radius, corner_radius)

        # Pass 2: State Content
        self._paint_state_content(p, t, rect)

        p.end()

    def _paint_state_content(self, p: QPainter, t: Tokens, rect: QRectF):
        cx = rect.center().x()
        cy = rect.center().y()
        w = rect.width()
        h = rect.height()
        state = self._state

        if state in ("recording", "preview"):
            # -------------------------------------------------------------
            # Top Row (y = 22): Signal Dot + 5-Bar Grayscale Meter + Status Dot
            # -------------------------------------------------------------
            top_cy = 22.0

            # 1. Left Recording Dot in reserved signal tone
            dot_color = QColor(t.signal_recording)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot_color)
            p.drawEllipse(QPointF(28.0, top_cy), 3.5, 3.5)

            # 2. 5-Bar Dynamic Waveform in on_surface grayscale (no per-bar color)
            waveform_cx = w / 2.0
            num_bars = 5
            spacing = 8.5
            start_bx = waveform_cx - (num_bars - 1) * spacing / 2.0
            now = time.time() * 7

            for i in range(num_bars):
                bx = start_bx + i * spacing
                phase = math.sin(now + i * 1.2) * 0.35 + 0.65
                bar_h = 3.5 + (16.0 * self._level * phase)
                bar_h = max(3.0, min(18.0, bar_h))

                bar_color = QColor(t.on_surface)
                if i in (1, 3):
                    bar_color = QColor(t.on_surface_variant)
                bar_color.setAlphaF(0.85 + 0.15 * (bar_h / 18.0))
                p.setBrush(bar_color)
                p.drawRoundedRect(QRectF(bx - 1.5, top_cy - bar_h / 2.0, 3.0, bar_h), 1.5, 1.5)

            # 3. Right Status Indicator Dot in signal tone
            p.setBrush(dot_color)
            p.drawEllipse(QPointF(w - 28.0, top_cy), 2.5, 2.5)

            # 4. Hairline Separator
            sep_y = 36.0
            p.setPen(QPen(QColor(t.outline_variant), 1.0))
            p.drawLine(QPointF(20.0, sep_y), QPointF(w - 20.0, sep_y))

            # -------------------------------------------------------------
            # Bottom Area (y: 38 to 74): High-Contrast Live Transcript Text
            # -------------------------------------------------------------
            p.save()
            text_rect = QRectF(18.0, 38.0, w - 36.0, 30.0)
            clip_path = QPainterPath()
            clip_path.addRect(text_rect)
            p.setClipPath(clip_path)

            font_live = QFont("Segoe UI Variable Display")
            font_live.setPixelSize(13)
            font_live.setWeight(QFont.Weight.DemiBold)
            p.setFont(font_live)

            if self._live_transcript:
                fm = QFontMetrics(font_live)
                text_w = fm.horizontalAdvance(self._live_transcript)

                if text_w > (w - 40.0):
                    draw_x = (w - 20.0) - text_w
                else:
                    draw_x = (w - text_w) / 2.0

                p.setPen(QColor(t.on_surface))
                p.drawText(QRectF(draw_x, 38.0, text_w + 10.0, 30.0), Qt.AlignmentFlag.AlignVCenter, self._live_transcript)
            else:
                font_hint = QFont("Segoe UI Variable Display")
                font_hint.setPixelSize(12)
                font_hint.setWeight(QFont.Weight.Medium)
                p.setFont(font_hint)
                p.setPen(QColor(t.on_surface_muted))
                p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Listening… speak naturally")

            p.restore()

        elif state == "transcribing":
            # 3 Breathing Dots in on_surface_muted (opacity pulse) + "Processing" label
            p.setPen(Qt.PenStyle.NoPen)
            dot_start_x = cx - 36.0
            now = time.time() * 5
            for i in range(3):
                wave = math.sin(now + i * 1.1) * 0.5 + 0.5
                r = 2.0 + 1.0 * wave
                dot_color = QColor(t.on_surface_muted)
                dot_color.setAlphaF(0.35 + 0.65 * wave * self._pulse)
                p.setBrush(dot_color)
                p.drawEllipse(QPointF(dot_start_x + i * 8.0, cy), r, r)

            # Processing Label in on_surface
            f = QFont("Segoe UI Variable Display")
            f.setPixelSize(12)
            f.setWeight(QFont.Weight.DemiBold)
            p.setFont(f)
            p.setPen(QColor(t.on_surface))
            p.drawText(QRectF(cx - 8.0, 0, w / 2.0 + 8.0, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Processing")

        elif state == "injecting":
            # Static Checkmark + "Inserted" Label
            p.setPen(QPen(QColor(t.on_surface), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            check_x = cx - 28.0
            p.drawLine(QPointF(check_x - 4.5, cy), QPointF(check_x - 1.0, cy + 3.5))
            p.drawLine(QPointF(check_x - 1.0, cy + 3.5), QPointF(check_x + 5.0, cy - 3.5))

            f = QFont("Segoe UI Variable Display")
            f.setPixelSize(12)
            f.setWeight(QFont.Weight.DemiBold)
            p.setFont(f)
            p.setPen(QColor(t.on_surface))
            p.drawText(QRectF(cx - 14.0, 0, w / 2.0 + 14.0, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Inserted")

        elif state == "loading":
            # Rotating Arc in on_surface_muted
            p.setPen(QPen(QColor(t.on_surface_muted), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            arc_rect = QRectF(cx - 7.0, cy - 7.0, 14.0, 14.0)
            start_angle = int((time.time() * 240) % 360) * 16
            p.drawArc(arc_rect, start_angle, 220 * 16)

        elif state == "error":
            # Exclamation Glyph in reserved signal_error tone
            err_color = QColor(t.signal_error)
            p.setPen(QPen(err_color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx, cy - 6.0), QPointF(cx, cy + 1.0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(err_color)
            p.drawEllipse(QPointF(cx, cy + 5.0), 1.4, 1.4)

        else:
            # Idle: Centered Microphone Glyph in on_surface_variant (or on_surface if hovered)
            mic_color = QColor(t.on_surface if self._hovered else t.on_surface_variant)
            self._draw_mic_glyph(p, mic_color, cx, cy, scale=1.0)

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
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hovered = False
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
                self.geometry_changed.emit()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._dragged:
                self.position_changed.emit(self.x(), self.y())
            else:
                self.toggle_requested.emit()
        self._press_pos = None
        self._dragged = False

    def _menu(self, global_pos: QPoint):
        m = QMenu(self)
        t = get_tokens(self._dark)
        m.setStyleSheet(build_qss(t))
        m.addAction("Copy Last Transcript", self.copy_last_requested.emit)
        m.addAction("Transcript History…", self.history_requested.emit)
        m.addSeparator()
        m.addAction("Settings…", self.settings_requested.emit)
        m.addSeparator()
        m.addAction("Quit Dictate", self.quit_requested.emit)
        m.exec(global_pos)
