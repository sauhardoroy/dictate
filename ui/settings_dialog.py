"""
settings_dialog.py — Preferences Dialog (Material 3 Monochrome)

Organized into 4 resilient categories:
1. General — Startup, clipboard restoration, theme selection.
2. Dictation — Activation mode, global shortcut capture, stop listening controls, live preview, and voice commands.
3. Audio — Input device selection and interactive real-time microphone tester.
4. Advanced — Speech models, hardware acceleration, custom jargon boosting, and optional Cloud AI Polish (opt-in with privacy disclosures).
"""

from __future__ import annotations

import sys
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QStackedWidget, QComboBox, QCheckBox, QLineEdit,
    QDoubleSpinBox, QFileDialog, QSizePolicy, QScrollArea, QPushButton,
)

from ui.material_theme import Tokens, build_qss, Shape
from ui.widgets import (
    ToggleSwitch, KeyCaptureButton, LevelMeter, SegmentedTabBar,
    StatusPill, make_card, make_hairline, make_button, make_label,
)

try:
    import sounddevice as sd
    import numpy as np
    _AUDIO_AVAILABLE = True
except Exception:
    _AUDIO_AVAILABLE = False


TABS = ["General", "Dictation", "Audio", "Advanced"]

FINAL_MODELS = [
    ("parakeet-tdt-0.6b-v3", "NVIDIA Parakeet TDT 0.6B v3 (English FastConformer, ~250MB)"),
    ("sense-voice-small", "Alibaba SenseVoice Small (Multilingual Fast + ITN, ~110MB)"),
]

PREVIEW_MODELS = [
    ("nemo-fast-conformer-80ms", "NVIDIA FastConformer CTC 80ms (Real-Time Preview, ~420MB)"),
    ("paraformer-zh-en", "Alibaba Streaming Paraformer (Bilingual ZH/EN, ~235MB)"),
]

HW_ACCEL_OPTIONS = [
    ("auto", "Auto-detect (GPU with CPU fallback)"),
    ("cpu", "CPU only"),
    ("cuda", "CUDA GPU (NVIDIA)"),
]

CLOUD_PROVIDERS = [
    ("openrouter", "OpenRouter (Free & Fast LLMs — GLM, Llama, Gemini)"),
    ("nvidia", "NVIDIA NIM Cloud (Build.nvidia.com)"),
]

CLOUD_MODELS_BY_PROVIDER = {
    "openrouter": [
        ("minimax/minimax-m3:free (Recommended Free)", "minimax/minimax-m3:free"),
        ("meta-llama/llama-3.3-70b-instruct:free", "meta-llama/llama-3.3-70b-instruct:free"),
        ("google/gemini-2.0-flash-exp:free", "google/gemini-2.0-flash-exp:free"),
        ("deepseek/deepseek-chat", "deepseek/deepseek-chat"),
    ],
    "nvidia": [
        ("nvidia/nemotron-3-nano-30b-a3b", "nvidia/nemotron-3-nano-30b-a3b"),
        ("meta/llama-3.1-70b-instruct", "meta/llama-3.1-70b-instruct"),
    ],
}

DEFAULT_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
}


def _row(text: str, detail: str, control: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    text_col = QVBoxLayout()
    text_col.setSpacing(2)
    text_col.addWidget(make_label(text, "body", wrap=False))
    if detail:
        text_col.addWidget(make_label(detail, "body_sm", wrap=False))
    row.addLayout(text_col)
    row.addStretch()
    row.addWidget(control)
    return row


def _section_header(title: str) -> QLabel:
    return make_label(title.upper(), "label_caps")


class AppleToggle(ToggleSwitch):
    """Compatibility alias for ToggleSwitch."""
    pass


class MicTestWidget(QWidget):
    """Interactive live microphone test bar with accessible status."""

    def __init__(self, tokens: Tokens, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.btn_test = make_button("Test Microphone", "secondary")
        self.btn_test.clicked.connect(self._toggle_test)
        header.addWidget(self.btn_test)

        self.lbl_status = make_label("Idle — click “Test Microphone” to check audio input.", "body_sm")
        header.addWidget(self.lbl_status, 1)
        layout.addLayout(header)

        self.level_meter = LevelMeter(tokens)
        layout.addWidget(self.level_meter)

        self.stream = None
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._update_meter)
        self._current_level = 0.0

        if not _AUDIO_AVAILABLE:
            self.btn_test.setEnabled(False)
            self.lbl_status.setText("sounddevice is not installed in this environment.")

    def _audio_callback(self, indata, frames, time_info, status):
        if _AUDIO_AVAILABLE:
            rms = np.sqrt(np.mean(indata**2))
            self._current_level = float(rms)

    def _toggle_test(self):
        if self.stream is None:
            self._start()
        else:
            self._stop()

    def _start(self, device_id=None):
        if not _AUDIO_AVAILABLE:
            return
        try:
            self.stream = sd.InputStream(
                device=device_id,
                samplerate=16000,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self.stream.start()
            self.timer.start()
            self.btn_test.setText("Stop Test")
            self.lbl_status.setText("Listening… Speak into your microphone")
        except Exception as e:
            self.lbl_status.setText(f"Microphone error: {e}")

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
            self.level_meter.set_level(0.0)

    def _update_meter(self):
        # Normalize into 0..1 range
        val = min(1.0, self._current_level * 10.0)
        self.level_meter.set_level(val)

    def cleanup(self):
        self._stop()


class SettingsDialog(QDialog):
    """Material 3 Monochrome Preferences Dialog for Dictate."""

    def __init__(
        self,
        current_settings: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
        theme_mode: str = "dark",
    ):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Dictate Settings")
        self.resize(760, 620)
        self.setObjectName("root")

        data = current_settings or {}
        theme_pref = data.get("theme", theme_mode)
        self.dark = (theme_pref == "dark")
        self._tokens = Tokens.dark() if self.dark else Tokens.light()
        self.setStyleSheet(build_qss(self._tokens))

        self._drag_pos: Optional[QPoint] = None
        self._raw_data = data

        self._provider_data = {
            "openrouter": {
                "key": data.get("ai_polish_api_key_openrouter") or (data.get("ai_polish_api_key", "") if data.get("ai_polish_provider") == "openrouter" else ""),
                "url": data.get("ai_polish_base_url_openrouter", "https://openrouter.ai/api/v1"),
                "model": data.get("ai_polish_model_openrouter", "minimax/minimax-m3:free"),
                "placeholder": "API Key (sk-or-v1-...)",
            },
            "nvidia": {
                "key": data.get("ai_polish_api_key_nvidia") or (data.get("ai_polish_api_key", "") if data.get("ai_polish_provider") == "nvidia" else ""),
                "url": data.get("ai_polish_base_url_nvidia", "https://integrate.api.nvidia.com/v1"),
                "model": data.get("ai_polish_model_nvidia", "nvidia/nemotron-3-nano-30b-a3b"),
                "placeholder": "API Key (nvapi-...)",
            },
        }

        self._build_ui(data)

    def _build_ui(self, data: dict):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(28, 0, 28, 0)
        self._tab_bar = SegmentedTabBar(TABS)
        self._tab_bar.currentChanged.connect(lambda i: self._stack.setCurrentIndex(i))
        tab_row.addWidget(self._tab_bar)
        tab_row.addStretch()

        wrapper = QVBoxLayout()
        wrapper.setContentsMargins(0, 16, 0, 0)
        wrapper.addLayout(tab_row)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._scrollable(self._build_tab_general(data)))
        self._stack.addWidget(self._scrollable(self._build_tab_dictation(data)))
        self._stack.addWidget(self._scrollable(self._build_tab_audio(data)))
        self._stack.addWidget(self._scrollable(self._build_tab_advanced(data)))
        wrapper.addWidget(self._stack, 1)

        wrapper.addWidget(self._build_actions())

        container = QWidget()
        container.setLayout(wrapper)
        root.addWidget(container, 1)

    def _scrollable(self, inner: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setWidget(inner)
        return area

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(72)
        layout = QVBoxLayout(header)
        layout.setContentsMargins(28, 14, 28, 10)
        layout.setSpacing(2)
        layout.addWidget(make_label("Settings", "headline"))
        layout.addWidget(make_label(
            "Configure voice typing, offline models, audio devices, and privacy.",
            "body",
        ))
        return header

    def _build_actions(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(28, 14, 28, 20)
        layout.addStretch()
        self.btn_cancel = make_button("Cancel", "secondary")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_save = make_button("Save Changes", "primary")
        self.btn_save.clicked.connect(self._on_save)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.btn_save)
        return bar

    # ------------------------------------------------------------------
    # Tab 1: General
    # ------------------------------------------------------------------

    def _build_tab_general(self, data: dict) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 8, 28, 8)
        layout.setSpacing(20)

        layout.addWidget(_section_header("System Integration"))
        card1 = make_card(t)
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(20, 16, 20, 16)
        c1.setSpacing(12)
        self.autostart_cb = QCheckBox("Launch Dictate automatically at Windows startup")
        self.autostart_cb.setChecked(bool(data.get("autostart", False)))
        self.restore_cb = QCheckBox("Restore previous clipboard content after typing text")
        self.restore_cb.setChecked(bool(data.get("restore_clipboard", True)))
        c1.addWidget(self.autostart_cb)
        c1.addWidget(self.restore_cb)
        layout.addWidget(card1)

        layout.addWidget(_section_header("Appearance & Accessibility"))
        card2 = make_card(t)
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(20, 16, 20, 16)
        self.theme_mode = QComboBox()
        self.theme_mode.addItem("Dark Mode (Recommended)", "dark")
        self.theme_mode.addItem("Light Mode", "light")
        cur_theme = data.get("theme", "dark")
        self.theme_mode.setCurrentIndex(0 if cur_theme == "dark" else 1)
        self.theme_mode.currentIndexChanged.connect(self._on_theme_changed)
        c2.addLayout(_row("Theme", "", self.theme_mode))
        layout.addWidget(card2)

        layout.addStretch()
        return page

    def _on_theme_changed(self, _index: int):
        mode = self.theme_mode.currentData()
        self.dark = (mode == "dark")
        self._tokens = Tokens.dark() if self.dark else Tokens.light()
        self.setStyleSheet(build_qss(self._tokens))

    # ------------------------------------------------------------------
    # Tab 2: Dictation
    # ------------------------------------------------------------------

    def _build_tab_dictation(self, data: dict) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 8, 28, 8)
        layout.setSpacing(20)

        layout.addWidget(_section_header("Activation & Shortcut"))
        card1 = make_card(t)
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(20, 16, 20, 16)
        c1.setSpacing(14)

        self.mode = QComboBox()
        self.mode.addItem("Hold to Talk (Push-to-Talk)", "ptt")
        self.mode.addItem("Press to Start / Stop (Toggle)", "toggle")
        idx = self.mode.findData(data.get("mode", "ptt"))
        if idx >= 0:
            self.mode.setCurrentIndex(idx)
        c1.addLayout(_row("Trigger Mode", "", self.mode))
        c1.addWidget(make_hairline(t))

        self.key_btn = KeyCaptureButton(data.get("trigger_key", data.get("shortcut", "ctrl+shift+p")))
        c1.addLayout(_row("Global Shortcut", "Works in any application", self.key_btn))
        layout.addWidget(card1)

        layout.addWidget(_section_header("Listening & Stopping Control"))
        card2 = make_card(t)
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(20, 16, 20, 16)
        c2.setSpacing(14)

        self.stop_mode = QComboBox()
        self.stop_mode.addItem("Automatically stop on silence (Auto-Stop)", True)
        self.stop_mode.addItem("Manual stop (Click floating pill, tray icon, or shortcut)", False)
        is_auto_stop = bool(data.get("auto_stop", True))
        self.stop_mode.setCurrentIndex(0 if is_auto_stop else 1)
        self.stop_mode.currentIndexChanged.connect(self._on_stop_mode_changed)
        c2.addLayout(_row("Stop Mode", "", self.stop_mode))
        c2.addWidget(make_hairline(t))

        self.preview_cb = QCheckBox("Show live transcript preview while speaking")
        self.preview_cb.setChecked(bool(data.get("show_interim_preview", True)))
        self.voice_commands_cb = QCheckBox("Enable Voice Commands (e.g. 'new line', 'comma', 'period')")
        self.voice_commands_cb.setChecked(bool(data.get("voice_commands", True)))
        c2.addWidget(self.preview_cb)
        c2.addWidget(self.voice_commands_cb)
        c2.addWidget(make_hairline(t))

        self.vad_silence = QDoubleSpinBox()
        self.vad_silence.setRange(0.3, 5.0)
        self.vad_silence.setSingleStep(0.1)
        self.vad_silence.setSuffix(" s")
        self.vad_silence.setValue(float(data.get("vad_silence_seconds", data.get("silence_threshold", 1.4))))

        self._silence_container = QWidget()
        sw_layout = QVBoxLayout(self._silence_container)
        sw_layout.setContentsMargins(0, 0, 0, 0)
        sw_layout.setSpacing(6)
        sw_layout.addLayout(_row("Silence Threshold", "", self.vad_silence))
        sw_layout.addWidget(make_label(
            "Dictate automatically grants extra thinking time when you pause mid-sentence.",
            "body_sm",
        ))
        c2.addWidget(self._silence_container)

        self._manual_notice = make_card(t)
        mn_layout = QVBoxLayout(self._manual_notice)
        mn_layout.setContentsMargins(14, 10, 14, 10)
        mn_layout.addWidget(make_label(
            "Manual mode keeps recording continuously until you stop it yourself — "
            "useful for long-form dictation where pauses shouldn't cut you off.",
            "body_sm",
        ))
        c2.addWidget(self._manual_notice)

        layout.addWidget(card2)
        layout.addStretch()

        self._on_stop_mode_changed(0)
        return page

    def _on_stop_mode_changed(self, _index: int):
        is_auto = bool(self.stop_mode.currentData())
        self._silence_container.setVisible(is_auto)
        self._manual_notice.setVisible(not is_auto)

    # ------------------------------------------------------------------
    # Tab 3: Audio
    # ------------------------------------------------------------------

    def _build_tab_audio(self, data: dict) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 8, 28, 8)
        layout.setSpacing(20)

        layout.addWidget(_section_header("Microphone Input"))
        card1 = make_card(t)
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(20, 16, 20, 16)

        self.mic_device = QComboBox()
        self.mic_device.addItem("System Default Microphone", None)
        if _AUDIO_AVAILABLE:
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
        c1.addLayout(_row("Input Device", "", self.mic_device))
        layout.addWidget(card1)

        layout.addWidget(_section_header("Microphone Test & Diagnostics"))
        card2 = make_card(t)
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(20, 16, 20, 16)
        self.mic_tester = MicTestWidget(t)
        c2.addWidget(self.mic_tester)
        layout.addWidget(card2)

        layout.addStretch()
        return page

    # ------------------------------------------------------------------
    # Tab 4: Advanced
    # ------------------------------------------------------------------

    def _build_tab_advanced(self, data: dict) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 8, 28, 8)
        layout.setSpacing(20)

        layout.addWidget(_section_header("Speech Recognition Engine (On-Device)"))
        card1 = make_card(t)
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(20, 16, 20, 16)
        c1.setSpacing(14)

        self.model = QComboBox()
        for key, label in FINAL_MODELS:
            self.model.addItem(label, key)
        curr_m = data.get("model", data.get("final_model", "parakeet-tdt-0.6b-v3"))
        idx = self.model.findData(curr_m)
        if idx >= 0:
            self.model.setCurrentIndex(idx)
        c1.addLayout(_row("Final Speech Model", "", self.model))
        c1.addWidget(StatusPill("Cached locally", tone="success"))
        c1.addWidget(make_hairline(t))

        self.streaming_model = QComboBox()
        for key, label in PREVIEW_MODELS:
            self.streaming_model.addItem(label, key)
        curr_sm = data.get("streaming_model", data.get("preview_model", "nemo-fast-conformer-80ms"))
        idx = self.streaming_model.findData(curr_sm)
        if idx >= 0:
            self.streaming_model.setCurrentIndex(idx)
        c1.addLayout(_row("Real-Time Preview Model", "", self.streaming_model))
        c1.addWidget(make_hairline(t))

        self.device = QComboBox()
        for key, label in HW_ACCEL_OPTIONS:
            self.device.addItem(label, key)
        curr_dev = data.get("device", data.get("hw_accel", "auto"))
        idx = self.device.findData(curr_dev)
        if idx >= 0:
            self.device.setCurrentIndex(idx)
        c1.addLayout(_row("Hardware Acceleration", "", self.device))
        layout.addWidget(card1)

        layout.addWidget(_section_header("Custom Vocabulary & Phrase Boosting"))
        card2 = make_card(t)
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(20, 16, 20, 16)
        c2.setSpacing(14)

        hotwords_row = QHBoxLayout()
        self.hotwords_file = QLineEdit(data.get("hotwords_file", data.get("hotwords_path", "hotwords.txt")))
        browse = make_button("Browse…", "secondary")
        browse.clicked.connect(self._browse_hotwords)
        hotwords_row.addWidget(self.hotwords_file, 1)
        hotwords_row.addWidget(browse)
        c2.addWidget(make_label("Hotwords File", "body"))
        c2.addLayout(hotwords_row)
        c2.addWidget(make_hairline(t))

        self.hotwords_score = QDoubleSpinBox()
        self.hotwords_score.setRange(0.5, 10.0)
        self.hotwords_score.setSingleStep(0.5)
        self.hotwords_score.setValue(float(data.get("hotwords_score", data.get("boost_score", 2.0))))
        c2.addLayout(_row("Acoustic Boost Score", "", self.hotwords_score))
        c2.addWidget(make_hairline(t))

        self.initial_prompt = QLineEdit(data.get("initial_prompt", data.get("extra_keywords", "")))
        self.initial_prompt.setPlaceholderText("Additional custom technical terms…")
        c2.addWidget(make_label("Extra Keywords", "body"))
        c2.addWidget(self.initial_prompt)
        layout.addWidget(card2)

        layout.addWidget(_section_header("Optional Cloud AI Polish (Opt-in)"))
        card3 = make_card(t)
        c3 = QVBoxLayout(card3)
        c3.setContentsMargins(20, 16, 20, 16)
        c3.setSpacing(14)

        c3.addWidget(make_label(
            "Privacy Notice: Audio is transcribed 100% locally on your device. "
            "When enabled, only the final transcribed text is sent to the chosen "
            "cloud AI provider to clean filler words and grammar.",
            "body_sm",
        ))
        c3.addWidget(make_hairline(t))

        self.ai_enable_cb = ToggleSwitch(t, checked=bool(data.get("ai_polish", data.get("cloud_polish_enabled", False))))
        c3.addLayout(_row("Enable Cloud AI Polish", "", self.ai_enable_cb))

        self._cloud_config = QWidget()
        cc_layout = QVBoxLayout(self._cloud_config)
        cc_layout.setContentsMargins(0, 8, 0, 0)
        cc_layout.setSpacing(12)
        cc_layout.addWidget(make_hairline(t))

        self.ai_provider = QComboBox()
        for key, label in CLOUD_PROVIDERS:
            self.ai_provider.addItem(label, key)
        cur_prov = data.get("ai_polish_provider", data.get("cloud_provider", "openrouter"))
        idx = self.ai_provider.findData(cur_prov)
        if idx >= 0:
            self.ai_provider.setCurrentIndex(idx)
        self.ai_provider.currentIndexChanged.connect(self._on_provider_changed)
        cc_layout.addLayout(_row("Provider", "", self.ai_provider))

        self.ai_polish_api_key = QLineEdit()
        self.ai_polish_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        cc_layout.addWidget(make_label("API Key", "body"))
        cc_layout.addWidget(self.ai_polish_api_key)

        self.ai_polish_base_url = QLineEdit()
        cc_layout.addWidget(make_label("Base URL", "body"))
        cc_layout.addWidget(self.ai_polish_base_url)

        self.ai_polish_model = QComboBox()
        self.ai_polish_model.setEditable(True)
        cc_layout.addWidget(make_label("Model", "body"))
        cc_layout.addWidget(self.ai_polish_model)

        self.async_polish_cb = QCheckBox("Instant paste first (Fast ~150ms injection, refine in background)")
        self.async_polish_cb.setChecked(bool(data.get("async_polish", False)))
        cc_layout.addWidget(self.async_polish_cb)

        c3.addWidget(self._cloud_config)
        self.ai_enable_cb.toggled.connect(self._on_cloud_toggled)

        layout.addWidget(card3)
        layout.addStretch()

        self._update_provider_ui(cur_prov)
        self._on_cloud_toggled(self.ai_enable_cb.isChecked())
        return page

    def _browse_hotwords(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select hotwords file", "", "Text Files (*.txt)")
        if path:
            self.hotwords_file.setText(path)

    def _update_provider_ui(self, prov: str):
        info = self._provider_data.get(prov, self._provider_data["openrouter"])
        self.ai_polish_api_key.setText(info["key"])
        self.ai_polish_api_key.setPlaceholderText(info["placeholder"])
        self.ai_polish_base_url.setText(info["url"])
        self.ai_polish_model.clear()
        for label, val in CLOUD_MODELS_BY_PROVIDER.get(prov, []):
            self.ai_polish_model.addItem(label, val)
        cur_m = info["model"]
        m_idx = self.ai_polish_model.findData(cur_m)
        if m_idx >= 0:
            self.ai_polish_model.setCurrentIndex(m_idx)
        else:
            self.ai_polish_model.setCurrentText(cur_m)

    def _on_provider_changed(self):
        prov = self.ai_provider.currentData()
        self._update_provider_ui(prov)

    def _on_cloud_toggled(self, checked: bool):
        self._cloud_config.setVisible(checked)

    # ------------------------------------------------------------------
    # Value reading & persistence
    # ------------------------------------------------------------------

    def values(self) -> Dict[str, Any]:
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
            "trigger_key": self.key_btn.value(),
            "model": self.model.currentData() or self.model.currentText(),
            "device": self.device.currentData(),
            "hotwords_file": self.hotwords_file.text().strip(),
            "hotwords_score": round(self.hotwords_score.value(), 1),
            "initial_prompt": self.initial_prompt.text().strip(),
            "input_device": self.mic_device.currentData(),
            "restore_clipboard": self.restore_cb.isChecked(),
            "autostart": self.autostart_cb.isChecked(),
            "auto_stop": bool(self.stop_mode.currentData()),
            "vad_silence_seconds": round(self.vad_silence.value(), 1),
            "voice_commands": self.voice_commands_cb.isChecked(),
            "show_interim_preview": self.preview_cb.isChecked(),
            "streaming_model": self.streaming_model.currentData() or self.streaming_model.currentText(),
            "ai_polish": self.ai_enable_cb.isChecked(),
            "async_polish": self.async_polish_cb.isChecked(),
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

    def _cleanup_audio(self):
        if hasattr(self, "mic_tester") and self.mic_tester:
            try:
                self.mic_tester.cleanup()
            except Exception:
                pass

    def _on_save(self):
        self._cleanup_audio()
        self.accept()

    def _on_cancel(self):
        self._cleanup_audio()
        self.reject()

    def closeEvent(self, event):
        self._cleanup_audio()
        super().closeEvent(event)

    def reject(self):
        self._cleanup_audio()
        super().reject()

    def accept(self):
        self._cleanup_audio()
        super().accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 72:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


def main():
    app = QApplication(sys.argv)
    dlg = SettingsDialog(theme_mode="dark")
    if dlg.exec():
        print("Saved:", dlg.values())
    else:
        print("Cancelled")


if __name__ == "__main__":
    main()
