"""
onboarding.py — First-Run Onboarding (Material 3 Monochrome)

A 3-step introductory flow that guides first-time users from download
to their first successful voice dictation in under 30 seconds.

Features:
- Google Material 3 Monochrome design language (tonal surfaces, no blur).
- Draggable frameless dialog with smooth opacity fade-in.
- Left navigation rail with active/done/upcoming step tracking.
- Step 1: Welcome & Offline privacy assurance.
- Step 2: Global shortcut capture & local speech model status.
- Step 3: Optional Cloud AI polish toggle & ready activation.
"""

from __future__ import annotations

import sys
from typing import Optional, Dict, Any

from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QPaintEvent
from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QStackedWidget, QGraphicsOpacityEffect, QSizePolicy,
)

from ui.material_theme import Tokens, build_qss, Shape
from ui.widgets import (
    NavRailStep, StatusPill, ToggleSwitch, KeyCaptureButton,
    make_card, make_hairline, make_button, make_label,
)


STEP_LABELS = ["Welcome", "Setup", "Get Started"]


class HeroStage(QFrame):
    """A tonal platter with a centered glyph representing the step's theme."""

    def __init__(self, tokens: Tokens, glyph: str, parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self.glyph = glyph
        self.setProperty("role", "card")
        self.setFixedHeight(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(glyph)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"color: {tokens.on_surface_variant}; font-size: 38px; font-weight: bold; background: transparent;")
        layout.addWidget(self.label)


class OnboardingShell(QFrame):
    """Compatibility shell for preview and embedded testing."""
    def __init__(self, rail_width: int = 240, dark: bool = True, parent=None):
        super().__init__(parent)
        self.rail_width = rail_width
        self.dark = dark


class OnboardingDialog(QDialog):
    """Three-stage first-run onboarding flow with Material 3 Monochrome aesthetics."""

    class DialogCode:
        Accepted = 1
        Rejected = 0

    def __init__(
        self,
        trigger_key: str = "ctrl+shift+p",
        model_id: str = "parakeet-tdt-0.6b-v3",
        dark: bool = True,
        parent: Optional[QWidget] = None,
        **kwargs,
    ):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Dictate — Welcome")
        self.resize(880, 560)
        self.setObjectName("root")

        self.dark = dark
        self.trigger_key = trigger_key
        self.model_id = model_id

        self._tokens = Tokens.dark() if dark else Tokens.light()
        self.setStyleSheet(build_qss(self._tokens))

        self._drag_pos: Optional[QPoint] = None
        self._current_step = 0
        self._settings: Dict[str, Any] = {
            "trigger_key": trigger_key,
            "shortcut": trigger_key,
            "ai_polish": False,
            "polish_transcripts": False,
        }

        self._build_ui()
        self._go_to_step(0)

    # -- backward-compatible public API --------------------------------

    def values(self) -> Dict[str, Any]:
        """Returns the settings configured during onboarding."""
        shortcut = self._key_capture.value() if hasattr(self, "_key_capture") else self._settings["trigger_key"]
        polish = self._polish_toggle.isChecked() if hasattr(self, "_polish_toggle") else self._settings["ai_polish"]
        return {
            "trigger_key": shortcut,
            "ai_polish": polish,
        }

    def showEvent(self, event):
        super().showEvent(event)
        self._fade_in()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 64:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # -- construction -----------------------------------------------------

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_nav_rail())
        root.addWidget(self._build_content_stage(), 1)

    def _build_nav_rail(self) -> QWidget:
        rail = QWidget()
        rail.setObjectName("navRail")
        rail.setFixedWidth(240)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(4)

        # App brand identity
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        mark = QLabel("◆")
        mark.setStyleSheet(f"color:{self._tokens.on_surface}; font-size:18px;")
        title = make_label("Dictate", "title")
        brand_row.addWidget(mark)
        brand_row.addWidget(title)
        brand_row.addStretch()
        layout.addLayout(brand_row)
        layout.addSpacing(28)

        category = make_label("ONBOARDING", "label_caps")
        layout.addWidget(category)
        layout.addSpacing(8)

        self._nav_steps = []
        for i, label in enumerate(STEP_LABELS):
            step = NavRailStep(i, label)
            step.clicked.connect(lambda _c=False, idx=i: self._go_to_step(idx))
            layout.addWidget(step)
            self._nav_steps.append(step)

        layout.addStretch()

        footnote = make_label("Privacy-first · 100% offline engine", "body_sm")
        layout.addWidget(footnote)
        return rail

    def _build_content_stage(self) -> QWidget:
        wrapper = QWidget()
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(48, 36, 48, 32)
        outer.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step_welcome())
        self._stack.addWidget(self._build_step_setup())
        self._stack.addWidget(self._build_step_ready())
        outer.addWidget(self._stack, 1)

        return wrapper

    # -- Step 1: Welcome --------------------------------------------------

    def _build_step_welcome(self) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        layout.addWidget(HeroStage(t, "🎙"))
        layout.addSpacing(6)

        layout.addWidget(make_label("Dictate, wherever you write.", "headline"))
        layout.addWidget(make_label(
            "Hold a shortcut, speak, and Dictate places clean text at your cursor.",
            "body",
        ))

        layout.addSpacing(4)
        trust = StatusPill("Speech recognition stays on your device · 100% Offline", tone="success")
        trust.setAlignment(Qt.AlignmentFlag.AlignLeft)
        trust_row = QHBoxLayout()
        trust_row.addWidget(trust)
        trust_row.addStretch()
        layout.addLayout(trust_row)

        layout.addStretch()

        actions = QHBoxLayout()
        actions.addStretch()
        cont = make_button("Continue →", "primary")
        cont.clicked.connect(lambda: self._go_to_step(1))
        actions.addWidget(cont)
        layout.addLayout(actions)

        return page

    # -- Step 2: Setup ----------------------------------------------------

    def _build_step_setup(self) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        layout.addWidget(HeroStage(t, "⚙"))
        layout.addSpacing(6)

        layout.addWidget(make_label("A few essentials.", "headline"))
        layout.addWidget(make_label("Set the shortcut you'll use to start dictating.", "body"))

        layout.addSpacing(4)
        card = make_card(t)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(14)

        # Row 1: Shortcut Capture
        row1 = QHBoxLayout()
        row1_text = QVBoxLayout()
        row1_text.addWidget(make_label("Dictation Shortcut", "body", wrap=False))
        row1_text.addWidget(make_label("Available in any app", "body_sm", wrap=False))
        row1.addLayout(row1_text)
        row1.addStretch()
        self._key_capture = KeyCaptureButton(self._settings["trigger_key"])
        self._key_capture.shortcutChanged.connect(self._on_shortcut_changed)
        row1.addWidget(self._key_capture)
        card_layout.addLayout(row1)

        card_layout.addWidget(make_hairline(t))

        # Row 2: Speech Model Status
        row2 = QHBoxLayout()
        row2_text = QVBoxLayout()
        row2_text.addWidget(make_label("Local Speech Model", "body", wrap=False))
        row2_text.addWidget(make_label("Ready for offline transcription · Privacy first", "body_sm", wrap=False))
        row2.addLayout(row2_text)
        row2.addStretch()
        row2.addWidget(StatusPill("OFFLINE READY", tone="success"))
        card_layout.addLayout(row2)

        layout.addWidget(card)
        layout.addStretch()

        actions = QHBoxLayout()
        back = make_button("← Back", "secondary")
        back.clicked.connect(lambda: self._go_to_step(0))
        actions.addWidget(back)
        actions.addStretch()
        cont = make_button("Continue →", "primary")
        cont.clicked.connect(lambda: self._go_to_step(2))
        actions.addWidget(cont)
        layout.addLayout(actions)

        return page

    def _on_shortcut_changed(self, chord: str):
        self._settings["trigger_key"] = chord
        self._settings["shortcut"] = chord

    # -- Step 3: Get Started ----------------------------------------------

    def _build_step_ready(self) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        layout.addWidget(HeroStage(t, "▶"))
        layout.addSpacing(6)

        layout.addWidget(make_label("Ready when you are.", "headline"))
        layout.addWidget(make_label(
            "Focus a text field, hold your shortcut, then speak naturally.", "body"
        ))

        layout.addSpacing(4)
        card = make_card(t)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(14)

        # Row: AI Polish Toggle
        row1 = QHBoxLayout()
        row1_text = QVBoxLayout()
        row1_text.addWidget(make_label("Polish transcripts (Optional)", "body", wrap=False))
        row1_text.addWidget(make_label("Remove filler words and tidy punctuation.", "body_sm", wrap=False))
        row1.addLayout(row1_text)
        row1.addStretch()
        self._polish_toggle = ToggleSwitch(t, checked=self._settings["ai_polish"])
        self._polish_toggle.toggled.connect(self._on_polish_toggled)
        row1.addWidget(self._polish_toggle)
        card_layout.addLayout(row1)

        card_layout.addWidget(make_hairline(t))

        # Footnote
        privacy_row = QHBoxLayout()
        privacy_row.setSpacing(8)
        lock = QLabel("🔒")
        lock.setStyleSheet(f"color: {t.on_surface_muted};")
        privacy_row.addWidget(lock)
        privacy_row.addWidget(make_label(
            "Your speech is transcribed 100% locally. Cloud polish is strictly optional.",
            "body_sm",
        ))
        privacy_row.addStretch()
        card_layout.addLayout(privacy_row)

        layout.addWidget(card)
        layout.addStretch()

        actions = QHBoxLayout()
        back = make_button("← Back", "secondary")
        back.clicked.connect(lambda: self._go_to_step(1))
        actions.addWidget(back)
        actions.addStretch()
        start = make_button("Start Dictating", "primary")
        start.clicked.connect(self._finish)
        actions.addWidget(start)
        layout.addLayout(actions)

        return page

    def _on_polish_toggled(self, checked: bool):
        self._settings["ai_polish"] = checked
        self._settings["polish_transcripts"] = checked

    def _finish(self):
        self.accept()

    # -- Navigation helpers -----------------------------------------------

    def _go_to_step(self, index: int):
        self._current_step = index
        self._stack.setCurrentIndex(index)
        for i, step in enumerate(self._nav_steps):
            if i < index:
                step.set_state(NavRailStep.STATE_DONE)
            elif i == index:
                step.set_state(NavRailStep.STATE_ACTIVE)
            else:
                step.set_state(NavRailStep.STATE_UPCOMING)

    def _go_to_scene(self, index: int):
        self._go_to_step(index)

    # -- Motion -----------------------------------------------------------

    def _fade_in(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._fade_anim = anim


def main():
    app = QApplication(sys.argv)
    dlg = OnboardingDialog(dark=True)
    if dlg.exec():
        print("Onboarding complete:", dlg.values())
    else:
        print("Onboarding cancelled")


if __name__ == "__main__":
    main()