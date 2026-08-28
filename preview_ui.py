"""Dictate UI Workbench & Live Playground.

Standalone tool to test, inspect, and tweak all Dictate UI screens rapidly
without restarting the app, without modifying settings.json, and without
loading any speech recognition models.

Usage:
    .venv\\Scripts\\python.exe preview_ui.py
"""
from __future__ import annotations

import sys
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.material_theme import Tokens, get_tokens, build_qss
from ui.history_dialog import HistoryDialog
from ui.onboarding import HeroStage, OnboardingDialog, OnboardingShell
from ui.pill import Pill
from ui.preview_overlay import PreviewOverlay
from ui.settings_dialog import SettingsDialog


class CanvasWidget(QWidget):
    """Backdrop viewport simulating various desktop wallpapers for glass testing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_theme = "Deep Indigo (Dark)"
        self.setMinimumSize(940, 640)

    def set_wallpaper(self, name: str):
        self.bg_theme = name
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        rect = QRectF(0, 0, w, h)

        if self.bg_theme == "Deep Indigo (Dark)":
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor("#0B0F19"))
            grad.setColorAt(0.4, QColor("#1E1B4B"))
            grad.setColorAt(0.8, QColor("#312E81"))
            grad.setColorAt(1.0, QColor("#0284C7"))
            p.fillRect(rect, grad)
        elif self.bg_theme == "Aurora Purple (Dark)":
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor("#090D16"))
            grad.setColorAt(0.5, QColor("#4C1D95"))
            grad.setColorAt(1.0, QColor("#BE185D"))
            p.fillRect(rect, grad)
        elif self.bg_theme == "Sunset Amber (Light)":
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor("#FFF7ED"))
            grad.setColorAt(0.4, QColor("#FED7AA"))
            grad.setColorAt(0.8, QColor("#FBCFE8"))
            grad.setColorAt(1.0, QColor("#BAE6FD"))
            p.fillRect(rect, grad)
        elif self.bg_theme == "Ocean Breeze (Light)":
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor("#F0FDF4"))
            grad.setColorAt(0.5, QColor("#CFFAFE"))
            grad.setColorAt(1.0, QColor("#E0E7FF"))
            p.fillRect(rect, grad)
        elif self.bg_theme == "Slate Minimal":
            p.fillRect(rect, QColor("#1E293B"))
        elif self.bg_theme == "Grid / Checkers":
            p.fillRect(rect, QColor("#111827"))
            p.setPen(QPen(QColor(255, 255, 255, 18), 1))
            step = 30
            for x in range(0, int(w), step):
                p.drawLine(x, 0, x, int(h))
            for y in range(0, int(h), step):
                p.drawLine(0, y, int(w), y)


class UIWorkbenchWindow(QWidget):
    """Main Workbench window with live parameter tuning and screen switching."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dictate UI Workbench & Live Playground")
        self.resize(1380, 780)
        self.setStyleSheet("""
            QWidget {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 10px;
                margin-top: 14px;
                padding-top: 16px;
                font-weight: 600;
                font-size: 12px;
                color: #38BDF8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding-left: 8px;
                padding-right: 8px;
            }
            QLabel {
                font-size: 11px;
                color: #94A3B8;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #334155;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #0284C7;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #F8FAFC;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QComboBox, QPushButton {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2D3D54;
                border-color: #38BDF8;
            }
            QPushButton#primaryAction {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
            }
            QPushButton#primaryAction:hover {
                background-color: #0369A1;
            }
        """)

        self.dark_mode = True
        self.reduced_transparency = False
        self.reduced_motion = False
        self.current_scene = 0

        self._build_ui()
        self._reload_embedded_dialog()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Splitter: Left Preview Canvas | Right Controls
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Left: Preview Canvas
        self.canvas = CanvasWidget()
        self.canvas_layout = QVBoxLayout(self.canvas)
        self.canvas_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        splitter.addWidget(self.canvas)

        # Right: Scrollable Control Sidebar
        scroll = QScrollArea()
        scroll.setFixedWidth(400)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        ctrl_container = QWidget()
        ctrl_layout = QVBoxLayout(ctrl_container)
        ctrl_layout.setContentsMargins(18, 18, 18, 24)
        ctrl_layout.setSpacing(14)

        # Title
        title = QLabel("UI Workbench")
        title.setFont(theme.get_font(18, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        ctrl_layout.addWidget(title)

        subtitle = QLabel("Tweak frosted glass parameters and test screens in real-time.")
        subtitle.setWordWrap(True)
        ctrl_layout.addWidget(subtitle)

        # Group 1: Screen & Scene Selection
        grp_screen = QGroupBox("Screen Selection")
        v_screen = QVBoxLayout(grp_screen)
        v_screen.setSpacing(8)

        self.combo_screen = QComboBox()
        self.combo_screen.addItems([
            "Onboarding — Welcome (0)",
            "Onboarding — Setup (1)",
            "Onboarding — Ready / Get Started (2)",
            "Settings Dialog (Modal Test)",
            "History Dialog (Modal Test)",
            "Live Preview Overlay (Simulation)",
        ])
        self.combo_screen.currentIndexChanged.connect(self._on_screen_changed)
        v_screen.addWidget(self.combo_screen)

        btn_launch_native = QPushButton("🚀 Open Floating over Desktop")
        btn_launch_native.setObjectName("primaryAction")
        btn_launch_native.clicked.connect(self._launch_native_floating)
        v_screen.addWidget(btn_launch_native)

        ctrl_layout.addWidget(grp_screen)

        # Group 2: Environment & Theme
        grp_env = QGroupBox("Theme & Environment")
        v_env = QVBoxLayout(grp_env)
        v_env.setSpacing(8)

        self.chk_dark = QCheckBox("Dark Mode Theme")
        self.chk_dark.setChecked(True)
        self.chk_dark.toggled.connect(self._on_theme_toggled)
        v_env.addWidget(self.chk_dark)

        self.chk_rt = QCheckBox("Reduced Transparency (A11y)")
        self.chk_rt.toggled.connect(self._on_rt_toggled)
        v_env.addWidget(self.chk_rt)

        self.chk_rm = QCheckBox("Reduced Motion (A11y)")
        self.chk_rm.toggled.connect(self._on_rm_toggled)
        v_env.addWidget(self.chk_rm)

        lbl_wall = QLabel("Test Wallpaper Backdrop:")
        v_env.addWidget(lbl_wall)
        self.combo_wall = QComboBox()
        self.combo_wall.addItems([
            "Deep Indigo (Dark)",
            "Aurora Purple (Dark)",
            "Sunset Amber (Light)",
            "Ocean Breeze (Light)",
            "Slate Minimal",
            "Grid / Checkers",
        ])
        self.combo_wall.currentTextChanged.connect(self.canvas.set_wallpaper)
        v_env.addWidget(self.combo_wall)

        ctrl_layout.addWidget(grp_env)

        # Group 3: Glass Parameters (Live Sliders)
        grp_params = QGroupBox("Frosted Glass Tuning")
        v_params = QVBoxLayout(grp_params)
        v_params.setSpacing(10)

        # Sliders
        self.sl_left_alpha = self._add_slider(v_params, "Left Rail Opacity (Alpha)", 0, 255, 95)
        self.sl_right_alpha = self._add_slider(v_params, "Right Panel Opacity (Alpha)", 0, 255, 120)
        self.sl_radius = self._add_slider(v_params, "Window Corner Radius", 8, 40, 24)
        self.sl_highlight = self._add_slider(v_params, "Top Specular Highlight Rim", 0, 255, 28)
        self.sl_border = self._add_slider(v_params, "Glass Outer Border Opacity", 0, 255, 35)
        self.sl_hero_card = self._add_slider(v_params, "Hero Content Card Opacity", 0, 255, 14)
        self.sl_orb_size = self._add_slider(v_params, "Hero Badge Orb Size", 40, 120, 88)

        ctrl_layout.addWidget(grp_params)

        # Group 4: Actions & Snippet
        grp_actions = QGroupBox("Quick Actions")
        v_act = QVBoxLayout(grp_actions)
        v_act.setSpacing(8)

        btn_reset = QPushButton("🔄 Reset to Recommended Defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        v_act.addWidget(btn_reset)

        self.lbl_snippet = QLabel("Left: 95 | Right: 120 | Radius: 24 | Rim: 28")
        self.lbl_snippet.setStyleSheet("font-family: monospace; font-size: 10px; color: #38BDF8; background: #090D16; padding: 6px; border-radius: 4px;")
        v_act.addWidget(self.lbl_snippet)

        ctrl_layout.addWidget(grp_actions)
        ctrl_layout.addStretch()

        scroll.setWidget(ctrl_container)
        splitter.addWidget(scroll)
        splitter.setSizes([980, 400])

    def _add_slider(self, layout: QVBoxLayout, title: str, min_val: int, max_val: int, default: int) -> QSlider:
        header = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_val = QLabel(str(default))
        lbl_val.setStyleSheet("color: #38BDF8; font-weight: bold;")
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(lbl_val)
        layout.addLayout(header)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.valueChanged.connect(lambda val: lbl_val.setText(str(val)))
        slider.valueChanged.connect(self._apply_live_params)
        layout.addWidget(slider)
        return slider

    def _on_screen_changed(self, idx: int):
        if idx in (0, 1, 2):
            self.current_scene = idx
            if hasattr(self, "embedded_dlg") and self.embedded_dlg:
                self.embedded_dlg._go_to_scene(idx)
        elif idx == 3:
            # Settings Dialog Modal Test
            dlg = SettingsDialog({"trigger_key": "ctrl+shift+p", "mode": "push_to_talk"}, self)
            dlg.exec()
            self.combo_screen.setCurrentIndex(0)
        elif idx == 4:
            # History Dialog Modal Test
            dlg = HistoryDialog(self)
            dlg.exec()
            self.combo_screen.setCurrentIndex(0)
        elif idx == 5:
            # Preview Overlay Test
            overlay = PreviewOverlay(dark=self.dark_mode)
            overlay.show()
            overlay.set_text("Dictate streaming real-time live preview")
            QTimer.singleShot(3500, overlay.hide_animated)
            self.combo_screen.setCurrentIndex(0)

    def _on_theme_toggled(self, checked: bool):
        self.dark_mode = checked
        if checked:
            self.combo_wall.setCurrentText("Deep Indigo (Dark)")
            self.sl_left_alpha.setValue(95)
            self.sl_right_alpha.setValue(120)
            self.sl_highlight.setValue(28)
            self.sl_border.setValue(35)
            self.sl_hero_card.setValue(14)
        else:
            self.combo_wall.setCurrentText("Sunset Amber (Light)")
            self.sl_left_alpha.setValue(115)
            self.sl_right_alpha.setValue(85)
            self.sl_highlight.setValue(140)
            self.sl_border.setValue(180)
            self.sl_hero_card.setValue(80)
        self._reload_embedded_dialog()

    def _on_rt_toggled(self, checked: bool):
        self.reduced_transparency = checked
        self._reload_embedded_dialog()

    def _on_rm_toggled(self, checked: bool):
        self.reduced_motion = checked
        self._reload_embedded_dialog()

    def _reset_defaults(self):
        if self.dark_mode:
            self.sl_left_alpha.setValue(95)
            self.sl_right_alpha.setValue(120)
            self.sl_highlight.setValue(28)
            self.sl_border.setValue(35)
            self.sl_hero_card.setValue(14)
        else:
            self.sl_left_alpha.setValue(115)
            self.sl_right_alpha.setValue(85)
            self.sl_highlight.setValue(140)
            self.sl_border.setValue(180)
            self.sl_hero_card.setValue(80)
        self.sl_radius.setValue(24)
        self.sl_orb_size.setValue(88)

    def _reload_embedded_dialog(self):
        # Clear existing
        if hasattr(self, "embedded_dlg") and self.embedded_dlg:
            self.embedded_dlg.deleteLater()
            self.embedded_dlg = None

        self.embedded_dlg = OnboardingDialog(
            dark=self.dark_mode,
            reduced_transparency=self.reduced_transparency,
            reduced_motion=self.reduced_motion,
            parent=self.canvas,
        )
        self.canvas_layout.addWidget(self.embedded_dlg)
        self.embedded_dlg._go_to_scene(self.current_scene)
        self._apply_live_params()

    def _apply_live_params(self):
        if not hasattr(self, "embedded_dlg") or not self.embedded_dlg:
            return

        la = self.sl_left_alpha.value()
        ra = self.sl_right_alpha.value()
        rad = float(self.sl_radius.value())
        ha = self.sl_highlight.value()
        ba = self.sl_border.value()
        ca = self.sl_hero_card.value()
        orb = float(self.sl_orb_size.value())

        # Update shell properties
        if hasattr(self.embedded_dlg, "shell"):
            shell: OnboardingShell = self.embedded_dlg.shell
            shell.radius = rad
            shell.left_alpha = la
            shell.right_alpha = ra
            shell.highlight_alpha = ha
            shell.border_alpha = ba
            shell.update()

        # Update hero stage properties
        for hero in self.embedded_dlg.findChildren(HeroStage):
            hero.card_alpha = ca
            hero.orb_size = orb
            hero.update()

        self.lbl_snippet.setText(f"Left α:{la} | Right α:{ra} | Rad:{int(rad)}px | Hero α:{ca}")

    def _launch_native_floating(self):
        dlg = OnboardingDialog(
            dark=self.dark_mode,
            reduced_transparency=self.reduced_transparency,
            reduced_motion=self.reduced_motion,
        )
        # Apply tuned parameters
        if hasattr(dlg, "shell"):
            dlg.shell.radius = float(self.sl_radius.value())
            dlg.shell.left_alpha = self.sl_left_alpha.value()
            dlg.shell.right_alpha = self.sl_right_alpha.value()
            dlg.shell.highlight_alpha = self.sl_highlight.value()
            dlg.shell.border_alpha = self.sl_border.value()
        for hero in dlg.findChildren(HeroStage):
            hero.card_alpha = self.sl_hero_card.value()
            hero.orb_size = float(self.sl_orb_size.value())

        dlg._go_to_scene(self.current_scene)
        dlg.exec()


def main():
    app = QApplication(sys.argv)
    window = UIWorkbenchWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
