"""Visual QA harness for the Real-time Apple Liquid Glass Shader.

Evaluates the two-pass shader pipeline with live Snell refraction, Cauchy dispersion,
edge surface tension lensing, and Blinn-Phong specular glints.
"""
import sys

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication

from ui import theme
from ui.pill import Pill

app = QApplication(sys.argv)

STATES = ["idle", "recording", "transcribing", "injecting", "loading", "error"]


def create_rich_backdrop(w: int, h: int, dark: bool) -> QPixmap:
    pm = QPixmap(w, h)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Base gradient
    grad = QLinearGradient(0, 0, w, h)
    if dark:
        grad.setColorAt(0.0, QColor("#090D16"))
        grad.setColorAt(0.5, QColor("#131B2E"))
        grad.setColorAt(1.0, QColor("#0B132B"))
    else:
        grad.setColorAt(0.0, QColor("#F8FAFC"))
        grad.setColorAt(0.5, QColor("#E2E8F0"))
        grad.setColorAt(1.0, QColor("#F1F5F9"))
    p.fillRect(pm.rect(), grad)

    # High-contrast geometric shapes and text to verify Snell's law refraction & chromatic dispersion
    for i in range(len(STATES)):
        cx = i * 340 + 170
        p.setPen(Qt.PenStyle.NoPen)
        if dark:
            p.setBrush(QColor("#1E293B"))
            p.drawEllipse(cx - 48, 16, 96, 60)
            p.setBrush(QColor("#38BDF8" if i % 2 == 0 else "#FB7185"))
            p.drawRect(cx - 32, 38, 64, 18)
        else:
            p.setBrush(QColor("#CBD5E1"))
            p.drawEllipse(cx - 48, 16, 96, 60)
            p.setBrush(QColor("#0284C7" if i % 2 == 0 else "#E11D48"))
            p.drawRect(cx - 32, 38, 64, 18)

        p.setPen(QColor("#94A3B8" if dark else "#64748B"))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.drawText(cx - 35, 84, STATES[i].upper())

    p.end()
    return pm


def render_row(dark: bool, filename: str):
    cell_w, cell_h = 340, 100
    total_w = cell_w * len(STATES)

    sheet = create_rich_backdrop(total_w, cell_h, dark)
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pill = Pill(x=100, y=100)
    pill._dark = dark

    for i, state in enumerate(STATES):
        pill.set_state(state, "")
        if state == "recording":
            pill.update_preview("Redesigning Dictate with Liquid Glass")
        pill._morph_anim.stop()
        w = theme.STATES[state].width
        h = theme.STATES[state].height
        pill._width = float(w)
        pill._height = float(h)
        pill.resize(w, h)
        pill._pulse = 0.85
        pill._ripple_phase = 0.5

        # Screen crop directly under this cell
        x = i * cell_w + (cell_w - w) // 2
        y = (cell_h - h) // 2

        crop = sheet.copy(x, y, w, h)
        pill._bg_pixmap = crop
        pill._execute_shader_pass()
        pill.repaint()

        shot = pill.grab()
        painter.drawPixmap(x, y, shot)

    painter.end()
    sheet.save(filename)
    pill.close()


render_row(dark=True, filename="_qa_pill_dark.png")
render_row(dark=False, filename="_qa_pill_light.png")
print("saved _qa_pill_dark.png and _qa_pill_light.png")
