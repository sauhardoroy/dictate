"""System tray icon with monochrome styling and status badges."""
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from ui import theme


def draw_icon(badge_color: str = None) -> QIcon:
    """Draw a clean monochrome microphone tray icon with optional status badge."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Base microphone glyph in crisp white/light-gray
    p.setPen(QPen(QColor("#F8FAFC"), 3.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)

    # Mic body
    p.drawRoundedRect(26, 14, 12, 22, 6, 6)
    # Mic arc
    p.drawArc(18, 22, 28, 20, 180 * 16, 180 * 16)
    # Stem & base
    p.drawLine(32, 42, 32, 49)
    p.drawLine(24, 49, 40, 49)

    # Status badge (if active state)
    if badge_color:
        p.setPen(QPen(QColor("#0F172A"), 1.8))
        p.setBrush(QColor(badge_color))
        p.drawEllipse(44, 10, 14, 14)

    p.end()
    return QIcon(pm)


class TrayIcon(QSystemTrayIcon):
    toggle_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    history_requested = pyqtSignal()
    copy_last_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self):
        super().__init__(draw_icon())
        self.setToolTip("Dictate — Ready")

        menu = QMenu()
        menu.setStyleSheet(theme.get_dialog_stylesheet(dark=True))

        self.act_record = QAction("Start Dictation", self)
        self.act_record.triggered.connect(self.toggle_requested.emit)
        self.act_copy_last = QAction("Copy Last Transcript", self)
        self.act_copy_last.triggered.connect(self.copy_last_requested.emit)
        act_history = QAction("Transcript History…", self)
        act_history.triggered.connect(self.history_requested.emit)
        act_settings = QAction("Settings…", self)
        act_settings.triggered.connect(self.settings_requested.emit)
        act_quit = QAction("Quit Dictate", self)
        act_quit.triggered.connect(self.quit_requested.emit)

        menu.addAction(self.act_record)
        menu.addSeparator()
        menu.addAction(self.act_copy_last)
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
        badge = {
            "recording": "#E11D48",
            "preview": "#E11D48",
            "transcribing": "#A855F7",
            "injecting": "#30D158",
            "loading": "#94A3B8",
            "error": "#DC2626",
        }.get(state, None)

        self.setIcon(draw_icon(badge))

        if hasattr(self, "act_record"):
            if state in ("recording", "preview"):
                self.act_record.setText("Stop Dictation")
            else:
                self.act_record.setText("Start Dictation")

        # Stable state vocabulary
        label = theme.STATES.get(state, theme.STATES["idle"]).label
        if state in ("recording", "preview"):
            tip = "Dictate — Listening…\nClick tray icon or floating pill to stop"
            if detail:
                tip += f"\n{detail}"
            self.setToolTip(tip)
        elif state == "idle":
            tip = "Dictate — Ready\nClick or press hotkey to record"
            if detail:
                tip += f"\n{detail}"
            self.setToolTip(tip)
        else:
            self.setToolTip(f"Dictate — {label}" + (f"\n{detail}" if detail else ""))
