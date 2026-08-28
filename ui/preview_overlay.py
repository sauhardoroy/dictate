"""The floating always-on-top live transcript preview overlay.

Displays a real-time, free-flowing 4-word sliding window as words are spoken:
the active (latest) word is displayed in bold on_surface text, while previous
words gently fade in on_surface_variant / on_surface_muted.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QVariantAnimation,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QApplication, QWidget

from ui.material_theme import (
    FONT_FAMILY,
    MOTION,
    Tokens,
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


class PreviewOverlay(QWidget):
    OVERLAY_WIDTH = 300
    OVERLAY_HEIGHT = 34
    CORNER_RADIUS = 17
    MAX_VISIBLE_WORDS = 4

    def __init__(self, dark: bool = None, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._dark = is_system_dark_mode() if dark is None else dark
        self._opacity = 0.0
        self._target_pos = None
        self._is_showing = False

        self._display_words: list[str] = []

        self.setFixedSize(self.OVERLAY_WIDTH, self.OVERLAY_HEIGHT)

        self._fade_anim = QVariantAnimation(self)
        self._fade_anim.valueChanged.connect(self._on_fade_value)
        self._fade_anim.finished.connect(self._on_fade_finished)

        self.hide()

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

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_native_flags()

    def set_dark_mode(self, dark: bool):
        self._dark = dark
        self.update()

    def set_text(self, text: str):
        """Update live 4-word preview directly from incoming streaming transcript."""
        raw_words = [w.strip() for w in text.strip().split() if w.strip()]
        if not raw_words:
            return

        new_window = raw_words[-self.MAX_VISIBLE_WORDS:]
        if new_window == self._display_words and self._is_showing:
            return

        self._display_words = new_window

        if not self._is_showing:
            self.show_animated()
        else:
            self.update()

    def clear(self):
        """Reset streaming state."""
        self._display_words.clear()
        self.update()

    def reposition(self, pill_geo: QRect):
        """Position the overlay centered below the pill, or above if close to screen bottom."""
        screen = QApplication.screenAt(pill_geo.center()) or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        target_x = pill_geo.x() + (pill_geo.width() - self.OVERLAY_WIDTH) // 2
        target_x = max(geo.left() + 10, min(target_x, geo.right() - self.OVERLAY_WIDTH - 10))

        # Prefer 8px below the pill
        target_y = pill_geo.y() + pill_geo.height() + 8
        # If it overflows screen bottom, flip to 8px above pill
        if target_y + self.OVERLAY_HEIGHT > geo.bottom() - 6:
            target_y = pill_geo.y() - self.OVERLAY_HEIGHT - 8

        self._target_pos = (target_x, target_y)
        if not self._fade_anim.state() == QVariantAnimation.State.Running:
            self.move(target_x, target_y)

    def show_animated(self):
        self._is_showing = True
        self._fade_anim.stop()

        if self._target_pos:
            self.move(self._target_pos[0], self._target_pos[1])

        self.show()
        self._apply_native_flags()

        self._fade_anim.setDuration(MOTION["standard"])
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

    def hide_animated(self):
        if not self._is_showing and self._opacity == 0.0:
            return
        self._is_showing = False
        self._fade_anim.stop()
        self._fade_anim.setDuration(MOTION["fast"])
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_anim.start()

    def _on_fade_value(self, val: float):
        self._opacity = val
        self.update()

    def _on_fade_finished(self):
        if not self._is_showing:
            self.clear()
            self.hide()

    def paintEvent(self, _event):
        if self._opacity <= 0.001 or not self._display_words:
            return

        t = get_tokens(self._dark)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        r = float(self.CORNER_RADIUS)

        path = QPainterPath()
        path.addRoundedRect(rect, r, r)

        # Background Flat Surface Fill + Outline (scaled with opacity)
        bg_col = QColor(t.surface_container_low)
        bg_col.setAlphaF(min(1.0, 0.95 * self._opacity))
        border_col = QColor(t.outline)
        border_col.setAlphaF(min(1.0, 0.70 * self._opacity))

        p.fillPath(path, bg_col)
        p.strokePath(path, QPen(border_col, 1.0))

        # Left mic indicator dot in reserved signal_recording tone
        dot_col = QColor(t.signal_recording)
        dot_col.setAlphaF(min(1.0, self._opacity))
        dot_cx = 15.0
        dot_cy = h / 2.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(dot_col)
        p.drawEllipse(QPointF(dot_cx, dot_cy), 2.5, 2.5)

        # Draw 4 words with progressive opacity fade
        words = self._display_words
        num_words = len(words)

        font_normal = QFont("Segoe UI Variable Display", 9)
        font_normal.setWeight(QFont.Weight.Normal)

        font_active = QFont("Segoe UI Variable Display", 9)
        font_active.setWeight(QFont.Weight.DemiBold)

        fm_normal = QFontMetrics(font_normal)
        fm_active = QFontMetrics(font_active)

        word_widths = []
        for i, word in enumerate(words):
            is_latest = (i == num_words - 1)
            fm = fm_active if is_latest else fm_normal
            word_widths.append(fm.horizontalAdvance(word))

        space_w = 6.0
        start_x = 26.0

        cur_x = start_x
        for i, word in enumerate(words):
            dist_from_latest = num_words - 1 - i
            is_latest = (dist_from_latest == 0)

            if is_latest:
                w_col = QColor(t.on_surface)
                w_col.setAlphaF(min(1.0, self._opacity))
                p.setFont(font_active)
            elif dist_from_latest == 1:
                w_col = QColor(t.on_surface_variant)
                w_col.setAlphaF(min(1.0, 0.85 * self._opacity))
                p.setFont(font_normal)
            elif dist_from_latest == 2:
                w_col = QColor(t.on_surface_muted)
                w_col.setAlphaF(min(1.0, 0.65 * self._opacity))
                p.setFont(font_normal)
            else:
                w_col = QColor(t.on_surface_muted)
                w_col.setAlphaF(min(1.0, 0.45 * self._opacity))
                p.setFont(font_normal)

            ww = word_widths[i]
            p.setPen(w_col)
            p.drawText(
                QRectF(cur_x, 0, ww + 1.0, h),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                word,
            )
            cur_x += ww + space_w

        p.end()
