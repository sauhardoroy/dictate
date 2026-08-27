"""Transcript History Dialog: search, stat counters, rich card view, copy feedback, and export."""
import json
import os

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
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
from ui import theme


class TranscriptCardWidget(QFrame):
    """Rich card widget representing a single transcript record in history."""

    deleted = pyqtSignal(str)
    reinject_requested = pyqtSignal(str)

    def __init__(self, record: TranscriptRecord, target_hwnd: int = 0, dark: bool = True, parent=None):
        super().__init__(parent)
        self.record = record
        self.target_hwnd = target_hwnd
        self.dark = dark

        card_bg = theme.pick(theme.SURFACE_CARD, dark)
        border_subtle = theme.pick(theme.BORDER_SUBTLE, dark)
        accent = theme.pick(theme.SYSTEM_BLUE, dark)

        self.setStyleSheet(f"""
            TranscriptCardWidget {{
                background-color: {card_bg};
                border: 1px solid {border_subtle};
                border-radius: 10px;
            }}
            TranscriptCardWidget:hover {{
                border-color: {accent};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header row: timestamp, app badge, duration/words, actions
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        time_lbl = QLabel(record.formatted_time())
        time_lbl.setFont(theme.get_font(11, QFont.Weight.Bold))
        time_lbl.setStyleSheet(f"color: {accent};")
        header_row.addWidget(time_lbl)

        if record.target_app:
            app_badge = QLabel(record.target_app)
            app_badge.setFont(theme.get_font(10, QFont.Weight.DemiBold))
            elevated = theme.pick(theme.SURFACE_ELEVATED, dark)
            border_strong = theme.pick(theme.BORDER_STRONG, dark)
            app_badge.setStyleSheet(f"""
                color: {theme.pick(theme.TEXT_SECONDARY, dark)};
                background-color: {elevated};
                border: 1px solid {border_strong};
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
            stats_lbl.setFont(theme.get_font(10, QFont.Weight.Normal))
            stats_lbl.setStyleSheet(f"color: {theme.pick(theme.TEXT_MUTED, dark)};")
            header_row.addWidget(stats_lbl)

        header_row.addStretch()

        # Action Buttons
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setFixedHeight(28)
        self.btn_copy.clicked.connect(self._copy_text)
        header_row.addWidget(self.btn_copy)

        insert_label = f"Insert in {record.target_app}" if record.target_app else "Insert at Cursor"
        self.btn_paste = QPushButton(insert_label)
        self.btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_paste.setFixedHeight(28)
        self.btn_paste.clicked.connect(self._reinject_text)
        header_row.addWidget(self.btn_paste)

        btn_del = QPushButton("×")
        btn_del.setToolTip("Delete entry")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 0 6px;
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
        text_lbl.setFont(theme.get_font(13, QFont.Weight.Normal))
        text_lbl.setStyleSheet(f"color: {theme.pick(theme.TEXT_PRIMARY, dark)}; line-height: 1.4;")
        text_lbl.setWordWrap(True)
        text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text_lbl)

    def _copy_text(self):
        copy_to_clipboard(self.record.text)
        self.btn_copy.setText("✓ Copied")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 3px 12px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self.btn_copy.setText("Copy")
        self.btn_copy.setStyleSheet("")

    def _reinject_text(self):
        self.reinject_requested.emit(self.record.text)


class HistoryDialog(QDialog):
    """Full-featured modal window to search, review, copy, and export past dictations."""

    def __init__(self, history_manager: HistoryManager, target_hwnd: int = 0, dark: bool = True, parent=None):
        super().__init__(parent)
        self.history = history_manager
        self.target_hwnd = target_hwnd
        self.dark = dark

        self.setWindowTitle("Dictate — Transcript History")
        self.setMinimumSize(660, 540)
        self.resize(720, 600)
        self.setStyleSheet(theme.get_dialog_stylesheet(dark=self.dark))

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        # Header Title & Summary
        top_bar = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)
        title = QLabel("Transcript History")
        title.setFont(theme.get_font(20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {theme.pick(theme.TEXT_PRIMARY, self.dark)};")
        header_text.addWidget(title)

        subtitle = QLabel("Review, copy, or export your recent voice typing records.")
        subtitle.setFont(theme.get_font(12, QFont.Weight.Normal))
        subtitle.setStyleSheet(f"color: {theme.pick(theme.TEXT_SECONDARY, self.dark)};")
        header_text.addWidget(subtitle)
        top_bar.addLayout(header_text)
        top_bar.addStretch()

        root.addLayout(top_bar)

        # Stats Dashboard Strip
        self.stats_container = QFrame()
        card_bg = theme.pick(theme.SURFACE_CARD, self.dark)
        border_subtle = theme.pick(theme.BORDER_SUBTLE, self.dark)
        self.stats_container.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {border_subtle};
                border-radius: 8px;
                padding: 6px 14px;
            }}
        """)
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(8, 4, 8, 4)

        self.stat_count_lbl = QLabel()
        self.stat_count_lbl.setStyleSheet(f"color: {theme.pick(theme.SYSTEM_CYAN, self.dark)}; font-weight: bold;")
        stats_layout.addWidget(self.stat_count_lbl)
        stats_layout.addStretch()

        self.stat_words_lbl = QLabel()
        self.stat_words_lbl.setStyleSheet(f"color: {theme.pick(theme.SYSTEM_GREEN, self.dark)}; font-weight: bold;")
        stats_layout.addWidget(self.stat_words_lbl)
        stats_layout.addStretch()

        self.stat_time_lbl = QLabel()
        self.stat_time_lbl.setStyleSheet(f"color: {theme.pick(theme.SYSTEM_PURPLE, self.dark)}; font-weight: bold;")
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

        btn_clear = QPushButton("Clear All")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
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

        btn_close = QPushButton("Done")
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
        minutes_saved = round((total_words / 40.0) - (total_words / 130.0), 1) if total_words > 0 else 0.0

        self.stat_count_lbl.setText(f"{total_entries} Dictation{'s' if total_entries != 1 else ''}")
        self.stat_words_lbl.setText(f"{total_words:,} Words")
        self.stat_time_lbl.setText(f"~{minutes_saved:.0f}m Saved")

        if not entries:
            empty_item = QListWidgetItem()
            msg = "No transcripts recorded yet." if not query else "No transcripts match your search."
            empty_widget = QLabel(f"{msg}")
            empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_widget.setStyleSheet(f"color: {theme.pick(theme.TEXT_MUTED, self.dark)}; font-size: 13px; padding: 40px;")
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
