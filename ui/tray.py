"""System tray icon with modern styling and state badges."""
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from ui import theme


def draw_icon(hex_color: str) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(hex_color))
    p.drawEllipse(4, 4, 56, 56)

    # Microphone icon glyph in white
    p.setPen(QPen(QColor("#FFFFFF"), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(27, 16, 10, 18, 5, 5)
    p.drawArc(21, 23, 22, 16, 180 * 16, 180 * 16)
    p.drawLine(32, 39, 32, 45)
    p.drawLine(26, 45, 38, 45)
    p.end()
    return QIcon(pm)


class TrayIcon(QSystemTrayIcon):
    toggle_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    history_requested = pyqtSignal()
    copy_last_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self):
        super().__init__(draw_icon("#38BDF8"))
        self.setToolTip("Dictate — Ready")

        menu = QMenu()
        menu.setStyleSheet(theme.get_dialog_stylesheet(dark=True))

        self.act_record = QAction("🎙 Start Listening (Toggle)", self)
        self.act_record.triggered.connect(self.toggle_requested.emit)
        act_copy_last = QAction("📋 Copy Last Transcript", self)
        act_copy_last.triggered.connect(self.copy_last_requested.emit)
        act_history = QAction("🕒 Transcript History…", self)
        act_history.triggered.connect(self.history_requested.emit)
        act_settings = QAction("⚙️ Settings…", self)
        act_settings.triggered.connect(self.settings_requested.emit)
        act_quit = QAction("✕ Quit Dictate", self)
        act_quit.triggered.connect(self.quit_requested.emit)

        menu.addAction(self.act_record)
        menu.addSeparator()
        menu.addAction(act_copy_last)
        menu.addAction(act_history)
        menu.addSeparator()
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _on_activated(self, reason):
        try:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                self.toggle_requested.emit()
        except Exception:
            pass

    def set_status(self, state: str, detail: str = ""):
        color = {
            "recording": "#F43F5E",
            "transcribing": "#A855F7",
            "injecting": "#22C55E",
            "loading": "#94A3B8",
            "error": "#EF4444",
        }.get(state, "#38BDF8")
        self.setIcon(draw_icon(color))
        if hasattr(self, "act_record"):
            if state == "recording":
                self.act_record.setText("⏹ Stop Listening (Finish & Transcribe)")
            else:
                self.act_record.setText("🎙 Start Listening (Toggle)")

        if state == "recording":
            tip = "Dictate — Listening…\nClick tray icon or floating pill to stop"
            if detail:
                tip += f"\n{detail}"
            self.setToolTip(tip)
        else:
            self.setToolTip(f"Dictate — {state.title()}" + (f"\n{detail}" if detail else ""))
