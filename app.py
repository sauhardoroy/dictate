"""DictateApp: orchestrates mic, ASR engine, injection, pill and tray.

Threading model:
- `keyboard` callbacks and worker threads only emit Qt signals on AppSignals;
  Qt queues them to the GUI thread, so all widget state changes are safe.
- Engine loading and transcription run on daemon threads so quitting is
  never blocked by a long download or inference.
"""
import sys
import threading
import os


import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication, QDialog

from asr.faster_whisper_engine import FasterWhisperEngine, model_loading_message
from asr.nemotron_engine import NemotronEngine
from asr.streaming_sherpa import SherpaStreamingEngine
from audio.capture import MicUnavailableError, Recorder, trim_silence
from config.settings import Settings, set_autostart
from history.manager import HistoryManager
from hotkey.manager import HotkeyManager
from injection.sanitizer import sanitize
from injection.typer import execute_action, paste_text
from log import get_logger
from punctuation.post_processor import HALLUCINATION_BLOCKLIST, polish
from punctuation.semantic_vad import get_adaptive_silence_duration
from punctuation.voice_commands import ACTION_DISPLAY_NAMES, get_action_command
from ui.pill import Pill
from ui.tray import TrayIcon

log = get_logger(__name__)


class AppSignals(QObject):
    trigger = pyqtSignal()        # hotkey press / pill click / tray click
    release = pyqtSignal()        # push-to-talk key release
    esc_cancel = pyqtSignal()
    engine_loaded = pyqtSignal(bool, str)
    engine_result = pyqtSignal(object)
    interim_text = pyqtSignal(str)  # Real-time partial transcript preview


class DictateApp(QObject):
    def __init__(self, load_model: bool = True):
        super().__init__()
        self.settings = Settings()
        self.state = "loading"
        self.last_text = ""
        self.recorder = None
        self._esc_hook = None
        self.target_hwnd = None
        self.target_app_name = ""
        self.target_window_title = ""
        self._history_dialog = None
        self._last_duration = 0.0
        self._engine_lock = threading.Lock()

        self.history = HistoryManager(
            max_entries=self.settings.get("max_history_entries", 100),
            enabled=self.settings.get("enable_history", True),
        )

        self.sig = AppSignals()
        self.sig.trigger.connect(self.on_trigger)
        self.sig.release.connect(self.on_release)
        self.sig.esc_cancel.connect(self.on_esc)
        self.sig.engine_loaded.connect(self.on_engine_loaded)
        self.sig.engine_result.connect(self.on_result)
        self.sig.interim_text.connect(self._on_interim_text)

        self.engine = self._make_engine()

        self.pill = Pill(x=self.settings.get("pill_x"), y=self.settings.get("pill_y"))
        self.pill.toggle_requested.connect(self.sig.trigger)
        self.pill.settings_requested.connect(self.open_settings)
        self.pill.history_requested.connect(self.open_history)
        self.pill.copy_last_requested.connect(self.copy_last_transcript)
        self.pill.quit_requested.connect(self.quit)
        self.pill.position_changed.connect(self._on_pill_moved)

        self.streaming_engine = SherpaStreamingEngine()
        model_name = self.settings.get("streaming_model", "zipformer-70M")
        threading.Thread(target=lambda: self.streaming_engine.load(model_name), daemon=True).start()

        self._interim_timer = QTimer(self)
        self._interim_timer.setInterval(200)
        self._interim_timer.timeout.connect(self._on_interim_tick)

        self.tray = TrayIcon()
        self.tray.toggle_requested.connect(self.sig.trigger)
        self.tray.settings_requested.connect(self.open_settings)
        self.tray.history_requested.connect(self.open_history)
        self.tray.copy_last_requested.connect(self.copy_last_transcript)
        self.tray.quit_requested.connect(self.quit)

        self.hotkeys = HotkeyManager(
            key=self.settings["trigger_key"],
            mode=self.settings["mode"],
            on_press=self.sig.trigger.emit,
            on_release=self.sig.release.emit,
        )
        try:
            self.hotkeys.register()
            log.info("hotkey registered: %s (%s)", self.settings["trigger_key"], self.settings["mode"])
        except RuntimeError as exc:
            self._set_state("error", str(exc))
            log.exception("hotkey registration failed: %s", exc)

        if load_model:
            model_name = self.settings.get("model", "parakeet-tdt-0.6b-v3")
            if model_name == "parakeet-tdt-0.6b-v3" or self.settings.get("engine") == "parakeet":
                message = "Loading NVIDIA Parakeet TDT engine…"
            elif model_name == "sense-voice-small":
                message = "Loading Alibaba SenseVoice engine…"
            elif self.settings["engine"] == "nemotron":
                message = "Loading Nemotron engine…"
            else:
                message = f"Loading {model_name} model…"
            self._set_state("loading", message)
            threading.Thread(target=self._load_engine, daemon=True).start()
        else:
            self._set_state("idle", "Smoke mode — model not loaded")

        if self.settings["show_pill"]:
            self.pill.show()
        self.tray.show()

        # Show first-run onboarding while the model loads in the background
        if not self.settings["onboarding_completed"]:
            self._show_onboarding()

    # ---- engine -----------------------------------------------------------

    def _make_engine(self):
        if self.settings["engine"] == "nemotron":
            return NemotronEngine(binary=self.settings["nemotron_binary"])
        model_name = self.settings.get("model", "parakeet-tdt-0.6b-v3")
        if model_name == "parakeet-tdt-0.6b-v3" or self.settings.get("engine") == "parakeet":
            from asr.parakeet_engine import ParakeetTDTEngine
            return ParakeetTDTEngine(
                num_threads=self.settings.get("cpu_threads", 4),
                hotwords_file=self.settings.get("hotwords_file", "hotwords.txt"),
                hotwords_score=self.settings.get("hotwords_score", 2.0),
                device=self.settings.get("device", "auto"),
                language=self.settings.get("language", "en"),
            )
        if model_name == "sense-voice-small" or model_name.startswith("moonshine-"):
            from asr.sherpa_offline_engine import SherpaOfflineEngine
            return SherpaOfflineEngine(
                model_id=model_name,
                num_threads=self.settings.get("cpu_threads", 4),
            )
        return FasterWhisperEngine(
            model_size=model_name,
            device=self.settings["device"],
            compute_type=self.settings["compute_type"],
            language=self.settings["language"],
            vad_filter=self.settings["vad_filter"],
            initial_prompt=self.settings.get("initial_prompt", ""),
            cpu_threads=self.settings.get("cpu_threads", 0),
        )

    def _load_engine(self):
        try:
            log.info("loading engine %s", self.engine.name)
            self.engine.load()
            self.sig.engine_loaded.emit(True, self.engine.name)
            log.info("engine loaded: %s", self.engine.name)
        except Exception as exc:  # noqa: BLE001
            log.exception("engine load failed")
            self.sig.engine_loaded.emit(False, f"{type(exc).__name__}: {exc}")

    @pyqtSlot(bool, str)
    def on_engine_loaded(self, ok: bool, msg: str):
        if ok:
            key = self.settings["trigger_key"].upper()
            self._set_state("idle", f"Ready — hold {key} and speak")
        else:
            self._set_state("error", f"Model failed: {msg}")
            if self.tray.supportsMessages():
                self.tray.showMessage("Dictate", f"Model failed to load: {msg}")
            QTimer.singleShot(1200, self._offer_engine_retry)

    def _offer_engine_retry(self):
        """Return to an actionable state and let the user retry from the pill."""
        if self.state != "error" or self.engine.is_loaded():
            return
        self._set_state("idle", "Model unavailable — click to retry")

    def _retry_engine_load(self):
        self._set_state("loading", "Retrying model load…")
        threading.Thread(target=self._load_engine, daemon=True).start()

    def _transcribe(self, audio):
        try:
            with self._engine_lock:
                result = self.engine.transcribe(audio)
            raw_text = result.get("text", "")
            result["raw_text"] = raw_text
            log.debug("raw transcript (%d samples): %r", len(audio), raw_text)

            # Post-process (potentially slow if using AI polish)
            text = polish(raw_text, settings=self.settings.data)
            result["text"] = text
            result["duration_s"] = len(audio) / 16000.0
            log.info("transcribed %.1fs -> %d chars", len(audio) / 16000, len(text))

            self.sig.engine_result.emit(result)
        except Exception as exc:  # noqa: BLE001
            log.exception("transcription failed")
            self.sig.engine_result.emit(exc)

    # ---- recording lifecycle ----------------------------------------------

    def _capture_target_window(self):
        try:
            if sys.platform == "win32":
                import ctypes
                cur_fg = ctypes.windll.user32.GetForegroundWindow()
                pill_hwnd = int(self.pill.winId()) if hasattr(self, "pill") and self.pill else 0
                if cur_fg and cur_fg != pill_hwnd:
                    self.target_hwnd = cur_fg
                    from injection.sanitizer import _get_process_name
                    self.target_app_name = _get_process_name(cur_fg)
                    buf = (ctypes.c_wchar * 260)()
                    if ctypes.windll.user32.GetWindowTextW(cur_fg, buf, 260):
                        self.target_window_title = buf.value
                    else:
                        self.target_window_title = ""
            elif sys.platform == "darwin":
                # On macOS, window focus is managed by the OS
                self.target_hwnd = 0
        except Exception:
            pass

    @pyqtSlot()
    def on_trigger(self):
        if self.state == "recording":
            self._finish_recording(cancel=False)
        elif self.state == "idle":
            if not self.engine.is_loaded():
                self._retry_engine_load()
                return
            self._capture_target_window()
            self._start_recording()
        elif self.state in ("loading", "transcribing", "injecting"):
            if self.tray.supportsMessages():
                self.tray.showMessage("Dictate", f"Busy: {self.state}")

    @pyqtSlot()
    def on_release(self):
        if self.state == "recording":
            self._finish_recording(cancel=False)

    @pyqtSlot()
    def on_esc(self):
        if self.state == "recording":
            self._finish_recording(cancel=True)

    def _play_sound(self, name: str):
        try:
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "assets", "sounds", f"{name}.wav")
            if os.path.exists(path):
                if sys.platform == "win32":
                    import winsound
                    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _on_audio_chunk(self, chunk: np.ndarray):
        """Streaming real-time acoustic chunk ingestion (<5ms latency)."""
        if not self.settings.get("show_interim_preview", True) or self.state not in ("recording", "preview"):
            return
        if not self.streaming_engine.is_available():
            return

        text = self.streaming_engine.accept_chunk(chunk)
        if text:
            self.sig.interim_text.emit(text)
            # Update adaptive silence duration live from streaming text
            if self.recorder and self.state in ("recording", "preview"):
                base_sec = float(self.settings.get("vad_silence_seconds", 1.4))
                adaptive_sec = get_adaptive_silence_duration(text, base_silence_seconds=base_sec)
                self.recorder.update_silence_duration(adaptive_sec)

    def _on_interim_tick(self):
        """Fallback interim evaluator if streaming engine is still downloading/initializing."""
        if not self.settings.get("show_interim_preview", True):
            return
        if self.streaming_engine.is_available():
            return  # Streaming engine handles live preview with zero polling lag
        if not self.engine.is_loaded() or self.state not in ("recording", "preview") or not self.recorder:
            return

        audio_snapshot = self.recorder.snapshot()
        # Start showing preview as soon as ~0.5s of speech (8,000 samples @ 16kHz) is captured
        if len(audio_snapshot) < 8000:
            return

        # For low-latency streaming, transcribe the active tail window (last 2.5s / 40,000 samples)
        # to ensure CPU inference completes in ~30-40ms per tick.
        eval_audio = audio_snapshot if len(audio_snapshot) <= 40000 else audio_snapshot[-40000:]

        def _worker():
            if not self._engine_lock.acquire(blocking=False):
                return
            try:
                # Use fast=True for instant greedy decode without timestamp alignment
                res = self.engine.transcribe(eval_audio, fast=True) if hasattr(self.engine, "transcribe") else {}
                if isinstance(res, dict):
                    raw_text = res.get("text", "").strip()
                    if raw_text and raw_text.lower() not in HALLUCINATION_BLOCKLIST:
                        self.sig.interim_text.emit(raw_text)

                        # Update adaptive silence duration from the latest text in the same pass
                        if self.recorder and self.state in ("recording", "preview"):
                            base_sec = float(self.settings.get("vad_silence_seconds", 1.4))
                            adaptive_sec = get_adaptive_silence_duration(raw_text, base_silence_seconds=base_sec)
                            self.recorder.update_silence_duration(adaptive_sec)
            except Exception as exc:
                log.debug("interim preview transcription error: %s", exc)
            finally:
                self._engine_lock.release()

        threading.Thread(target=_worker, daemon=True).start()

    @pyqtSlot(str)
    def _on_interim_text(self, text: str):
        if self.state in ("recording", "preview") and self.settings.get("show_interim_preview", True):
            self.pill.update_preview(text)

    def _on_silence_eval(self, audio_snapshot):
        """Asynchronously evaluates semantic thought completion on partial audio to dynamically adapt silence duration."""
        # If the fast interim timer is already running, it updates adaptive silence on every tick.
        if self.settings.get("show_interim_preview", True) and self._interim_timer.isActive():
            return

        if not self.engine.is_loaded() or len(audio_snapshot) < 8000:
            return

        def _worker():
            if not self._engine_lock.acquire(blocking=False):
                return
            try:
                res = self.engine.transcribe(audio_snapshot, fast=True)
                if isinstance(res, dict):
                    text = res.get("text", "")
                    base_sec = float(self.settings.get("vad_silence_seconds", 1.4))
                    adaptive_sec = get_adaptive_silence_duration(text, base_silence_seconds=base_sec)
                    if self.recorder and self.state in ("recording", "preview"):
                        self.recorder.update_silence_duration(adaptive_sec)
            except Exception as exc:
                log.debug("Semantic silence evaluation error: %s", exc)
            finally:
                self._engine_lock.release()

        threading.Thread(target=_worker, daemon=True).start()

    def _start_recording(self):
        if not self.engine.is_loaded():
            self.pill.set_state("loading", "Model still loading\u2026")
            return
        if not self.target_hwnd:
            self._capture_target_window()
        try:
            self.recorder = Recorder(
                device=self.settings["input_device"],
                on_level=self.pill.set_level,
                on_auto_stop=self.sig.release.emit,
                on_silence_eval=self._on_silence_eval,
                on_chunk=self._on_audio_chunk,
                use_vad=self.settings.get("auto_stop", True),
                vad_silence_seconds=float(self.settings.get("vad_silence_seconds", 1.4)),
            )
            self.recorder.start()
            log.info("recording started (device=%s, vad=%s)", self.settings["input_device"], self.settings.get("auto_stop", True))
        except MicUnavailableError as exc:
            log.error("mic unavailable: %s", exc)
            self._set_state("error", f"Mic error: {exc}")
            QTimer.singleShot(2500, lambda: self._idle())
            return
        except Exception as exc:  # noqa: BLE001
            log.exception("recording failed to start")
            self._set_state("error", f"Recording error: {exc}")
            QTimer.singleShot(2500, lambda: self._idle())
            return

        self._esc_hook = HotkeyManager("esc", "cancel", self.sig.esc_cancel.emit)
        self._esc_hook.register()
        auto_stop = bool(self.settings.get("auto_stop", True))
        rec_msg = "Listening… (Auto-stops on silence)" if auto_stop else "Listening… (Click pill or tray to stop)"
        self.pill.clear_preview()
        self._set_state("recording", rec_msg)
        self._play_sound("start")
        if self.settings.get("show_interim_preview", True):
            if self.streaming_engine.is_available():
                self.streaming_engine.start_stream()
            else:
                self._interim_timer.start()

    def _finish_recording(self, cancel: bool):
        self._interim_timer.stop()
        if self.streaming_engine.is_available():
            self.streaming_engine.stop_stream()
        self.pill.clear_preview()
        self._unhook_esc()
        audio = self.recorder.stop()
        duration = self.recorder.duration()
        log.debug("recording finished cancel=%s duration=%.2fs", cancel, duration)
        if cancel:
            self._idle("Cancelled")
            return
        if duration < 0.2:
            log.info("ignoring very short recording (%.2fs)", duration)
            self._idle("No speech detected")
            return
        trimmed_audio = trim_silence(audio)
        if len(trimmed_audio) != len(audio):
            log.info("trimmed recording from %.2fs to %.2fs", len(audio) / 16000, len(trimmed_audio) / 16000)
        self._play_sound("stop")
        self._set_state("transcribing", "Transcribing…")
        threading.Thread(target=self._transcribe, args=(trimmed_audio,), daemon=True).start()

    def _unhook_esc(self):
        if self._esc_hook is not None:
            self._esc_hook.unregister()
            self._esc_hook = None

    # ---- result -----------------------------------------------------------

    @pyqtSlot(object)
    def on_result(self, result):
        if isinstance(result, Exception):
            log.error("transcription failed in worker: %s", result)
            self._play_sound("error")
            self._set_state("error", f"Transcription failed: {result}")
            QTimer.singleShot(2500, lambda: self._idle())
            return
        text = result.get("text", "")
        if not text or text.lower() in HALLUCINATION_BLOCKLIST:
            log.info("nothing recognized (blocked hallucination)")
            self._idle("Nothing recognized")
            return

        # Check for action voice command (e.g. "delete that", "select all", "press enter")
        if self.settings.get("voice_commands", True):
            action = get_action_command(text)
            if action:
                display = ACTION_DISPLAY_NAMES.get(action, action.title())
                self.last_text = display
                self._set_state("injecting", display)
                ok = execute_action(action, target_hwnd=self.target_hwnd or 0)
                if ok:
                    self.history.add_entry(
                        text=display,
                        raw_text=text,
                        duration_s=result.get("duration_s", 0.0),
                        target_app=self.target_app_name,
                        window_title=self.target_window_title,
                        is_action=True,
                    )
                    self._play_sound("success")
                    log.info("executed action command: %s (%s)", action, display)
                    QTimer.singleShot(800, lambda: self._idle(display))
                else:
                    self._play_sound("error")
                    self._set_state("error", f"Action failed: {display}")
                    QTimer.singleShot(2500, lambda: self._idle())
                return

        # Sanitize before injection (strips dangerous patterns for terminals)
        sanitized, san_warnings = sanitize(text, target_hwnd=self.target_hwnd or 0)
        if san_warnings:
            log.warning("sanitizer modified text: %s", "; ".join(san_warnings))
        if not sanitized:
            log.info("sanitizer removed all text")
            self._idle("Text blocked by safety filter")
            return
        text = sanitized

        self.last_text = text
        self._set_state("injecting", text)
        self._play_sound("success")
        log.info("injecting text (%d chars) into target", len(text))
        injected = paste_text(
            text,
            restore=self.settings["restore_clipboard"],
            delay_ms=self.settings["injection_delay_ms"],
            target_hwnd=self.target_hwnd,
        )
        if not injected:
            self._play_sound("error")
            self._set_state("error", "Paste failed — click the target text box and try again")
            QTimer.singleShot(2500, lambda: self._idle())
            return

        self.history.add_entry(
            text=text,
            raw_text=result.get("raw_text", text),
            duration_s=result.get("duration_s", 0.0),
            target_app=self.target_app_name,
            window_title=self.target_window_title,
            is_action=False,
        )
        QTimer.singleShot(450, lambda: self._idle())

    # ---- state helpers ----------------------------------------------------

    def _set_state(self, state: str, detail: str = ""):
        self.state = state
        self.pill.set_state(state, detail)
        self.tray.set_status(state, detail)

    def _idle(self, detail: str = ""):
        if detail:
            msg = detail
        elif self.last_text:
            msg = f"Last: {self.last_text[:80]}"
        else:
            msg = "Ready"
        self._set_state("idle", msg)

    def _on_pill_moved(self, x: int, y: int):
        self.settings["pill_x"] = x
        self.settings["pill_y"] = y
        log.debug("saved pill position: (%d, %d)", x, y)

    # ---- onboarding -------------------------------------------------------

    def copy_last_transcript(self):
        """Quick action: copy the most recent transcript text to the clipboard."""
        last_rec = self.history.get_last()
        if last_rec and last_rec.text:
            from injection.typer import copy_to_clipboard
            copy_to_clipboard(last_rec.text)
            self._play_sound("success")
            self._set_state("idle", "Copied to clipboard")
            QTimer.singleShot(1500, lambda: self._idle())
            log.info("copied last transcript to clipboard (%d chars)", len(last_rec.text))
        else:
            self._set_state("idle", "No transcripts in history")
            QTimer.singleShot(1500, lambda: self._idle())

    def open_history(self):
        """Open the Transcript History window."""
        from ui.history_dialog import HistoryDialog

        if self._history_dialog is not None and self._history_dialog.isVisible():
            self._history_dialog.activateWindow()
            self._history_dialog.raise_()
            return
        self._history_dialog = HistoryDialog(
            history_manager=self.history,
            target_hwnd=self.target_hwnd or 0,
        )
        self._history_dialog.show()

    def _show_onboarding(self):
        """Launch the first-run wizard after a short delay so the pill is visible."""
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(300, self._run_onboarding)

    def _run_onboarding(self):
        from ui.onboarding import OnboardingDialog

        dlg = OnboardingDialog(
            trigger_key=self.settings.get("trigger_key", "ctrl+shift+p"),
            model_id=self.settings.get("model", "parakeet-tdt-0.6b-v3"),
        )
        if dlg.exec() == OnboardingDialog.DialogCode.Accepted:
            self.settings["onboarding_completed"] = True
            
            # Save any settings configured in the onboarding dialog
            vals = dlg.values()
            if "trigger_key" in vals:
                self.settings["trigger_key"] = vals["trigger_key"]
                self.hotkeys.key = vals["trigger_key"]
                try:
                    self.hotkeys.register()
                except Exception as exc:
                    log.error("Failed to register hotkey from onboarding: %s", exc)

            log.info("onboarding completed")

    # ---- settings / quit --------------------------------------------------

    def open_settings(self):
        from ui.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self.settings.data)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.values()

            # Detect whether the ASR engine needs a reload
            engine_keys = ("model", "engine", "device", "compute_type", "language", "vad_filter", "cpu_threads", "hotwords_file", "hotwords_score")
            engine_changed = any(vals.get(k) != self.settings.get(k) for k in engine_keys
                                 if k in vals)

            streaming_changed = vals.get("streaming_model") != self.settings.get("streaming_model")
            for k, v in vals.items():
                self.settings[k] = v
            log.info("settings updated: %s", ", ".join(sorted(vals.keys())))

            if hasattr(self, "streaming_engine") and streaming_changed:
                new_s_model = vals.get("streaming_model", "nemo-fast-conformer-80ms")
                threading.Thread(target=lambda: self.streaming_engine.load(new_s_model), daemon=True).start()

            # Custom vocabulary is read per-transcription, not baked into the
            # loaded model, so it can be updated live without a reload.
            if "initial_prompt" in vals and hasattr(self.engine, "initial_prompt"):
                self.engine.initial_prompt = vals["initial_prompt"]
            self.hotkeys.key = vals["trigger_key"]
            self.hotkeys.mode = vals["mode"]
            try:
                self.hotkeys.register()
            except RuntimeError as exc:
                log.error("hotkey re-register failed: %s", exc)
                self.tray.showMessage("Dictate", str(exc))
            try:
                set_autostart(vals["autostart"])
            except Exception as exc:  # noqa: BLE001
                log.exception("autostart update failed")
                if self.tray.supportsMessages():
                    self.tray.showMessage("Dictate", f"Autostart failed: {exc}")

            if engine_changed:
                self._hot_swap_engine()

    def _hot_swap_engine(self):
        """Unload the current engine and load the new one on a background thread."""
        if self.state == "recording":
            self._finish_recording(cancel=True)

        old_name = self.engine.name if self.engine else "none"
        log.info("hot-swapping engine: %s -> %s/%s",
                 old_name, self.settings["engine"], self.settings["model"])

        # Discard old engine (let GC reclaim its memory)
        self.engine = None

        # Build the new engine from updated settings
        self.engine = self._make_engine()

        model_name = self.settings.get("model", "parakeet-tdt-0.6b-v3")
        if model_name == "parakeet-tdt-0.6b-v3" or self.settings.get("engine") == "parakeet":
            message = "Loading NVIDIA Parakeet TDT engine…"
        elif model_name == "sense-voice-small":
            message = "Loading Alibaba SenseVoice engine…"
        elif self.settings["engine"] == "nemotron":
            message = "Loading Nemotron engine…"
        else:
            message = f"Loading {model_name} model…"
        self._set_state("loading", message)
        threading.Thread(target=self._load_engine, daemon=True).start()

    def quit(self):
        log.info("quitting")
        if self.state in ("recording", "preview"):
            self._finish_recording(cancel=True)
        self._unhook_esc()
        self.hotkeys.unregister()
        QApplication.instance().quit()
