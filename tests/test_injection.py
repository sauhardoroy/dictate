from injection import typer


def test_paste_retains_on_clipboard_when_target_window_cannot_be_activated(monkeypatch):
    """Never blind paste into unrelated app, but safely retain dictated text in clipboard."""
    copied = []
    pasted = []
    monkeypatch.setattr(typer, "activate_window", lambda hwnd: False)
    monkeypatch.setattr(typer, "copy_to_clipboard", lambda text: copied.append(text) or True)
    monkeypatch.setattr(typer, "_send_ctrl_v", lambda: pasted.append("ctrl-v"))

    result = typer.paste_text("important dictation", target_hwnd=123)

    assert result is True
    assert copied == ["important dictation"]
    assert pasted == []


def test_paste_default_keeps_clipboard_without_restore(monkeypatch):
    """Default mode (restore=False) keeps transcribed text on clipboard for future Ctrl+V."""
    calls = []
    monkeypatch.setattr(typer, "activate_window", lambda hwnd: calls.append(("activate", hwnd)) or True)
    monkeypatch.setattr(typer, "copy_to_clipboard", lambda text: calls.append(("copy", text)) or True)
    monkeypatch.setattr(typer, "_send_ctrl_v", lambda: calls.append(("paste",)))

    result = typer.paste_text("new text", restore=False, target_hwnd=456)

    assert result is True
    assert calls == [("copy", "new text"), ("activate", 456), ("paste",)]


def test_paste_uses_target_then_restores_clipboard_when_explicitly_requested(monkeypatch):
    calls = []
    timers = []

    class ImmediateTimer:
        def __init__(self, seconds, callback):
            timers.append(seconds)
            self.callback = callback

        def start(self):
            self.callback()

    monkeypatch.setattr(typer, "activate_window", lambda hwnd: calls.append(("activate", hwnd)) or True)
    monkeypatch.setattr(typer, "get_clipboard_text", lambda: "previous")
    monkeypatch.setattr(typer, "copy_to_clipboard", lambda text: calls.append(("copy", text)) or True)
    monkeypatch.setattr(typer, "_send_ctrl_v", lambda: calls.append(("paste",)))
    monkeypatch.setattr(typer.threading, "Timer", ImmediateTimer)

    result = typer.paste_text("new text", restore=True, delay_ms=150, target_hwnd=456)

    assert result is True
    assert calls == [("copy", "new text"), ("activate", 456), ("paste",), ("copy", "previous")]
    assert timers == [0.15]


def test_paste_uses_unicode_fallback_when_clipboard_is_unavailable(monkeypatch):
    calls = []
    monkeypatch.setattr(typer, "copy_to_clipboard", lambda text: False)
    monkeypatch.setattr(typer, "_send_unicode_string", lambda text: calls.append(text))

    assert typer.paste_text("Hello\nworld") is True
    assert calls == ["Hello\nworld"]

