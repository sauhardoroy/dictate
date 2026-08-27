import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from ui.pill import Pill

app = QApplication(sys.argv)
p = Pill()
p.set_state("recording")
p.resize(310, 102)
p._width = 310.0
p._height = 102.0

print("1. First word 'one'")
p.update_preview("one")
p._on_card_anim_finished()
print("Visible cards:", [c['word'] for c in p._cards])
assert len(p._cards) == 1

print("2. Second word 'two'")
p.update_preview("one two")
p._on_card_anim_finished()
print("Visible cards:", [c['word'] for c in p._cards])
assert len(p._cards) == 2

print("3. Third word 'three'")
p.update_preview("one two three")
p._on_card_anim_finished()
print("Visible cards:", [c['word'] for c in p._cards])
assert len(p._cards) == 3

print("4. Fourth word 'four' -> 'one' should exit off the left, keeping max 3 cards")
p.update_preview("one two three four")
p._on_card_anim_finished()
print("Visible cards:", [c['word'] for c in p._cards])
assert len(p._cards) == 3
assert [c['word'] for c in p._cards] == ["two", "three", "four"]

print("5. Render with transparent glass pipeline")
p.repaint()
print("3-card focus and exit pipeline verified successfully!")
