import os
import sys
import traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

try:
    from ui.pill import Pill
    from ui import theme

    app = QApplication.instance() or QApplication(sys.argv)
    pill = Pill()
    print("Pill created successfully")
    pill.set_state("recording")
    print("Pill recording state set successfully")
    pill.update_preview("hello world dynamic cards stacking")
    print(f"Pill words: {pill._words}")
    
    img = QImage(pill.width(), pill.height(), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    pill.render(p)
    p.end()
    print(f"Rendered image: {img.width()}x{img.height()}")
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
