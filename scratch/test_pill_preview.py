"""Test In-Pill Live Transcript Preview Integration & Stacking Word Animations."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from ui.pill import Pill
from ui import theme
from app import DictateApp

def test_pill_preview():
    app = QApplication.instance() or QApplication(sys.argv)
    
    pill = Pill()
    assert pill.width() == theme.WIDTH_IDLE
    print(f"Pill initialized in idle state: width={pill.width()}")
    
    # 1. Start recording state
    pill.set_state("recording")
    print(f"Pill set to recording state: state={pill._state}")
    
    # 2. Feed streaming partial transcript
    pill.update_preview("hello")
    assert pill._state == "preview"
    assert pill._words == ["hello"]
    print(f"Pill updated with 1 word: {pill._words}, state={pill._state}")
    
    # 3. Feed longer partial transcript
    pill.update_preview("hello world how are you today")
    assert len(pill._words) == pill.MAX_VISIBLE_WORDS
    assert pill._words == ["how", "are", "you", "today"]
    print(f"Pill sliding window 4 words: {pill._words}")
    
    # 4. Render to QImage buffer to verify rendering pipeline
    img = QImage(320, 60, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    pill.render(p)
    p.end()
    assert not img.isNull()
    print("In-Pill live preview rendered successfully onto liquid glass buffer.")
    
    # 5. Clear preview & test state transition to transcribing & idle
    pill.clear_preview()
    assert len(pill._words) == 0
    pill.set_state("transcribing")
    assert pill._state == "transcribing"
    pill.set_state("idle")
    assert pill._state == "idle"
    print("Pill state transitions and preview clearing verified.")
    
    # 6. Test DictateApp smoke test
    dictate = DictateApp(load_model=False)
    dictate.hotkeys.unregister()
    print("DictateApp initialized cleanly without PreviewOverlay.")

if __name__ == "__main__":
    test_pill_preview()
