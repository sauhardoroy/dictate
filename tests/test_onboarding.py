"""Unit tests for the Apple Liquid Glass OnboardingDialog."""
import pytest
from PyQt6.QtWidgets import QApplication
from ui.onboarding import OnboardingDialog, GlassBadge, GlassPanel, GlassButton, GlassProgressBar, SidebarRail


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_onboarding_dialog_initialization(qapp):
    dlg = OnboardingDialog(trigger_key="ctrl+shift+}", model_id="parakeet-tdt-0.6b-v3")
    assert dlg.stack.count() == 5
    assert dlg.stack.currentIndex() == 0
    assert dlg.btn_back.isHidden() is True
    assert dlg.btn_next.text() == "Next"
    assert dlg.sidebar._current_index == 0


def test_onboarding_dialog_navigation(qapp):
    dlg = OnboardingDialog(trigger_key="ctrl+shift+}", model_id="parakeet-tdt-0.6b-v3")
    
    # Page 0 -> Page 1
    dlg._go_next()
    assert dlg.stack.currentIndex() == 1
    assert dlg.btn_back.isHidden() is False
    assert dlg.sidebar._current_index == 1

    # Page 1 -> Page 2
    dlg._go_next()
    assert dlg.stack.currentIndex() == 2

    # Page 2 -> Page 3 (Download page)
    dlg._go_next()
    assert dlg.stack.currentIndex() == 3

    # Page 3 -> Page 4 (Ready page)
    dlg._go_next()
    assert dlg.stack.currentIndex() == 4
    assert dlg.btn_next.text() == "Start Dictating"

    # Page 4 -> Back -> Page 3
    dlg._go_back()
    assert dlg.stack.currentIndex() == 3



def test_glass_badge_vector_rendering(qapp):
    from PyQt6.QtGui import QColor
    badge = GlassBadge("welcome_hero", "mic", QColor("#38BDF8"), size=64)
    assert badge.width() == 64
    assert badge.height() == 64
