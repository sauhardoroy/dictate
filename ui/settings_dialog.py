"""Modern Apple & Material-style Frosted Glass Settings Dialog (Zero Emoji, Clean Typography)."""
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

        # Card 2: Smart Auto-Stop & Punctuation
        card2 = FrostedCard("Listening & Stopping Control")
        v2 = QVBoxLayout()
        v2.setSpacing(12)

        form2 = QFormLayout()
        form2.setSpacing(12)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.stop_mode = QComboBox()
        self.stop_mode.addItem("Automatically stop on silence (Auto-Stop)", True)
        self.stop_mode.addItem("Manual stop (Click floating pill, tray icon, or shortcut)", False)
        is_auto_stop = bool(data.get("auto_stop", True))
        self.stop_mode.setCurrentIndex(0 if is_auto_stop else 1)
        form2.addRow("Stop Listening Mode", self.stop_mode)
        v2.addLayout(form2)

        self.auto_stop_cb = QCheckBox("Adaptive Semantic Auto-Stop on silence")
        self.auto_stop_cb.setChecked(is_auto_stop)
        self.auto_stop_cb.setVisible(False)

        self.preview_cb = QCheckBox("Show live transcript preview while recording")
        self.preview_cb.setChecked(bool(data.get("show_interim_preview", True)))
        v2.addWidget(self.preview_cb)

        self.voice_commands_cb = QCheckBox("Enable Voice Commands (e.g. 'new line', 'comma', 'period')")
        self.voice_commands_cb.setChecked(bool(data.get("voice_commands", True)))
        v2.addWidget(self.voice_commands_cb)

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
        v2.addWidget(self.silence_container)

        self.manual_helper = QLabel("💡 Manual Mode active: Dictate will record continuously without cutting you off. Click the floating pill, tray icon, or press your hotkey when done.")
        self.manual_helper.setStyleSheet("color: #38BDF8; font-size: 11px; margin-top: 2px;")
        self.manual_helper.setWordWrap(True)
        v2.addWidget(self.manual_helper)

        def _on_stop_mode_changed():
            auto = bool(self.stop_mode.currentData())
            self.auto_stop_cb.setChecked(auto)
            self.silence_container.setVisible(auto)
            self.manual_helper.setVisible(not auto)

        self.stop_mode.currentIndexChanged.connect(_on_stop_mode_changed)
        _on_stop_mode_changed()

        card2.layout_box.addLayout(v2)
        layout.addWidget(card2)

        layout.addStretch()
        return page

    def _build_model_page(self, data: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        # Card 1: Model & Hardware
        card = FrostedCard("Sherpa-ONNX Speech Models (NVIDIA & Alibaba)")
        form = QFormLayout()
        form.setSpacing(12)

        self.model = QComboBox()
        from asr.model_manager import is_model_cached
        
        parakeet_status = "✓ Ready" if is_model_cached("parakeet-tdt-0.6b-v3") else "↓ Auto-download"
        sensevoice_status = "✓ Ready" if is_model_cached("sense-voice-small") else "↓ Auto-download"
        fastconformer_status = "✓ Ready" if is_model_cached("nemo-fast-conformer-80ms") else "↓ Auto-download"

        models = [
            (f"🚀 NVIDIA Parakeet TDT 0.6B v3 (English FastConformer, ~250MB) [{parakeet_status}]", "parakeet-tdt-0.6b-v3"),
            (f"🌐 Alibaba SenseVoice Small (Multilingual 50x Fast + ITN, ~110MB) [{sensevoice_status}]", "sense-voice-small"),
        ]

        for label, val in models:
            self.model.addItem(label, val)
        curr = data.get("model", "parakeet-tdt-0.6b-v3")
        idx = self.model.findData(curr)
        if idx >= 0:
            self.model.setCurrentIndex(idx)
        else:
            self.model.setCurrentIndex(0)
        form.addRow("Speech Model (Final)", self.model)

        self.streaming_model = QComboBox()
        streaming_models = [
            (f"🚀 NVIDIA FastConformer CTC 80ms (Real-Time Preview, ~420MB) [{fastconformer_status}]", "nemo-fast-conformer-80ms"),
        ]
        for label, val in streaming_models:
            self.streaming_model.addItem(label, val)
        self.streaming_model.setCurrentIndex(0)
        form.addRow("Real-Time Preview Model", self.streaming_model)

        self.device = QComboBox()
        self.device.addItem("Auto-detect (GPU with CPU fallback)", "auto")
        self.device.addItem("CPU only", "cpu")
        self.device.addItem("CUDA GPU (NVIDIA)", "cuda")
        idx = self.device.findData(data.get("device", "auto"))
        if idx >= 0:
            self.device.setCurrentIndex(idx)
        form.addRow("Hardware Acceleration", self.device)

        card.layout_box.addLayout(form)
        layout.addWidget(card)

        # Card 2: Custom Jargon & Hotwords Phrase Boosting
        card2 = FrostedCard("Custom Vocabulary & Phrase Boosting")
        v2 = QVBoxLayout()
        v2.setSpacing(10)

        form2 = QFormLayout()
        form2.setSpacing(12)

        self.hotwords_file = QLineEdit(data.get("hotwords_file", "hotwords.txt"))
        self.hotwords_file.setPlaceholderText("Path to hotwords.txt")
        form2.addRow("Hotwords File", self.hotwords_file)

        self.hotwords_score = QDoubleSpinBox()
        self.hotwords_score.setRange(0.5, 10.0)
        self.hotwords_score.setSingleStep(0.5)
        self.hotwords_score.setValue(float(data.get("hotwords_score", 2.0)))
        form2.addRow("Acoustic Boost Score", self.hotwords_score)

        self.initial_prompt = QLineEdit(data.get("initial_prompt", ""))
        self.initial_prompt.setPlaceholderText("Additional custom vocabulary...")
        form2.addRow("Extra Keywords", self.initial_prompt)

        v2.addLayout(form2)

        # Check hotwords file status
        hw_file = data.get("hotwords_file", "hotwords.txt")
        hw_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), hw_file)
        hw_count = 0
        if os.path.exists(hw_path):
            try:
                with open(hw_path, "r", encoding="utf-8") as f:
                    hw_count = sum(1 for line in f if line.strip() and not line.startswith("#"))
            except Exception:
                pass

        if hw_count > 0:
            lbl_status = QLabel(f"✓ Active: {hw_count:,} technical keywords & jargon loaded from {hw_file}")
            lbl_status.setStyleSheet("color: #38BDF8; font-weight: 500; font-size: 12px; margin-top: 4px;")
        else:
            lbl_status = QLabel(f"ℹ No hotwords file found at {hw_file}. Create it to boost domain terms.")
            lbl_status.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 4px;")
        v2.addWidget(lbl_status)

        card2.layout_box.addLayout(v2)
        layout.addWidget(card2)

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

        card = FrostedCard("AI Cloud Grammar & Dictation Polish")
        v = QVBoxLayout()
        v.setSpacing(12)

        self.ai_enable_cb = QCheckBox("Enable Cloud AI Polish (removes filler words, cleans repetitions & formats grammar)")
        self.ai_enable_cb.setChecked(bool(data.get("ai_polish", True)))
        v.addWidget(self.ai_enable_cb)

        form = QFormLayout()
        form.setSpacing(12)

        self.ai_provider = QComboBox()
        self.ai_provider.addItem("OpenRouter (Free & Fast LLMs — GLM, Llama, Gemini)", "openrouter")
        self.ai_provider.addItem("NVIDIA NIM Cloud (Build.nvidia.com)", "nvidia")
        cur_prov = data.get("ai_polish_provider", "openrouter")
        idx = self.ai_provider.findData(cur_prov)
        if idx >= 0:
            self.ai_provider.setCurrentIndex(idx)
        form.addRow("AI Provider", self.ai_provider)

        self.ai_notice = QLabel("")
        self.ai_notice.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.4;")
        self.ai_notice.setWordWrap(True)
        form.addRow("", self.ai_notice)

        self.ai_polish_api_key = QLineEdit()
        self.ai_polish_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key", self.ai_polish_api_key)

        self.ai_polish_base_url = QLineEdit()
        form.addRow("Base URL", self.ai_polish_base_url)

        self.ai_polish_model = QComboBox()
        self.ai_polish_model.setEditable(True)
        form.addRow("AI Model", self.ai_polish_model)

        # Store initial settings for both providers
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
                "notice": "OpenRouter provides free and fast open-weights LLMs for instant punctuation and verbatim speech cleanup.",
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
                "notice": "NVIDIA NIM hosted models at build.nvidia.com for high-throughput speech transcription cleanup.",
            },
        }

        def _update_provider_ui(prov: str):
            info = self._provider_data.get(prov, self._provider_data["openrouter"])
            self.ai_polish_api_key.setText(info["key"])
            self.ai_polish_api_key.setPlaceholderText(info["placeholder"])
            self.ai_polish_base_url.setText(info["url"])
            self.ai_notice.setText(info["notice"])

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

        v.addLayout(form)
        card.layout_box.addLayout(v)
        layout.addWidget(card)

        layout.addStretch()
        return page

    def values(self) -> dict:
        cur_prov = self.ai_provider.currentData() or "openrouter"
        cur_model = self.ai_polish_model.currentData() or self.ai_polish_model.currentText().strip()
        cur_key = self.ai_polish_api_key.text().strip()
        cur_url = self.ai_polish_base_url.text().strip()

        # Update cached per-provider values
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
