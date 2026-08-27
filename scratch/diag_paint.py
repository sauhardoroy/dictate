import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import traceback

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPainter, QPaintEvent
from PyQt6.QtCore import Qt, QRect

app = QApplication(sys.argv)
from ui.pill import Pill

p = Pill()
p.set_state("recording")
p.resize(290, 84)
p._width = 290.0
p._height = 84.0
p.update_preview("hello world testing cards deck")

try:
    p.repaint()
    print("Repaint executed cleanly!")
except Exception as e:
    traceback.print_exc()
