"""Transcript History Dialog: search, stat counters, rich card view, copy feedback, and export."""
import json
import os
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QApplication,
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
from ui import theme

FONT_FAMILY = "Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif"


class TranscriptCardWidget(QFrame):
    """Rich card widget representing a single transcript record in history."""

    deleted = pyqtSignal(str)
    reinject_requested = pyqtSignal(str)

    def __init__(self, record: TranscriptRecord, target_hwnd: int = 0, parent=None):
        super().__init__(parent)
        self.record = record
        self.target_hwnd = target_hwnd

        self.setStyleSheet("""
            TranscriptCardWidget {
                background-color: #131B2E;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
            TranscriptCardWidget:hover {
                border-color: #38BDF8;
                background-color: #162035;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header row: timestamp, app badge, duration/words, actions
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        time_lbl = QLabel(record.formatted_time())
        time_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        time_lbl.setStyleSheet("color: #38BDF8;")
        header_row.addWidget(time_lbl)

        if record.target_app:
            app_badge = QLabel(record.target_app)
            app_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            app_badge.setStyleSheet("""
                color: #94A3B8;
                background-color: #090D16;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 1px 6px;
            """)
            header_row.addWidget(app_badge)

        if record.duration_s > 0 or record.word_count > 0:
            info_text = []
            if record.word_count > 0:
                info_text.append(f"{record.word_count} word{'s' if record.word_count != 1 else ''}")
            if record.duration_s > 0:
                info_text.append(f"{record.duration_s:.1f}s")
            stats_lbl = QLabel(" • ".join(info_text))
            stats_lbl.setFont(QFont("Segoe UI", 8))
            stats_lbl.setStyleSheet("color: #64748B;")
            header_row.addWidget(stats_lbl)

        header_row.addStretch()

        # Action Buttons
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 5px;
                padding: 3px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #38BDF8;
                color: #090D16;
                font-weight: bold;
                border-color: #38BDF8;
            }
        """)
        self.btn_copy.clicked.connect(self._copy_text)
        header_row.addWidget(self.btn_copy)

        self.btn_paste = QPushButton("Paste to App")
        self.btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_paste.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 5px;
                padding: 3px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #22C55E;
                color: #090D16;
                font-weight: bold;
                border-color: #22C55E;
            }
        """)
        self.btn_paste.clicked.connect(self._reinject_text)
        header_row.addWidget(self.btn_paste)

        btn_del = QPushButton("×")
        btn_del.setToolTip("Delete entry")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                font-size: 14px;
                font-weight: bold;
                padding: 0 4px;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        btn_del.clicked.connect(lambda: self.deleted.emit(self.record.id))
        header_row.addWidget(btn_del)

        layout.addLayout(header_row)

        # Body: Transcript Text
        text_lbl = QLabel(record.text)
        text_lbl.setFont(QFont("Segoe UI", 10))
        text_lbl.setStyleSheet("color: #F8FAFC; line-height: 1.4;")
        text_lbl.setWordWrap(True)
        text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text_lbl)

    def _copy_text(self):
        copy_to_clipboard(self.record.text)
        self.btn_copy.setText("✓ Copied")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #22C55E;
                color: #090D16;
                border: 1px solid #22C55E;
                border-radius: 5px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self.btn_copy.setText("Copy")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 5px;
                padding: 3px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #38BDF8;
                color: #090D16;
                font-weight: bold;
                border-color: #38BDF8;
            }
        """)

    def _reinject_text(self):
        self.reinject_requested.emit(self.record.text)


class HistoryDialog(QDialog):
    """Full-featured modal window to search, review, copy, and export past dictations."""

    def __init__(self, history_manager: HistoryManager, target_hwnd: int = 0, parent=None):
        super().__init__(parent)
        self.history = history_manager
        self.target_hwnd = target_hwnd

        self.setWindowTitle("Dictate — Transcript History")
        self.setMinimumSize(640, 520)
        self.resize(700, 580)
        self.setStyleSheet(theme.get_dialog_stylesheet(dark=True))

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        # Header Title & Summary
        top_bar = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        title = QLabel("Transcript History")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        header_text.addWidget(title)

        subtitle = QLabel("Search, copy, or export your recent voice typing records.")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #94A3B8;")
        header_text.addWidget(subtitle)
        top_bar.addLayout(header_text)
        top_bar.addStretch()

        root.addLayout(top_bar)

        # Stats Dashboard Strip
        self.stats_container = QFrame()
        self.stats_container.setStyleSheet("""
            QFrame {
                background-color: #131B2E;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(8, 4, 8, 4)

        self.stat_count_lbl = QLabel()
        self.stat_count_lbl.setStyleSheet("color: #38BDF8; font-weight: bold;")
        stats_layout.addWidget(self.stat_count_lbl)
        stats_layout.addStretch()

        self.stat_words_lbl = QLabel()
        self.stat_words_lbl.setStyleSheet("color: #34D399; font-weight: bold;")
        stats_layout.addWidget(self.stat_words_lbl)
        stats_layout.addStretch()

        self.stat_time_lbl = QLabel()
        self.stat_time_lbl.setStyleSheet("color: #A855F7; font-weight: bold;")
        stats_layout.addWidget(self.stat_time_lbl)

        root.addWidget(self.stats_container)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search transcripts, apps, or keywords…")
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

        btn_clear = QPushButton("Clear All")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #EF4444;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.15);
                border-color: #EF4444;
            }
        """)
        btn_clear.clicked.connect(self._clear_all)
        bottom_bar.addWidget(btn_clear)

        bottom_bar.addStretch()

        btn_export = QPushButton("Export…")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._export_history)
        bottom_bar.addWidget(btn_export)

        btn_close = QPushButton("Close")
        btn_close.setObjectName("primaryButton")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
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
        # Speech at ~130 WPM vs typing at ~40 WPM saves ~1.7 minutes per 100 words
        minutes_saved = round((total_words / 40.0) - (total_words / 130.0), 1) if total_words > 0 else 0.0

        self.stat_count_lbl.setText(f"📋 {total_entries} Dictations")
        self.stat_words_lbl.setText(f"💬 {total_words:,} Words")
        self.stat_time_lbl.setText(f"⚡ ~{minutes_saved:.0f}m Saved")

        if not entries:
            empty_item = QListWidgetItem()
            msg = "No transcripts recorded yet." if not query else "No transcripts match your search."
            empty_widget = QLabel(f"🎙 {msg}")
            empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_widget.setStyleSheet("color: #64748B; font-size: 13px; padding: 40px;")
            empty_item.setSizeHint(empty_widget.sizeHint())
            self.list_widget.addItem(empty_item)
            self.list_widget.setItemWidget(empty_item, empty_widget)
            return

        for record in entries:
            item = QListWidgetItem()
            card = TranscriptCardWidget(record, target_hwnd=self.target_hwnd)
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
