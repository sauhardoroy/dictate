"""Modern Apple & Material-style Frosted Glass Settings Dialog (Zero Emoji, Clean Typography)."""
import sounddevice as sd
from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QLinearGradient,
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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class KeyCaptureButton(QPushButton):
    """Clean Material/Apple keycap capture button."""

    def __init__(self, current_key: str, parent=None):
        super().__init__(parent)
        self.key = current_key
        self.listening = False
        self._update_text()
        self.clicked.connect(self._toggle_listening)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)

    def _update_text(self):
        if self.listening:
            self.setText("Press shortcut key combination… (Esc to cancel)")
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(225, 29, 72, 0.15);
                    color: #FDA4AF;
                    border: 1px solid #E11D48;
                    border-radius: 6px;
                    font-weight: 500;
                    font-size: 12px;
                    padding: 0 12px;
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
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 0 14px;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #2D3D54;
                    border-color: #38BDF8;
                    color: #38BDF8;
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
    """Interactive live microphone test bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.btn_test = QPushButton("Test Microphone")
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.setFixedHeight(30)
        self.btn_test.setStyleSheet("""
            QPushButton {
                background: rgba(2, 132, 199, 0.15);
                color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 4px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(2, 132, 199, 0.30);
                border-color: #38BDF8;
            }
        """)
        self.btn_test.clicked.connect(self._toggle_test)
        header.addWidget(self.btn_test)

        self.lbl_status = QLabel("Click to speak and test input level")
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
                self.btn_test.setStyleSheet("""
                    QPushButton {
                        background: rgba(225, 29, 72, 0.20);
                        color: #FDA4AF;
                        border: 1px solid #E11D48;
                        border-radius: 6px;
                        padding: 4px 14px;
                        font-weight: 600;
                        font-size: 11px;
                    }
                """)
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
            self.btn_test.setStyleSheet("""
                QPushButton {
                    background: rgba(2, 132, 199, 0.15);
                    color: #38BDF8;
                    border: 1px solid rgba(56, 189, 248, 0.35);
                    border-radius: 6px;
                    padding: 4px 14px;
                    font-weight: 600;
                    font-size: 11px;
                }
            """)
            self.lbl_status.setText("Test stopped")
            self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px;")
            self.meter.setValue(0)

    def _update_meter(self):
        val = int(min(100.0, self._current_level * 300.0))
        self.meter.setValue(val)

    def cleanup(self):
        self._stop()


class SegmentedNavBar(QWidget):
    """Clean Apple/Material Segmented Tab Navigation with smooth sliding pill highlight."""

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
        self._anim.setDuration(180)
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
        radius = 8.0

        # Track Background (Frosted Glass)
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        p.setBrush(QColor(30, 41, 59, 160))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)

        # Sliding Highlight Capsule
        if self._indicator_w > 0:
            pill_rect = QRectF(self._indicator_x + 1.0, 3.0, self._indicator_w - 2.0, h - 6.0)
            p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
            p.setBrush(QColor(255, 255, 255, 28))
            p.drawRoundedRect(pill_rect, 6.0, 6.0)

        # Clean Text Labels
        font = QFont(self.font())
        font.setPointSize(10)
        font.setWeight(QFont.Weight.DemiBold)
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
        self._fade_anim.setDuration(160)
        self._fade_anim.setStartValue(0.15)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(lambda: next_widget.setGraphicsEffect(None))
        self._fade_anim.start()


class FrostedCard(QFrame):
    """Material/Apple styled frosted glass container card."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("frostedCard")
        self.setStyleSheet("""
            QFrame#frostedCard {
                background-color: rgba(30, 41, 59, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        self.layout_box = QVBoxLayout(self)
        self.layout_box.setContentsMargins(18, 16, 18, 16)
        self.layout_box.setSpacing(12)

        if title:
            lbl = QLabel(title.upper())
            lbl.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 700; letter-spacing: 0.06em;")
            self.layout_box.addWidget(lbl)


class SettingsDialog(QDialog):
    """Material & Apple-inspired Frosted Glass Preferences Dialog."""

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dictate Settings")
        self.setFixedSize(580, 560)
        self._apply_global_style()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)

        # 1. Header (Clean, Minimalist, No Emojis)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        lbl_title = QLabel("Settings")
        lbl_title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: 700; letter-spacing: -0.02em;")
        title_box.addWidget(lbl_title)

        lbl_sub = QLabel("Configure voice typing, offline models, and AI polish")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(lbl_sub)

        root.addLayout(title_box)

        # 2. Segmented Navigation Bar
        tab_names = ["Dictation", "Speech Model", "Microphone", "Behavior", "AI Polish"]
        self.nav_bar = SegmentedNavBar(tab_names)
        root.addWidget(self.nav_bar)

        # 3. Stacked Content Pages
        self.pages = AnimatedStackedWidget()
        data = current_settings
        self.pages.addWidget(self._build_dictation_page(data))
        self.pages.addWidget(self._build_model_page(data))
        self.pages.addWidget(self._build_audio_page(data))
        self.pages.addWidget(self._build_behavior_page(data))
        self.pages.addWidget(self._build_ai_page(data))

        self.nav_bar.currentChanged.connect(self.pages.slide_to_index)
        root.addWidget(self.pages, 1)

        # 4. Bottom Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 0 18px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.06);
                color: #F8FAFC;
                border-color: rgba(255, 255, 255, 0.20);
            }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setFixedHeight(34)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_save.clicked.connect(self._on_save)
        btn_box.addWidget(self.btn_save)

        root.addLayout(btn_box)

    def _apply_global_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            QLabel {
                color: #F8FAFC;
                font-size: 13px;
            }
            QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                min-height: 20px;
            }
            QComboBox:hover, QComboBox:focus {
                border-color: #38BDF8;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                selection-background-color: #0284C7;
                selection-color: #FFFFFF;
                outline: none;
                padding: 4px;
            }
            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QLineEdit:hover, QLineEdit:focus {
                border-color: #38BDF8;
            }
            QDoubleSpinBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QDoubleSpinBox:hover, QDoubleSpinBox:focus {
                border-color: #38BDF8;
            }
            QCheckBox {
                spacing: 10px;
                font-size: 13px;
                color: #F8FAFC;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.18);
                background-color: #1E293B;
            }
            QCheckBox::indicator:checked {
                background-color: #0284C7;
                border-color: #0284C7;
            }
        """)

    def _build_dictation_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        # Card 1: Trigger Mode
        card1 = FrostedCard("Activation Mode")
        form1 = QFormLayout()
        form1.setSpacing(12)
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.mode = QComboBox()
        self.mode.addItem("Hold to Talk (Push-to-Talk)", "ptt")
        self.mode.addItem("Press to Start / Stop (Toggle)", "toggle")
        idx = self.mode.findData(data.get("mode", "ptt"))
        if idx >= 0:
            self.mode.setCurrentIndex(idx)
        form1.addRow("Trigger Mode", self.mode)

        self.key_btn = KeyCaptureButton(data.get("trigger_key", "ctrl+shift+p"))
        form1.addRow("Global Shortcut", self.key_btn)
        card1.layout_box.addLayout(form1)
        layout.addWidget(card1)

        # Card 2: Smart Auto-Stop & Commands
        card2 = FrostedCard("Smart Auto-Stop & Punctuation")
        v2 = QVBoxLayout()
        v2.setSpacing(12)

        self.voice_commands_cb = QCheckBox("Enable Voice Commands (e.g. 'new line', 'comma', 'period')")
        self.voice_commands_cb.setChecked(bool(data.get("voice_commands", True)))
        v2.addWidget(self.voice_commands_cb)

        self.auto_stop_cb = QCheckBox("Adaptive Semantic Auto-Stop on silence")
        self.auto_stop_cb.setChecked(bool(data.get("auto_stop", True)))
        v2.addWidget(self.auto_stop_cb)

        row = QHBoxLayout()
        row.addWidget(QLabel("Base silence threshold (seconds):"))
        self.vad_silence = QDoubleSpinBox()
        self.vad_silence.setRange(0.3, 4.0)
        self.vad_silence.setSingleStep(0.1)
        self.vad_silence.setValue(float(data.get("vad_silence_seconds", 1.4)))
        row.addWidget(self.vad_silence)
        row.addStretch()
        v2.addLayout(row)

        helper = QLabel("Dictate automatically grants extra thinking time when you pause mid-sentence.")
        helper.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 2px;")
        v2.addWidget(helper)

        card2.layout_box.addLayout(v2)
        layout.addWidget(card2)

        layout.addStretch()
        return page

    def _build_model_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        card = FrostedCard("Offline Speech Recognition")
        form = QFormLayout()
        form.setSpacing(12)

        self.model = QComboBox()
        models = [
            ("small.en (Recommended, ~460MB)", "small.en"),
            ("base.en (Fast, ~140MB)", "base.en"),
            ("tiny.en (Fastest, ~75MB)", "tiny.en"),
            ("medium.en (High accuracy, ~1.5GB)", "medium.en"),
            ("large-v3 (Multilingual, ~3GB)", "large-v3"),
        ]
        for label, val in models:
            self.model.addItem(label, val)
        curr = data.get("model", "small.en")
        idx = self.model.findData(curr)
        if idx >= 0:
            self.model.setCurrentIndex(idx)
        else:
            self.model.setCurrentText(curr)
        form.addRow("Whisper Model", self.model)

        self.device = QComboBox()
        self.device.addItem("Auto-detect (GPU with CPU fallback)", "auto")
        self.device.addItem("CPU only", "cpu")
        self.device.addItem("CUDA GPU (NVIDIA)", "cuda")
        idx = self.device.findData(data.get("device", "auto"))
        if idx >= 0:
            self.device.setCurrentIndex(idx)
        form.addRow("Hardware Acceleration", self.device)

        self.initial_prompt = QLineEdit(data.get("initial_prompt", ""))
        self.initial_prompt.setPlaceholderText("Custom terms, names, product vocabulary...")
        form.addRow("Prompt Vocabulary", self.initial_prompt)

        card.layout_box.addLayout(form)
        layout.addWidget(card)

        layout.addStretch()
        return page

    def _build_audio_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        # Card 1: Device Selection
        card1 = FrostedCard("Microphone Input")
        form1 = QFormLayout()
        form1.setSpacing(12)

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
        form1.addRow("Input Device", self.mic_device)
        card1.layout_box.addLayout(form1)
        layout.addWidget(card1)

        # Card 2: Live Level Test
        card2 = FrostedCard("Live Level Meter")
        self.mic_tester = MicTestWidget()
        card2.layout_box.addWidget(self.mic_tester)
        layout.addWidget(card2)

        layout.addStretch()
        return page

    def _build_behavior_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        card = FrostedCard("System Integration")
        v = QVBoxLayout()
        v.setSpacing(14)

        self.restore_cb = QCheckBox("Restore previous clipboard content after typing")
        self.restore_cb.setChecked(bool(data.get("restore_clipboard", True)))
        v.addWidget(self.restore_cb)

        self.autostart_cb = QCheckBox("Launch Dictate automatically on Windows startup")
        self.autostart_cb.setChecked(bool(data.get("autostart", False)))
        v.addWidget(self.autostart_cb)

        card.layout_box.addLayout(v)
        layout.addWidget(card)

        layout.addStretch()
        return page

    def _build_ai_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        card = FrostedCard("NVIDIA AI Cloud Grammar Polish")
        v = QVBoxLayout()
        v.setSpacing(12)

        self.ai_enable_cb = QCheckBox("Enable NVIDIA Cloud AI Polish (removes filler words and corrects grammar)")
        self.ai_enable_cb.setChecked(bool(data.get("ai_polish", False)))
        v.addWidget(self.ai_enable_cb)

        notice = QLabel(
            "Dictate runs 100% offline by default. Enabling this uses NVIDIA's hosted LLMs (NVIDIA NIM). "
            "Get a free API key at build.nvidia.com."
        )
        notice.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.4;")
        notice.setWordWrap(True)
        v.addWidget(notice)

        form = QFormLayout()
        form.setSpacing(12)

        self.ai_polish_api_key = QLineEdit(data.get("ai_polish_api_key", ""))
        self.ai_polish_api_key.setPlaceholderText("API Key (nvapi-...)")
        self.ai_polish_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key", self.ai_polish_api_key)

        self.ai_polish_base_url = QLineEdit(data.get("ai_polish_base_url", "https://integrate.api.nvidia.com/v1"))
        form.addRow("Base URL", self.ai_polish_base_url)

        self.ai_polish_model = QComboBox()
        self.ai_polish_model.setEditable(True)
        nvidia_models = [
            ("nvidia/nemotron-3-nano-30b-a3b", "nvidia/nemotron-3-nano-30b-a3b"),
            ("meta/muse-glimmer-30b", "meta/muse-glimmer-30b"),
        ]
        for label, val in nvidia_models:
            self.ai_polish_model.addItem(label, val)

        cur_model = data.get("ai_polish_model", "nvidia/nemotron-3-nano-30b-a3b")
        idx = self.ai_polish_model.findData(cur_model)
        if idx >= 0:
            self.ai_polish_model.setCurrentIndex(idx)
        else:
            self.ai_polish_model.setCurrentText(cur_model)

        form.addRow("AI Model", self.ai_polish_model)
        v.addLayout(form)

        card.layout_box.addLayout(v)
        layout.addWidget(card)

        layout.addStretch()
        return page

    def values(self) -> dict:
        cur_model = self.ai_polish_model.currentData() or self.ai_polish_model.currentText().strip()
        return {
            "mode": self.mode.currentData(),
            "trigger_key": self.key_btn.key,
            "model": self.model.currentData() or self.model.currentText(),
            "device": self.device.currentData(),
            "initial_prompt": self.initial_prompt.text().strip(),
            "input_device": self.mic_device.currentData(),
            "restore_clipboard": self.restore_cb.isChecked(),
            "autostart": self.autostart_cb.isChecked(),
            "auto_stop": self.auto_stop_cb.isChecked(),
            "vad_silence_seconds": round(self.vad_silence.value(), 1),
            "voice_commands": self.voice_commands_cb.isChecked(),
            "ai_polish": self.ai_enable_cb.isChecked(),
            "ai_polish_api_key": self.ai_polish_api_key.text().strip(),
            "ai_polish_base_url": self.ai_polish_base_url.text().strip(),
            "ai_polish_model": cur_model,
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
