"""Transcript History Dialog: Material 3 Monochrome search, stat counters, rich card view, and export."""
from __future__ import annotations

import json
import os

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from history.manager import HistoryManager, TranscriptRecord
from injection.typer import copy_to_clipboard, paste_text
from ui.material_theme import (
    FONT_FAMILY,
    Shape,
    Tokens,
    build_qss,
    get_tokens,
    is_system_dark_mode,
)
from ui.widgets import StatusPill, make_button, make_card, make_label


class TranscriptCardWidget(QFrame):
    """Rich card widget representing a single transcript record in history."""

    deleted = pyqtSignal(str)
    reinject_requested = pyqtSignal(str)

    def __init__(self, record: TranscriptRecord, target_hwnd: int = 0, dark: bool = None, parent=None):
        super().__init__(parent)
        self.record = record
        self.target_hwnd = target_hwnd
        self.dark = is_system_dark_mode() if dark is None else dark
        self.t = get_tokens(self.dark)

        self.setProperty("role", "card")
        self.setStyleSheet(f"""
            TranscriptCardWidget {{
                background-color: {self.t.surface_container_low};
                border: 1px solid {self.t.outline_variant};
                border-radius: {Shape.LG}px;
            }}
            TranscriptCardWidget:hover {{
                border-color: {self.t.outline};
                background-color: {self.t.surface_container};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header row: timestamp, app badge, duration/words, actions
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        time_lbl = QLabel(record.formatted_time())
        time_lbl.setProperty("role", "label")
        time_lbl.setStyleSheet(f"color: {self.t.on_surface_variant}; font-weight: 600;")
        header_row.addWidget(time_lbl)

        if record.target_app:
            app_badge = StatusPill(record.target_app, tone="neutral", dot=False)
            header_row.addWidget(app_badge)

        if record.duration_s > 0 or record.word_count > 0:
            info_text = []
            if record.word_count > 0:
                info_text.append(f"{record.word_count} word{'s' if record.word_count != 1 else ''}")
            if record.duration_s > 0:
                info_text.append(f"{record.duration_s:.1f}s")
            stats_lbl = QLabel(" • ".join(info_text))
            stats_lbl.setProperty("role", "caption")
            stats_lbl.setStyleSheet(f"color: {self.t.on_surface_muted};")
            header_row.addWidget(stats_lbl)

        header_row.addStretch()

        # Action Buttons
        self.btn_copy = make_button("Copy", variant="secondary")
        self.btn_copy.setFixedHeight(28)
        self.btn_copy.clicked.connect(self._copy_text)
        header_row.addWidget(self.btn_copy)

        insert_label = f"Insert in {record.target_app}" if record.target_app else "Insert at Cursor"
        self.btn_paste = make_button(insert_label, variant="secondary")
        self.btn_paste.setFixedHeight(28)
        self.btn_paste.clicked.connect(self._reinject_text)
        header_row.addWidget(self.btn_paste)

        btn_del = make_button("Delete", variant="text")
        btn_del.setFixedHeight(28)
        btn_del.setToolTip("Delete entry")
        btn_del.clicked.connect(lambda: self.deleted.emit(self.record.id))
        header_row.addWidget(btn_del)

        layout.addLayout(header_row)

        # Body: Transcript Text
        text_lbl = QLabel(record.text)
        text_lbl.setProperty("role", "body")
        text_lbl.setStyleSheet(f"color: {self.t.on_surface};")
        text_lbl.setWordWrap(True)
        text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text_lbl)

    def _copy_text(self):
        copy_to_clipboard(self.record.text)
        self.btn_copy.setText("Copied")
        QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self.btn_copy.setText("Copy")

    def _reinject_text(self):
        self.reinject_requested.emit(self.record.text)


class HistoryDialog(QDialog):
    """Full-featured modal window to search, review, copy, and export past dictations."""

    def __init__(self, history_manager: HistoryManager, target_hwnd: int = 0, dark: bool = None, parent=None):
        super().__init__(parent)
        self.history = history_manager
        self.target_hwnd = target_hwnd
        self.dark = is_system_dark_mode() if dark is None else dark
        self.t = get_tokens(self.dark)

        self.setWindowTitle("Dictate — Transcript History")
        self.setMinimumSize(660, 540)
        self.resize(720, 600)
        self.setStyleSheet(build_qss(self.t))

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(14)

        # Header Title & Subtitle
        top_bar = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)
        title = make_label("Transcript History", role="headline")
        header_text.addWidget(title)

        subtitle = make_label("Review, copy, or export your recent voice typing records.", role="body_sm")
        header_text.addWidget(subtitle)
        top_bar.addLayout(header_text)
        top_bar.addStretch()
        root.addLayout(top_bar)

        # Stats Dashboard Strip
        self.stats_container = make_card(self.t)
        self.stats_container.setStyleSheet(f"""
            QFrame[role="card"] {{
                background-color: {self.t.surface_container_low};
                border: 1px solid {self.t.outline_variant};
                border-radius: {Shape.MD}px;
                padding: 6px 14px;
            }}
        """)
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(12, 6, 12, 6)

        self.stat_count_lbl = QLabel()
        self.stat_count_lbl.setProperty("role", "label")
        self.stat_count_lbl.setStyleSheet(f"color: {self.t.on_surface_variant}; font-weight: 600;")
        stats_layout.addWidget(self.stat_count_lbl)
        stats_layout.addStretch()

        self.stat_words_lbl = QLabel()
        self.stat_words_lbl.setProperty("role", "label")
        self.stat_words_lbl.setStyleSheet(f"color: {self.t.on_surface_variant}; font-weight: 600;")
        stats_layout.addWidget(self.stat_words_lbl)
        stats_layout.addStretch()

        self.stat_time_lbl = QLabel()
        self.stat_time_lbl.setProperty("role", "label")
        self.stat_time_lbl.setStyleSheet(f"color: {self.t.on_surface_variant}; font-weight: 600;")
        stats_layout.addWidget(self.stat_time_lbl)

        root.addWidget(self.stats_container)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search transcripts, apps, or keywords…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search)
        root.addWidget(self.search_input)

        # List Widget for Cards
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                margin-bottom: 8px;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        root.addWidget(self.list_widget, 1)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        btn_clear = make_button("Clear All", variant="text")
        btn_clear.clicked.connect(self._clear_all)
        bottom_bar.addWidget(btn_clear)

        bottom_bar.addStretch()

        btn_export = make_button("Export…", variant="secondary")
        btn_export.clicked.connect(self._export_history)
        bottom_bar.addWidget(btn_export)

        btn_close = make_button("Done", variant="primary")
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        root.addLayout(bottom_bar)

        self._refresh_list()

    def _on_search(self, text: str):
        self._refresh_list(query=text)

    def _refresh_list(self, query: str = ""):
        self.list_widget.clear()
        entries = self.history.search(query) if query else self.history.get_all()
        all_entries = self.history.get_all()

        total_words = sum(e.word_count for e in all_entries)
        total_entries = len(all_entries)
        minutes_saved = round((total_words / 40.0) - (total_words / 130.0), 1) if total_words > 0 else 0.0

        self.stat_count_lbl.setText(f"{total_entries} Dictation{'s' if total_entries != 1 else ''}")
        self.stat_words_lbl.setText(f"{total_words:,} Words")
        self.stat_time_lbl.setText(f"~{minutes_saved:.0f}m Saved")

        if not entries:
            empty_item = QListWidgetItem()
            msg = "No transcripts recorded yet." if not query else "No transcripts match your search."
            empty_widget = QLabel(f"{msg}")
            empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_widget.setStyleSheet(f"color: {self.t.on_surface_muted}; font-size: 13px; padding: 40px;")
            empty_item.setSizeHint(empty_widget.sizeHint())
            self.list_widget.addItem(empty_item)
            self.list_widget.setItemWidget(empty_item, empty_widget)
            return

        for record in entries:
            item = QListWidgetItem()
            card = TranscriptCardWidget(record, target_hwnd=self.target_hwnd, dark=self.dark)
            card.deleted.connect(self._delete_record)
            card.reinject_requested.connect(self._reinject_text)
            item.setSizeHint(card.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)

    def _delete_record(self, record_id: str):
        self.history.delete_entry(record_id)
        self._refresh_list(query=self.search_input.text())

    def _reinject_text(self, text: str):
        self.hide()
        QTimer.singleShot(150, lambda: paste_text(text, target_hwnd=self.target_hwnd))

    def _clear_all(self):
        reply = QMessageBox.question(
            self,
            "Clear Transcript History",
            "Are you sure you want to delete all saved transcripts? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self._refresh_list()

    def _export_history(self):
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Transcript History",
            os.path.expanduser("~/Documents/Dictate_Transcripts.md"),
            "Markdown Files (*.md);;Text Files (*.txt);;JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return

        try:
            if file_path.lower().endswith(".json") or "JSON" in selected_filter:
                data = [r.to_dict() for r in self.history.get_all()]
                content = json.dumps(data, indent=2, ensure_ascii=False)
            elif file_path.lower().endswith(".md") or "Markdown" in selected_filter:
                content = self.history.export_markdown()
            else:
                content = self.history.export_text()

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            QMessageBox.information(self, "Export Successful", f"Saved {len(self.history.get_all())} transcripts to:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not save file:\n{exc}")
