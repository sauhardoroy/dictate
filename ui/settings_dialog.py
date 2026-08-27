"""Modern Apple & Platform-Respectful Preferences Dialog for Dictate.

Structured across 4 resilient sections in the Content Layer:
1. General — Startup, clipboard restoration, theme appearance, and accessibility.
2. Dictation — Activation mode, global shortcut capture, stop listening controls, live preview, and voice commands.
3. Audio — Input device selection and interactive real-time microphone tester.
4. Advanced — Speech models, hardware acceleration, custom jargon boosting, and optional Cloud AI Polish (opt-in with privacy disclosures).
"""
import os
import sys
import sounddevice as sd
from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui import theme


class AppleToggle(QWidget):
    """Refined Apple/Windows rounded toggle switch."""
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = True, dark: bool = True, parent=None):
        super().__init__(parent)
        self.dark = dark
        self._checked = checked
        self._position = float(checked)
        self.setFixedSize(44, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._animation = QVariantAnimation(self)
        self._animation.setDuration(160)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._animate)

    def _animate(self, value):
        self._position = float(value)
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if checked == self._checked:
            return
        self._checked = checked
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(float(checked))
        self._animation.start()
        self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.setChecked(not self._checked)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        accent = QColor(theme.pick(theme.SYSTEM_BLUE, self.dark))
        track_off = QColor(theme.pick(theme.SURFACE_ELEVATED, self.dark))

        # Track background
        p.setPen(QPen(QColor(theme.pick(theme.BORDER_STRONG, self.dark)), 1.0))
        p.setBrush(accent if self._checked else track_off)
        p.drawRoundedRect(rect, 12.0, 12.0)

        # Focus ring
        if self.hasFocus():
            p.setPen(QPen(QColor(theme.pick(theme.BORDER_FOCUS, self.dark)), 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 13.0, 13.0)

        # Thumb knob
        thumb_x = rect.left() + 2.0 + self._position * (rect.width() - 24.0)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(thumb_x, rect.top() + 2.0, 20.0, 20.0))
        p.end()


class KeyCaptureButton(QPushButton):
    """Clean key combination capture button."""

    def __init__(self, current_key: str, parent=None):
        super().__init__(parent)
        self.key = current_key
        self.listening = False
        self._update_text()
        self.clicked.connect(self._toggle_listening)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _update_text(self):
        if self.listening:
            self.setText("Press shortcut keys… (Esc to cancel)")
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(225, 29, 72, 0.15);
                    color: #FB7185;
                    border: 1.5px solid #E11D48;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 0 14px;
                    text-align: center;
                }
            """)
        else:
            parts = [p.strip().upper() for p in self.key.split("+")]
            formatted = " + ".join(parts)
            self.setText(formatted)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #F8FAFC;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 0 16px;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #2D3D54;
                    border-color: #38BDF8;
                    color: #38BDF8;
                }
                QPushButton:focus {
                    border: 2px solid #38BDF8;
                }
            """)

    def _toggle_listening(self):
        self.listening = not self.listening
        self._update_text()
        if self.listening:
            self.grabKeyboard()
        else:
            self.releaseKeyboard()

    def keyPressEvent(self, event):
        if not self.listening:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        if key == Qt.Key.Key_Escape:
            self.listening = False
            self.releaseKeyboard()
            self._update_text()
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
            self.key = "+".join(parts)
            self.listening = False
            self.releaseKeyboard()
            self._update_text()


class MicTestWidget(QWidget):
    """Interactive live microphone test bar with accessible status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.btn_test = QPushButton("Test Microphone")
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.setFixedHeight(32)
        self.btn_test.clicked.connect(self._toggle_test)
        header.addWidget(self.btn_test)

        self.lbl_status = QLabel("Click to speak and test microphone input level")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px;")
        header.addWidget(self.lbl_status, 1)
        layout.addLayout(header)

        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setValue(0)
        self.meter.setTextVisible(False)
        self.meter.setFixedHeight(6)
        self.meter.setStyleSheet("""
            QProgressBar {
                background-color: #1E293B;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0284C7, stop:0.7 #38BDF8, stop:1.0 #E11D48);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.meter)

        self.stream = None
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self._update_meter)
        self._current_level = 0.0

    def _audio_callback(self, indata, frames, time_info, status):
        import numpy as np
        rms = np.sqrt(np.mean(indata**2))
        self._current_level = float(rms)

    def _toggle_test(self):
        if self.stream is None:
            try:
                self.stream = sd.InputStream(
                    samplerate=16000,
                    channels=1,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self.stream.start()
                self.timer.start()
                self.btn_test.setText("Stop Test")
                self.lbl_status.setText("Listening… Speak into your microphone")
                self.lbl_status.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 500;")
            except Exception as e:
                self.lbl_status.setText(f"Microphone error: {e}")
        else:
            self._stop()

    def _stop(self):
        if self.stream:
            self.timer.stop()
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
            self.btn_test.setText("Test Microphone")
            self.lbl_status.setText("Test stopped")
            self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px;")
            self.meter.setValue(0)

    def _update_meter(self):
        val = int(min(100.0, self._current_level * 300.0))
        self.meter.setValue(val)

    def cleanup(self):
        self._stop()


class SegmentedNavBar(QWidget):
    """Clean Segmented Navigation Bar with smooth sliding pill highlight."""
    currentChanged = pyqtSignal(int)

    def __init__(self, tab_labels: list[str], parent=None):
        super().__init__(parent)
        self.tab_labels = tab_labels
        self._current_index = 0
        self._indicator_x = 3.0
        self._indicator_w = 80.0

        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"indicatorProgress", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_indicator_progress(self) -> float:
        return self._indicator_x

    def set_indicator_progress(self, val: float):
        self._indicator_x = val
        self.update()

    indicatorProgress = pyqtProperty(float, get_indicator_progress, set_indicator_progress)

    def set_current_index(self, index: int):
        if 0 <= index < len(self.tab_labels) and index != self._current_index:
            self._current_index = index
            self._animate_to_tab(index)
            self.currentChanged.emit(index)

    def _animate_to_tab(self, index: int):
        target_x, target_w = self._get_tab_rect(index)
        self._indicator_w = target_w
        self._anim.stop()
        self._anim.setStartValue(self._indicator_x)
        self._anim.setEndValue(float(target_x))
        self._anim.start()

    def _get_tab_rect(self, index: int) -> tuple[float, float]:
        n = len(self.tab_labels)
        pad = 3.0
        avail_w = self.width() - (pad * 2)
        tab_w = avail_w / n
        x = pad + (index * tab_w)
        return x, tab_w

    def resizeEvent(self, event):
        super().resizeEvent(event)
        x, w = self._get_tab_rect(self._current_index)
        self._indicator_x = x
        self._indicator_w = w

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pad = 3.0
            avail_w = self.width() - (pad * 2)
            tab_w = avail_w / len(self.tab_labels)
            clicked_idx = int((event.pos().x() - pad) // tab_w)
            clicked_idx = max(0, min(len(self.tab_labels) - 1, clicked_idx))
            self.set_current_index(clicked_idx)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        radius = 10.0

        # Track Background
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        p.setBrush(QColor(30, 41, 59, 180))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)

        # Sliding Highlight Capsule
        if self._indicator_w > 0:
            pill_rect = QRectF(self._indicator_x + 1.0, 3.0, self._indicator_w - 2.0, h - 6.0)
            p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
            p.setBrush(QColor(255, 255, 255, 30))
            p.drawRoundedRect(pill_rect, 7.0, 7.0)

        # Text Labels
        font = theme.get_font(12, QFont.Weight.DemiBold)
        p.setFont(font)

        pad = 3.0
        tab_w = (w - (pad * 2)) / len(self.tab_labels)
        for i, label in enumerate(self.tab_labels):
            tx = pad + i * tab_w
            rect = QRectF(tx, 0, tab_w, h)
            is_active = (i == self._current_index)
            p.setPen(QColor("#FFFFFF" if is_active else "#94A3B8"))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        p.end()


class AnimatedStackedWidget(QStackedWidget):
    """Stacked container with clean cross-fade page transition."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fade_anim = None

    def slide_to_index(self, index: int):
        if index == self.currentIndex():
            return

        next_widget = self.widget(index)
        if not next_widget:
            return

        if self._fade_anim:
            self._fade_anim.stop()

        effect = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(effect)
        self.setCurrentIndex(index)

        self._fade_anim = QPropertyAnimation(effect, b"opacity", self)
        self._fade_anim.setDuration(theme.DURATION_CROSSFADE)
        self._fade_anim.setStartValue(0.15)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(lambda: next_widget.setGraphicsEffect(None))
        self._fade_anim.start()


class SettingsDialog(QDialog):
    """Apple-inspired Preferences Dialog organized into 4 resilient sections."""

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dictate Settings")
        self.setMinimumSize(640, 560)
        self.resize(680, 580)
        self.setStyleSheet(theme.get_dialog_stylesheet(dark=True))

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)

        # 1. Header
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        lbl_title = QLabel("Settings")
        lbl_title.setFont(theme.get_font(20, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #F8FAFC;")
        title_box.addWidget(lbl_title)

        lbl_sub = QLabel("Configure voice typing, offline models, audio devices, and privacy.")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(lbl_sub)

        root.addLayout(title_box)

        # 2. Segmented Navigation Bar (4 Resilient Categories)
        tab_names = ["General", "Dictation", "Audio", "Advanced"]
        self.nav_bar = SegmentedNavBar(tab_names)
        root.addWidget(self.nav_bar)

        # 3. Stacked Content Pages
        self.pages = AnimatedStackedWidget()
        data = current_settings
        self.pages.addWidget(self._build_general_page(data))
        self.pages.addWidget(self._build_dictation_page(data))
        self.pages.addWidget(self._build_audio_page(data))
        self.pages.addWidget(self._build_advanced_page(data))

        self.nav_bar.currentChanged.connect(self.pages.slide_to_index)
        root.addWidget(self.pages, 1)

        # 4. Bottom Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setFixedHeight(34)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save)
        btn_box.addWidget(self.btn_save)

        root.addLayout(btn_box)

    def _build_general_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        # Group 1: System Integration
        grp_sys = QGroupBox("System Integration")
        v_sys = QVBoxLayout(grp_sys)
        v_sys.setSpacing(12)

        self.autostart_cb = QCheckBox("Launch Dictate automatically at Windows startup")
        self.autostart_cb.setChecked(bool(data.get("autostart", False)))
        v_sys.addWidget(self.autostart_cb)

        self.restore_cb = QCheckBox("Restore previous clipboard content after typing text")
        self.restore_cb.setChecked(bool(data.get("restore_clipboard", True)))
        v_sys.addWidget(self.restore_cb)

        layout.addWidget(grp_sys)

        # Group 2: Appearance & Accessibility
        grp_app = QGroupBox("Appearance & Accessibility")
        form_app = QFormLayout(grp_app)
        form_app.setSpacing(12)

        self.theme_mode = QComboBox()
        self.theme_mode.addItem("Dark Mode (Recommended)", "dark")
        self.theme_mode.addItem("Light Mode", "light")
        form_app.addRow("Theme", self.theme_mode)

        layout.addWidget(grp_app)
        layout.addStretch()
        return page

    def _build_dictation_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        # Group 1: Activation & Shortcut
        grp_act = QGroupBox("Activation & Shortcut")
        form_act = QFormLayout(grp_act)
        form_act.setSpacing(12)

        self.mode = QComboBox()
        self.mode.addItem("Hold to Talk (Push-to-Talk)", "ptt")
        self.mode.addItem("Press to Start / Stop (Toggle)", "toggle")
        idx = self.mode.findData(data.get("mode", "ptt"))
        if idx >= 0:
            self.mode.setCurrentIndex(idx)
        form_act.addRow("Trigger Mode", self.mode)

        self.key_btn = KeyCaptureButton(data.get("trigger_key", "ctrl+shift+p"))
        form_act.addRow("Global Shortcut", self.key_btn)
        layout.addWidget(grp_act)

        # Group 2: Stopping & Options
        grp_stop = QGroupBox("Listening & Stopping Control")
        v_stop = QVBoxLayout(grp_stop)
        v_stop.setSpacing(12)

        form_stop = QFormLayout()
        form_stop.setSpacing(12)

        self.stop_mode = QComboBox()
        self.stop_mode.addItem("Automatically stop on silence (Auto-Stop)", True)
        self.stop_mode.addItem("Manual stop (Click floating pill, tray icon, or shortcut)", False)
        is_auto_stop = bool(data.get("auto_stop", True))
        self.stop_mode.setCurrentIndex(0 if is_auto_stop else 1)
        form_stop.addRow("Stop Mode", self.stop_mode)
        v_stop.addLayout(form_stop)

        self.auto_stop_cb = QCheckBox("Auto Stop on silence")
        self.auto_stop_cb.setChecked(is_auto_stop)
        self.auto_stop_cb.setVisible(False)

        self.preview_cb = QCheckBox("Show live transcript preview while speaking")
        self.preview_cb.setChecked(bool(data.get("show_interim_preview", True)))
        v_stop.addWidget(self.preview_cb)

        self.voice_commands_cb = QCheckBox("Enable Voice Commands (e.g. 'new line', 'comma', 'period')")
        self.voice_commands_cb.setChecked(bool(data.get("voice_commands", True)))
        v_stop.addWidget(self.voice_commands_cb)

        self.silence_container = QWidget()
        silence_layout = QVBoxLayout(self.silence_container)
        silence_layout.setContentsMargins(0, 0, 0, 0)
        silence_layout.setSpacing(6)

        row = QHBoxLayout()
        row.addWidget(QLabel("Silence threshold before auto-stopping (seconds):"))
        self.vad_silence = QDoubleSpinBox()
        self.vad_silence.setRange(0.3, 5.0)
        self.vad_silence.setSingleStep(0.1)
        self.vad_silence.setValue(float(data.get("vad_silence_seconds", 1.4)))
        row.addWidget(self.vad_silence)
        row.addStretch()
        silence_layout.addLayout(row)

        self.silence_helper = QLabel("Dictate automatically grants extra thinking time when you pause mid-sentence.")
        self.silence_helper.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 2px;")
        silence_layout.addWidget(self.silence_helper)
        v_stop.addWidget(self.silence_container)

        self.manual_helper = QLabel("Manual Mode: Dictate will record continuously until you click the floating pill, tray icon, or press your hotkey.")
        self.manual_helper.setStyleSheet("color: #38BDF8; font-size: 11px; margin-top: 2px;")
        self.manual_helper.setWordWrap(True)
        v_stop.addWidget(self.manual_helper)

        def _on_stop_mode_changed():
            auto = bool(self.stop_mode.currentData())
            self.auto_stop_cb.setChecked(auto)
            self.silence_container.setVisible(auto)
            self.manual_helper.setVisible(not auto)

        self.stop_mode.currentIndexChanged.connect(_on_stop_mode_changed)
        _on_stop_mode_changed()

        layout.addWidget(grp_stop)
        layout.addStretch()
        return page

    def _build_audio_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        # Group 1: Device Selection
        grp_dev = QGroupBox("Microphone Input")
        form_dev = QFormLayout(grp_dev)
        form_dev.setSpacing(12)

        self.mic_device = QComboBox()
        self.mic_device.addItem("Default System Microphone", None)
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d.get("max_input_channels", 0) > 0:
                    self.mic_device.addItem(f"{d['name']}", i)
        except Exception:
            pass
        cur_dev = data.get("input_device")
        idx = self.mic_device.findData(cur_dev)
        if idx >= 0:
            self.mic_device.setCurrentIndex(idx)
        form_dev.addRow("Input Device", self.mic_device)
        layout.addWidget(grp_dev)

        # Group 2: Real-time Level Test
        grp_test = QGroupBox("Microphone Test")
        v_test = QVBoxLayout(grp_test)
        self.mic_tester = MicTestWidget()
        v_test.addWidget(self.mic_tester)
        layout.addWidget(grp_test)

        layout.addStretch()
        return page

    def _build_advanced_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        # Group 1: Speech Engine & Acceleration
        grp_model = QGroupBox("Speech Recognition Engine (On-Device)")
        form_model = QFormLayout(grp_model)
        form_model.setSpacing(12)

        self.model = QComboBox()
        from asr.model_manager import is_model_cached

        parakeet_status = "Ready" if is_model_cached("parakeet-tdt-0.6b-v3") else "Auto-download"
        sensevoice_status = "Ready" if is_model_cached("sense-voice-small") else "Auto-download"
        fastconformer_status = "Ready" if is_model_cached("nemo-fast-conformer-80ms") else "Auto-download"
        paraformer_status = "Ready" if is_model_cached("paraformer-zh-en") else "Auto-download"

        models = [
            (f"NVIDIA Parakeet TDT 0.6B v3 (English FastConformer, ~250MB) [{parakeet_status}]", "parakeet-tdt-0.6b-v3"),
            (f"Alibaba SenseVoice Small (Multilingual Fast + ITN, ~110MB) [{sensevoice_status}]", "sense-voice-small"),
        ]

        for label, val in models:
            self.model.addItem(label, val)
        curr = data.get("model", "parakeet-tdt-0.6b-v3")
        idx = self.model.findData(curr)
        if idx >= 0:
            self.model.setCurrentIndex(idx)
        form_model.addRow("Speech Model (Final)", self.model)

        self.streaming_model = QComboBox()
        streaming_models = [
            (f"NVIDIA FastConformer CTC 80ms (Real-Time Preview, ~420MB) [{fastconformer_status}]", "nemo-fast-conformer-80ms"),
            (f"Alibaba Streaming Paraformer (Bilingual ZH/EN, ~235MB) [{paraformer_status}]", "paraformer-zh-en"),
        ]
        for label, val in streaming_models:
            self.streaming_model.addItem(label, val)
        curr_streaming = data.get("streaming_model", "nemo-fast-conformer-80ms")
        s_idx = self.streaming_model.findData(curr_streaming)
        if s_idx >= 0:
            self.streaming_model.setCurrentIndex(s_idx)
        form_model.addRow("Real-Time Preview Model", self.streaming_model)

        self.device = QComboBox()
        self.device.addItem("Auto-detect (GPU with CPU fallback)", "auto")
        self.device.addItem("CPU only", "cpu")
        self.device.addItem("CUDA GPU (NVIDIA)", "cuda")
        idx = self.device.findData(data.get("device", "auto"))
        if idx >= 0:
            self.device.setCurrentIndex(idx)
        form_model.addRow("Hardware Acceleration", self.device)
        layout.addWidget(grp_model)

        # Group 2: Custom Vocabulary
        grp_vocab = QGroupBox("Custom Vocabulary & Phrase Boosting")
        form_vocab = QFormLayout(grp_vocab)
        form_vocab.setSpacing(12)

        self.hotwords_file = QLineEdit(data.get("hotwords_file", "hotwords.txt"))
        form_vocab.addRow("Hotwords File", self.hotwords_file)

        self.hotwords_score = QDoubleSpinBox()
        self.hotwords_score.setRange(0.5, 10.0)
        self.hotwords_score.setSingleStep(0.5)
        self.hotwords_score.setValue(float(data.get("hotwords_score", 2.0)))
        form_vocab.addRow("Acoustic Boost Score", self.hotwords_score)

        self.initial_prompt = QLineEdit(data.get("initial_prompt", ""))
        self.initial_prompt.setPlaceholderText("Additional custom technical terms…")
        form_vocab.addRow("Extra Keywords", self.initial_prompt)
        layout.addWidget(grp_vocab)

        # Group 3: Optional Cloud AI Polish (Opt-in with clear privacy disclosure)
        grp_ai = QGroupBox("Optional Cloud AI Polish")
        v_ai = QVBoxLayout(grp_ai)
        v_ai.setSpacing(12)

        disclosure = QLabel(
            "Privacy Notice: Audio is transcribed 100% locally on your device. "
            "When enabled, only the final transcribed text is sent to the chosen cloud AI provider to clean filler words and grammar."
        )
        disclosure.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.4;")
        disclosure.setWordWrap(True)
        v_ai.addWidget(disclosure)

        self.ai_enable_cb = QCheckBox("Enable Cloud AI Polish")
        self.ai_enable_cb.setChecked(bool(data.get("ai_polish", False)))
        v_ai.addWidget(self.ai_enable_cb)

        self.ai_container = QWidget()
        form_ai = QFormLayout(self.ai_container)
        form_ai.setContentsMargins(0, 4, 0, 0)
        form_ai.setSpacing(12)

        self.ai_provider = QComboBox()
        self.ai_provider.addItem("OpenRouter (Free & Fast LLMs — GLM, Llama, Gemini)", "openrouter")
        self.ai_provider.addItem("NVIDIA NIM Cloud (Build.nvidia.com)", "nvidia")
        cur_prov = data.get("ai_polish_provider", "openrouter")
        idx = self.ai_provider.findData(cur_prov)
        if idx >= 0:
            self.ai_provider.setCurrentIndex(idx)
        form_ai.addRow("AI Provider", self.ai_provider)

        self.ai_polish_api_key = QLineEdit()
        self.ai_polish_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form_ai.addRow("API Key", self.ai_polish_api_key)

        self.ai_polish_base_url = QLineEdit()
        form_ai.addRow("Base URL", self.ai_polish_base_url)

        self.ai_polish_model = QComboBox()
        self.ai_polish_model.setEditable(True)
        form_ai.addRow("AI Model", self.ai_polish_model)

        self._provider_data = {
            "openrouter": {
                "key": data.get("ai_polish_api_key_openrouter") or (data.get("ai_polish_api_key", "") if cur_prov == "openrouter" else ""),
                "url": data.get("ai_polish_base_url_openrouter", "https://openrouter.ai/api/v1"),
                "model": data.get("ai_polish_model_openrouter", "minimax/minimax-m3:free"),
                "models": [
                    ("minimax/minimax-m3:free (Recommended Free)", "minimax/minimax-m3:free"),
                    ("meta-llama/llama-3.3-70b-instruct:free", "meta-llama/llama-3.3-70b-instruct:free"),
                    ("google/gemini-2.0-flash-exp:free", "google/gemini-2.0-flash-exp:free"),
                    ("deepseek/deepseek-chat", "deepseek/deepseek-chat"),
                ],
                "placeholder": "API Key (sk-or-v1-...)",
            },
            "nvidia": {
                "key": data.get("ai_polish_api_key_nvidia") or (data.get("ai_polish_api_key", "") if cur_prov == "nvidia" else ""),
                "url": data.get("ai_polish_base_url_nvidia", "https://integrate.api.nvidia.com/v1"),
                "model": data.get("ai_polish_model_nvidia", "nvidia/nemotron-3-nano-30b-a3b"),
                "models": [
                    ("nvidia/nemotron-3-nano-30b-a3b", "nvidia/nemotron-3-nano-30b-a3b"),
                    ("meta/llama-3.1-70b-instruct", "meta/llama-3.1-70b-instruct"),
                ],
                "placeholder": "API Key (nvapi-...)",
            },
        }

        def _update_provider_ui(prov: str):
            info = self._provider_data.get(prov, self._provider_data["openrouter"])
            self.ai_polish_api_key.setText(info["key"])
            self.ai_polish_api_key.setPlaceholderText(info["placeholder"])
            self.ai_polish_base_url.setText(info["url"])
            self.ai_polish_model.clear()
            for label, val in info["models"]:
                self.ai_polish_model.addItem(label, val)
            cur_m = info["model"]
            m_idx = self.ai_polish_model.findData(cur_m)
            if m_idx >= 0:
                self.ai_polish_model.setCurrentIndex(m_idx)
            else:
                self.ai_polish_model.setCurrentText(cur_m)

        def _on_provider_changed():
            prov = self.ai_provider.currentData()
            _update_provider_ui(prov)

        self.ai_provider.currentIndexChanged.connect(_on_provider_changed)
        _update_provider_ui(cur_prov)

        def _toggle_ai_visibility(checked: bool):
            self.ai_container.setVisible(checked)

        self.ai_enable_cb.toggled.connect(_toggle_ai_visibility)
        _toggle_ai_visibility(self.ai_enable_cb.isChecked())

        v_ai.addWidget(self.ai_container)
        layout.addWidget(grp_ai)

        layout.addStretch()
        return page

    def values(self) -> dict:
        cur_prov = self.ai_provider.currentData() or "openrouter"
        cur_model = self.ai_polish_model.currentData() or self.ai_polish_model.currentText().strip()
        cur_key = self.ai_polish_api_key.text().strip()
        cur_url = self.ai_polish_base_url.text().strip()

        if cur_prov in self._provider_data:
            self._provider_data[cur_prov]["key"] = cur_key
            self._provider_data[cur_prov]["url"] = cur_url
            self._provider_data[cur_prov]["model"] = cur_model

        return {
            "mode": self.mode.currentData(),
            "trigger_key": self.key_btn.key,
            "model": self.model.currentData() or self.model.currentText(),
            "device": self.device.currentData(),
            "hotwords_file": self.hotwords_file.text().strip(),
            "hotwords_score": round(self.hotwords_score.value(), 1),
            "initial_prompt": self.initial_prompt.text().strip(),
            "input_device": self.mic_device.currentData(),
            "restore_clipboard": self.restore_cb.isChecked(),
            "autostart": self.autostart_cb.isChecked(),
            "auto_stop": self.auto_stop_cb.isChecked(),
            "vad_silence_seconds": round(self.vad_silence.value(), 1),
            "voice_commands": self.voice_commands_cb.isChecked(),
            "show_interim_preview": self.preview_cb.isChecked(),
            "streaming_model": self.streaming_model.currentData() or self.streaming_model.currentText(),
            "ai_polish": self.ai_enable_cb.isChecked(),
            "ai_polish_provider": cur_prov,
            "ai_polish_api_key": cur_key,
            "ai_polish_base_url": cur_url,
            "ai_polish_model": cur_model,
            "ai_polish_api_key_openrouter": self._provider_data["openrouter"]["key"],
            "ai_polish_base_url_openrouter": self._provider_data["openrouter"]["url"],
            "ai_polish_model_openrouter": self._provider_data["openrouter"]["model"],
            "ai_polish_api_key_nvidia": self._provider_data["nvidia"]["key"],
            "ai_polish_base_url_nvidia": self._provider_data["nvidia"]["url"],
            "ai_polish_model_nvidia": self._provider_data["nvidia"]["model"],
        }

    def _on_save(self):
        if hasattr(self, "mic_tester"):
            self.mic_tester.cleanup()
        self.accept()

    def _on_cancel(self):
        if hasattr(self, "mic_tester"):
            self.mic_tester.cleanup()
        self.reject()

    def closeEvent(self, event):
        if hasattr(self, "mic_tester"):
            self.mic_tester.cleanup()
        super().closeEvent(event)
