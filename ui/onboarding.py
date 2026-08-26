"""First-run onboarding wizard: interactive walkthrough of Dictate's workflow and hotkeys."""
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui import theme

BG_DARK = QColor("#090D16")
BG_CARD = QColor("#131B2E")
ACCENT_CYAN = QColor("#38BDF8")
ACCENT_PINK = QColor("#F43F5E")
ACCENT_GREEN = QColor("#22C55E")
ACCENT_PURPLE = QColor("#A855F7")
TEXT_PRIMARY = QColor("#F8FAFC")
TEXT_SECONDARY = QColor("#94A3B8")
BORDER = QColor("#1E293B")

FONT_FAMILY = "Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif"


def _icon_badge(icon_char: str, color: QColor, size: int = 64) -> QLabel:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, color.lighter(125))
    grad.setColorAt(1, color)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawEllipse(2, 2, size - 4, size - 4)

    p.setPen(QPen(QColor("#090D16" if color == ACCENT_CYAN or color == ACCENT_GREEN else "#FFFFFF")))
    p.setFont(QFont("Segoe UI", int(size * 0.38), QFont.Weight.Bold))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, icon_char)
    p.end()

    lbl = QLabel()
    lbl.setPixmap(pm)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _heading(text: str, size: int = 20) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", size, QFont.Weight.Bold))
    lbl.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    return lbl


def _body(text: str, size: int = 11) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", size))
    lbl.setStyleSheet(f"color: {TEXT_SECONDARY.name()}; line-height: 1.5;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    return lbl


def _step_card(icon_char: str, color: QColor, number: str, title: str, description: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{
            background-color: {BG_CARD.name()};
            border: 1px solid {BORDER.name()};
            border-radius: 10px;
            padding: 12px;
        }}
    """)
    layout = QVBoxLayout(card)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(8)

    layout.addWidget(_icon_badge(icon_char, color, 48))

    num_lbl = QLabel(number)
    num_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    num_lbl.setStyleSheet(
        f"color: {color.name()}; background: {BG_DARK.name()}; "
        f"border: 1px solid {color.name()}; border-radius: 8px; "
        "padding: 2px 8px;"
    )
    num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    h = QHBoxLayout()
    h.addStretch()
    h.addWidget(num_lbl)
    h.addStretch()
    layout.addLayout(h)

    title_lbl = QLabel(title)
    title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
    title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_lbl)

    desc_lbl = QLabel(description)
    desc_lbl.setFont(QFont("Segoe UI", 10))
    desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
    desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_lbl.setWordWrap(True)
    layout.addWidget(desc_lbl)

    return card


def _page_welcome() -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(40, 24, 40, 20)
    layout.setSpacing(14)

    layout.addStretch()
    layout.addWidget(_icon_badge("🎙", ACCENT_CYAN, 72))
    layout.addWidget(_heading("Welcome to Dictate"))
    layout.addWidget(_body(
        "Your private, fast, offline voice typing assistant.\n"
        "Speak naturally in any application and your speech appears instantly."
    ))

    badge = QLabel("🔒 100% Offline • Zero Telemetry • Local Inference")
    badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    badge.setStyleSheet(f"""
        color: {ACCENT_GREEN.name()};
        background-color: {BG_CARD.name()};
        border: 1px solid {ACCENT_GREEN.name()};
        border-radius: 6px;
        padding: 4px 12px;
    """)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(badge)

    layout.addStretch()
    return page


def _page_how_it_works(trigger_key: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)

    layout.addWidget(_heading("How It Works", 16))

    cards = QHBoxLayout()
    cards.setSpacing(10)
    cards.addWidget(_step_card("⌨", ACCENT_CYAN, "STEP 1", f"Hold [{trigger_key.upper()}]", "Press & hold your hotkey to start speaking"))
    cards.addWidget(_step_card("🗣", ACCENT_PINK, "STEP 2", "Speak", "Talk naturally — the floating pill visualizes sound"))
    cards.addWidget(_step_card("✨", ACCENT_GREEN, "STEP 3", "Text Pastes", "Your transcribed speech appears in your active app"))
    layout.addLayout(cards)

    layout.addStretch()
    return page


def _page_tips() -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(36, 16, 36, 16)
    layout.setSpacing(10)

    layout.addWidget(_heading("Helpful Tips", 16))

    tips = [
        ("🖱️", "Shape-Shifting Pill", "The floating indicator morphs into a microphone or waveform. Drag it anywhere."),
        ("⚙️", "Settings & History", "Right-click the pill or tray icon to open Settings or search your past dictations."),
        ("🔇", "Smart Auto-Stop", "Dictate automatically detects silence when you pause and finishes your sentence."),
        ("⎋", "Press Escape", "Cancel dictation instantly at any moment without pasting text."),
    ]

    for emoji, title, desc in tips:
        row = QHBoxLayout()
        row.setSpacing(10)

        icon = QLabel(emoji)
        icon.setFont(QFont("Segoe UI", 16))
        icon.setFixedWidth(30)
        row.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        t.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
        text_layout.addWidget(t)
        d = QLabel(desc)
        d.setFont(QFont("Segoe UI", 9))
        d.setStyleSheet(f"color: {TEXT_SECONDARY.name()};")
        d.setWordWrap(True)
        text_layout.addWidget(d)

        row.addLayout(text_layout, 1)
        layout.addLayout(row)

    layout.addStretch()
    return page


def _page_ready(trigger_key: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(40, 24, 40, 20)
    layout.setSpacing(14)

    layout.addStretch()
    layout.addWidget(_icon_badge("✓", ACCENT_GREEN, 72))
    layout.addWidget(_heading("Ready to Dictate!"))
    layout.addWidget(_body(
        f"Click into any document, text box, or chat, hold [{trigger_key.upper()}], and speak.\n\n"
        "Your offline speech model is loaded and ready."
    ))
    layout.addStretch()
    return page


class _DotIndicator(QWidget):
    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self._count = count
        self._current = 0
        self.setFixedHeight(18)

    def set_current(self, index: int):
        self._current = index
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dot_size = 6
        spacing = 14
        total = self._count * dot_size + (self._count - 1) * (spacing - dot_size)
        x = (self.width() - total) / 2
        y = (self.height() - dot_size) / 2

        for i in range(self._count):
            if i == self._current:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(ACCENT_CYAN))
                p.drawRoundedRect(int(x), int(y), 16, dot_size, 3, 3)
                x += 16 + (spacing - dot_size)
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor("#334155")))
                p.drawEllipse(int(x), int(y), dot_size, dot_size)
                x += spacing
        p.end()


class OnboardingDialog(QDialog):
    def __init__(self, trigger_key: str = "ctrl+shift+p", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Dictate")
        self.setFixedSize(560, 430)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
        )
        self.setStyleSheet(theme.get_dialog_stylesheet(dark=True))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.addWidget(_page_welcome())
        self.stack.addWidget(_page_how_it_works(trigger_key))
        self.stack.addWidget(_page_tips())
        self.stack.addWidget(_page_ready(trigger_key))
        root.addWidget(self.stack, 1)

        # Bottom Bar: Pagination Dots + Navigation
        bottom = QHBoxLayout()
        bottom.setContentsMargins(24, 12, 24, 18)

        self.dots = _DotIndicator(self.stack.count())
        bottom.addWidget(self.dots, 1)

        self.btn_back = QPushButton("Back")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self._go_back)
        bottom.addWidget(self.btn_back)

        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("primaryButton")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self._go_next)
        bottom.addWidget(self.btn_next)

        root.addLayout(bottom)
        self._update_buttons()

    def _update_buttons(self):
        idx = self.stack.currentIndex()
        last = self.stack.count() - 1
        self.dots.set_current(idx)
        self.btn_back.setVisible(idx > 0)
        self.btn_next.setText("Start Dictating" if idx == last else "Next")

    def _go_next(self):
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            self._update_buttons()
        else:
            self.accept()

    def _go_back(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_buttons()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            return
        super().keyPressEvent(event)
