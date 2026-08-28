"""Persistent transcript history manager."""
from dataclasses import asdict, dataclass
import datetime
import json
import os
import threading
from typing import Any, Optional
import uuid

from config.settings import settings_dir
from log import get_logger

log = get_logger(__name__)


@dataclass
class TranscriptRecord:
    id: str
    timestamp: str  # ISO format string
    text: str
    raw_text: str = ""
    duration_s: float = 0.0
    word_count: int = 0
    char_count: int = 0
    target_app: str = ""
    window_title: str = ""
    is_action: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptRecord":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:8]),
            timestamp=data.get("timestamp", datetime.datetime.now().isoformat()),
            text=data.get("text", ""),
            raw_text=data.get("raw_text", ""),
            duration_s=float(data.get("duration_s", 0.0)),
            word_count=int(data.get("word_count", 0)),
            char_count=int(data.get("char_count", len(data.get("text", "")))),
            target_app=data.get("target_app", ""),
            window_title=data.get("window_title", ""),
            is_action=bool(data.get("is_action", False)),
        )

    def formatted_time(self) -> str:
        """Human-readable timestamp (e.g. 'Today 4:15 PM' or 'Aug 26, 7:30 PM')."""
        try:
            dt = datetime.datetime.fromisoformat(self.timestamp)
            now = datetime.datetime.now()
            if dt.date() == now.date():
                return f"Today, {dt.strftime('%I:%M %p').lstrip('0')}"
            if dt.date() == (now - datetime.timedelta(days=1)).date():
                return f"Yesterday, {dt.strftime('%I:%M %p').lstrip('0')}"
            return dt.strftime("%b %d, %I:%M %p")
        except Exception:
            return self.timestamp


def get_default_history_path() -> str:
    """Resolve default history.json path in the settings directory."""
    return os.path.join(settings_dir(), "history.json")


class HistoryManager:
    """Thread-safe manager for recording, querying, and persisting dictation history."""

    def __init__(self, file_path: Optional[str] = None, max_entries: int = 100, enabled: bool = True):
        self.file_path = file_path or get_default_history_path()
        self.max_entries = max_entries
        self.enabled = enabled
        self._entries: list[TranscriptRecord] = []
        self._lock = threading.RLock()
        self.load()

    def load(self):
        """Load history from disk."""
        with self._lock:
            if not os.path.exists(self.file_path):
                self._entries = []
                return
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._entries = [TranscriptRecord.from_dict(item) for item in data]
                        # Keep newest first and bounded
                        self._entries = self._entries[:self.max_entries]
            except Exception as exc:
                log.warning("failed to load history from %s: %s", self.file_path, exc)
                self._entries = []

    def save(self):
        """Persist history to disk atomically."""
        if not self.enabled:
            return
        with self._lock:
            temp_path = None
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
                data = [e.to_dict() for e in self._entries[:self.max_entries]]
                unique_suffix = f"{os.getpid()}_{threading.get_ident()}_{uuid.uuid4().hex[:6]}"
                temp_path = f"{self.file_path}.{unique_suffix}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.file_path)
            except Exception as exc:
                log.warning("failed to save history to %s: %s", self.file_path, exc)
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

    def add_entry(
        self,
        text: str,
        raw_text: str = "",
        duration_s: float = 0.0,
        target_app: str = "",
        window_title: str = "",
        is_action: bool = False,
    ) -> Optional[TranscriptRecord]:
        """Record a new transcript and persist."""
        if not self.enabled or not text:
            return None

        clean_text = text.strip()
        if not clean_text:
            return None

        words = clean_text.split()
        record = TranscriptRecord(
            id=uuid.uuid4().hex[:12],
            timestamp=datetime.datetime.now().isoformat(),
            text=clean_text,
            raw_text=raw_text.strip() if raw_text else clean_text,
            duration_s=round(duration_s, 2),
            word_count=len(words),
            char_count=len(clean_text),
            target_app=target_app.strip(),
            window_title=window_title.strip(),
            is_action=is_action,
        )

        with self._lock:
            # Prepend newest entry
            self._entries.insert(0, record)
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[:self.max_entries]
            self.save()

        log.debug("recorded transcript history (%d chars, %d words)", record.char_count, record.word_count)
        return record

    def get_all(self) -> list[TranscriptRecord]:
        """Return a copy of all transcript records (newest first)."""
        with self._lock:
            return list(self._entries)

    def get_last(self) -> Optional[TranscriptRecord]:
        """Return the most recent transcript record, or None."""
        with self._lock:
            return self._entries[0] if self._entries else None

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        with self._lock:
            initial_count = len(self._entries)
            self._entries = [e for e in self._entries if e.id != entry_id]
            removed = len(self._entries) < initial_count
            if removed:
                self.save()
            return removed

    def clear(self):
        """Clear all entries from history."""
        with self._lock:
            self._entries = []
            self.save()
        log.info("cleared transcript history")

    def search(self, query: str) -> list[TranscriptRecord]:
        """Search entries matching query in text, target app, or window title."""
        if not query or not query.strip():
            return self.get_all()

        q = query.strip().lower()
        with self._lock:
            return [
                e for e in self._entries
                if q in e.text.lower()
                or q in e.target_app.lower()
                or q in e.window_title.lower()
            ]

    def export_text(self) -> str:
        """Export all entries as plain text."""
        entries = self.get_all()
        lines = []
        for e in reversed(entries):  # Chronological order for export
            app_info = f" [{e.target_app}]" if e.target_app else ""
            lines.append(f"[{e.formatted_time()}]{app_info}\n{e.text}\n")
        return "\n".join(lines)

    def export_markdown(self) -> str:
        """Export all entries as formatted Markdown."""
        entries = self.get_all()
        lines = [
            "# Dictate — Transcript History",
            f"*Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            f"*Total entries: {len(entries)}*",
            "",
            "---",
            "",
        ]
        for e in reversed(entries):
            app_badge = f" `{e.target_app}`" if e.target_app else ""
            lines.append(f"### {e.formatted_time()}{app_badge}")
            if e.window_title:
                lines.append(f"> Target window: *{e.window_title}*")
            lines.append(f"\n{e.text}\n")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)
