"""
widgets.py — Reusable Material 3 monochrome components.

Framework-thin components styled primarily through the QSS in material_theme.py,
with custom paint routines only where needed for interactive animation
(ToggleSwitch thumb travel, KeyCaptureButton states, LevelMeter RMS).
"""

from typing import Optional, List, Callable

from PyQt6.QtCore import (
    Qt, QRect, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty,
    pyqtSignal, QSize, QTimer,
)
from PyQt6.QtGui import QPainter, QColor, QFont, QKeySequence, QPaintEvent, QPen
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QHBoxLayout, QVBoxLayout,
    QSizePolicy,
)

from ui.material_theme import Tokens, Shape, MOTION


# --------------------------------------------------------------------------
# Layout helpers
# --------------------------------------------------------------------------

def make_label(text: str, role: str, wrap: bool = True) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("role", role)
    lbl.setWordWrap(wrap)
    return lbl


def make_card(t: Tokens) -> QFrame:
    card = QFrame()
    card.setProperty("role", "card")
    return card


def make_hairline(t: Tokens) -> QFrame:
    line = QFrame()
    line.setProperty("role", "hairline")
    line.setFixedHeight(1)
    return line


def make_button(text: str, variant: str = "secondary") -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("variant", variant)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setMinimumHeight(38)
    return btn


class StatusPill(QLabel):
    """Small tonal badge, e.g. '● OFFLINE READY'."""

    def __init__(self, text: str, tone: str = "neutral", dot: bool = True, parent=None):
        super().__init__(("● " if dot else "") + text, parent)
        self.setProperty("role", "pill")
        self.setProperty("tone", tone)

    def set_text(self, text: str, dot: bool = True):
        self.setText(("● " if dot else "") + text)


# --------------------------------------------------------------------------
# ToggleSwitch — animated M3 switch
# --------------------------------------------------------------------------

class ToggleSwitch(QWidget):
    """A hand-painted M3-style switch (track + traveling thumb)."""

    toggled = pyqtSignal(bool)

    def __init__(self, tokens: Tokens, checked: bool = False, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._checked = checked
        self._thumb_pos = 1.0 if checked else 0.0
        self.setFixedSize(44, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumb_pos", self)
        self._anim.setDuration(MOTION["fast"])
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_tokens(self, tokens: Tokens):
        self._tokens = tokens
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool, animate: bool = True):
        if value == self._checked:
            return
        self._checked = value
        target = 1.0 if value else 0.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._thumb_pos)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self.thumb_pos = target
        self.toggled.emit(value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.setChecked(not self._checked)
        else:
            super().keyPressEvent(event)

    def get_thumb_pos(self) -> float:
        return self._thumb_pos

    def set_thumb_pos(self, value: float):
        self._thumb_pos = value
        self.update()

    thumb_pos = pyqtProperty(float, get_thumb_pos, set_thumb_pos)

    def paintEvent(self, event: QPaintEvent):
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_on = QColor(t.on_surface)
        track_off = QColor(t.surface_container_highest)
        border_off = QColor(t.outline)

        # Interpolate track color by thumb position
        track_color = self._lerp(track_off, track_on, self._thumb_pos)

        track_rect = QRectF(0, 3, 44, 20)
        p.setPen(Qt.PenStyle.NoPen if self._thumb_pos > 0.05 else self._pen(border_off))
        p.setBrush(track_color)
        p.drawRoundedRect(track_rect, 10, 10)

        # Thumb travels from x=5 (off) to x=23 (on)
        diameter = 14 + 4 * self._thumb_pos
        x = 5 + (44 - 10 - diameter) * self._thumb_pos
        y = 13 - diameter / 2
        thumb_color = QColor(t.surface) if self._thumb_pos > 0.5 else QColor(t.on_surface_muted)
        p.setBrush(thumb_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(x, y, diameter, diameter))

    @staticmethod
    def _pen(color: QColor):
        pen = QPen(color)
        pen.setWidthF(1.5)
        return pen

    @staticmethod
    def _lerp(a: QColor, b: QColor, t: float) -> QColor:
        return QColor(
            int(a.red() + (b.red() - a.red()) * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue() + (b.blue() - a.blue()) * t),
        )


# --------------------------------------------------------------------------
# KeyCaptureButton
# --------------------------------------------------------------------------

class KeyCaptureButton(QPushButton):
    """Click to arm; the next key chord pressed becomes the new shortcut.
    Esc cancels and restores the previous value. Emits `shortcutChanged(str)`.
    """

    shortcutChanged = pyqtSignal(str)

    def __init__(self, initial: str = "ctrl+shift+p", parent=None):
        super().__init__(initial, parent)
        self.key = initial
        self._value = initial
        self._previous = initial
        self._recording = False
        self.setProperty("variant", "key-capture")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(160)
        self.setFixedHeight(34)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(self._start_recording)
        self._format_text(initial)

    def _format_text(self, chord: str):
        parts = [p.strip().upper() for p in chord.split("+") if p.strip()]
        self.setText(" + ".join(parts) if parts else chord)

    def value(self) -> str:
        return self.key

    def setValue(self, chord: str):
        self.key = chord
        self._value = chord
        self._previous = chord
        self._format_text(chord)

    def _start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._previous = self.key
        self.setText("Press shortcut keys…")
        self.setProperty("recording", "true")
        self._repolish()
        self.setFocus()
        self.grabKeyboard()

    def _stop_recording(self, commit: bool, chord: Optional[str] = None):
        self._recording = False
        self.releaseKeyboard()
        self.setProperty("recording", "false")
        self._repolish()
        if commit and chord:
            self.key = chord.lower()
            self._value = self.key
            self._format_text(chord)
            self.shortcutChanged.emit(self.key)
        else:
            self._format_text(self._previous)

    def _repolish(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def keyPressEvent(self, event):
        if not self._recording:
            return super().keyPressEvent(event)

        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._stop_recording(commit=False)
            return

        if key in (
            Qt.Key.Key_Control, Qt.Key.Key_Shift,
            Qt.Key.Key_Alt, Qt.Key.Key_Meta,
        ):
            return

        modifiers = event.modifiers()
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("win")

        key_text = QKeySequence(key).toString().lower()
        if key_text:
            parts.append(key_text)

        if parts:
            chord = "+".join(parts)
            self._stop_recording(commit=True, chord=chord)

    def focusOutEvent(self, event):
        if self._recording:
            self._stop_recording(commit=False)
        super().focusOutEvent(event)


# --------------------------------------------------------------------------
# LevelMeter — real-time RMS bar for the mic test
# --------------------------------------------------------------------------

class LevelMeter(QWidget):
    """A horizontal bar of discrete segments, monochrome, lighting up
    proportional to `level` (0.0–1.0)."""

    SEGMENTS = 28

    def __init__(self, tokens: Tokens, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._level = 0.0
        self.setFixedHeight(18)
        self.setMinimumWidth(200)

    def set_tokens(self, tokens: Tokens):
        self._tokens = tokens
        self.update()

    def set_level(self, level: float):
        self._level = max(0.0, min(1.0, level))
        self.update()

    def paintEvent(self, event: QPaintEvent):
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        gap = 3.0
        seg_w = (w - gap * (self.SEGMENTS - 1)) / self.SEGMENTS
        lit_count = round(self._level * self.SEGMENTS)

        for i in range(self.SEGMENTS):
            x = i * (seg_w + gap)
            is_lit = i < lit_count
            if is_lit and i > self.SEGMENTS * 0.85:
                color = QColor(t.on_surface)
            elif is_lit:
                color = QColor(t.on_surface_variant)
            else:
                color = QColor(t.surface_container_high)
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, 0, seg_w, h), 2.0, 2.0)


# --------------------------------------------------------------------------
# SegmentedTabBar — animated M3 segmented control
# --------------------------------------------------------------------------

class SegmentedTabBar(QWidget):
    """A pill-shaped row of segment buttons with one active at a time."""

    currentChanged = pyqtSignal(int)

    def __init__(self, labels: List[str], parent=None):
        super().__init__(parent)
        self.setObjectName("segmentedBar")
        self._buttons: List[QPushButton] = []
        self._current = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setProperty("role", "segment")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, idx=i: self.set_current(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)

        self.set_current(0, emit=False)

    def set_current(self, index: int, emit: bool = True):
        self._current = index
        for i, btn in enumerate(self._buttons):
            active = (i == index)
            btn.setChecked(active)
            btn.setProperty("state", "active" if active else "inactive")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if emit:
            self.currentChanged.emit(index)

    def current(self) -> int:
        return self._current


# --------------------------------------------------------------------------
# NavRailStep — left-rail step item for onboarding
# --------------------------------------------------------------------------

class NavRailStep(QPushButton):
    """One row in the onboarding left rail: index/checkmark + label."""

    STATE_UPCOMING = "upcoming"
    STATE_ACTIVE = "active"
    STATE_DONE = "done"

    def __init__(self, index: int, label: str, parent=None):
        super().__init__(parent)
        self._index = index
        self._label = label
        self._state = self.STATE_UPCOMING
        self.setProperty("role", "navstep")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42)
        self._sync_text()

    def set_state(self, state: str):
        self._state = state
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self._sync_text()

    def _sync_text(self):
        if self._state == self.STATE_DONE:
            glyph = "✓"
        else:
            glyph = str(self._index + 1)
        self.setText(f"  {glyph}   {self._label}")
