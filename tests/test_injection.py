from injection import typer


def test_paste_aborts_when_target_window_cannot_be_activated(monkeypatch):
    """Never paste dictation into an unrelated foreground application."""
    pasted = []
    monkeypatch.setattr(typer, "activate_window", lambda hwnd: False)
    monkeypatch.setattr(typer, "copy_to_clipboard", lambda text: pasted.append(text) or True)
    monkeypatch.setattr(typer, "_send_ctrl_v", lambda: pasted.append("ctrl-v"))

    result = typer.paste_text("do not send", target_hwnd=123)

    assert result is False
    assert pasted == []


def test_paste_uses_target_then_restores_clipboard(monkeypatch):
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
    assert calls == [("activate", 456), ("copy", "new text"), ("paste",), ("copy", "previous")]
    assert timers == [0.15]


def test_paste_uses_unicode_fallback_when_clipboard_is_unavailable(monkeypatch):
    calls = []
    monkeypatch.setattr(typer, "copy_to_clipboard", lambda text: False)
    monkeypatch.setattr(typer, "_send_unicode_string", lambda text: calls.append(text))

    assert typer.paste_text("Hello\nworld") is True
    assert calls == ["Hello\nworld"]
