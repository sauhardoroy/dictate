"""Liquid Glass Shader Playground.

A fast, interactive PyQt6 test bench for the LiquidGlassShader engine.

- Drag the droplet around a busy test backdrop to see refraction respond
  to whatever is underneath it.
- Every optical parameter (refraction, dispersion, specular, Fresnel,
  ripples, light direction, tint, droplet size, theme) is exposed as a
  live slider — move it and the droplet updates on the very next frame.
- Rendering only touches the small droplet-sized region of the backdrop,
  not the whole window, so it stays responsive even while dragging.

Run with:  python app.py
"""
import sys
import time

from PyQt6.QtCore import Qt, QRect, QTimer, QPointF
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QFont, QPen, QRadialGradient
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout, QLabel,
    QSlider, QScrollArea, QGroupBox, QCheckBox, QPushButton, QColorDialog,
    QSizePolicy,
)

from shader import LiquidGlassShader, ShaderParams


# ----------------------------------------------------------------------------
# Backdrop: a busy test pattern so refraction/dispersion are easy to see
# ----------------------------------------------------------------------------
def build_test_backdrop(w: int, h: int) -> QPixmap:
    pm = QPixmap(w, h)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0.0, QColor("#0f2027"))
    grad.setColorAt(0.5, QColor("#203a43"))
    grad.setColorAt(1.0, QColor("#2c5364"))
    painter.fillRect(0, 0, w, h, grad)

    # Checkerboard so refraction distortion of straight lines is obvious
    cell = 28
    for gy in range(0, h, cell):
        for gx in range(0, w, cell):
            if ((gx // cell) + (gy // cell)) % 2 == 0:
                painter.fillRect(gx, gy, cell, cell, QColor(255, 255, 255, 18))

    # High-contrast colored circles (good for chromatic-aberration testing)
    colors = ["#FF453A", "#FFD60A", "#30D158", "#0A84FF", "#BF5AF2", "#FF9F0A"]
    r = 46
    step_x = w / (len(colors) + 1)
    for i, c in enumerate(colors):
        cx = step_x * (i + 1)
        cy = h * 0.32
        rg = QRadialGradient(cx, cy, r)
        rg.setColorAt(0.0, QColor(c))
        rg.setColorAt(1.0, QColor(c).darker(180))
        painter.setBrush(rg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), r, r)

    # Thin bright grid lines (great for seeing lens magnification)
    pen = QPen(QColor(255, 255, 255, 60), 2)
    painter.setPen(pen)
    for gx in range(0, w, cell * 2):
        painter.drawLine(gx, 0, gx, h)
    for gy in range(0, h, cell * 2):
        painter.drawLine(0, gy, w, gy)

    # Bold text (great for seeing dispersion/edge fringing on hard edges)
    painter.setPen(QColor(255, 255, 255, 230))
    painter.setFont(QFont("Arial", 42, QFont.Weight.Bold))
    painter.drawText(QRect(0, int(h * 0.55), w, 80), Qt.AlignmentFlag.AlignCenter, "LIQUID GLASS")
    painter.setFont(QFont("Arial", 16))
    painter.drawText(QRect(0, int(h * 0.55) + 70, w, 40), Qt.AlignmentFlag.AlignCenter,
                      "drag the droplet over me")

    painter.end()
    return pm


# ----------------------------------------------------------------------------
# Canvas: draws the backdrop + the draggable droplet
# ----------------------------------------------------------------------------
class DropletCanvas(QWidget):
    def __init__(self, shader: LiquidGlassShader, params: ShaderParams):
        super().__init__()
        self.shader = shader
        self.params = params
        self.dark = True
        self.accent_color = QColor("#0A84FF")

        self.droplet_w = 180
        self.droplet_h = 130
        self.cx = 300.0
        self.cy = 220.0

        self.dragging = False
        self.drag_offset = QPointF(0, 0)

        self.backdrop = QPixmap()
        self.phase = 0.0
        self._last_t = time.perf_counter()

        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)

        # Animation timer for the ripple; also drives smooth redraw while dragging
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)  # ~60 FPS

    def resizeEvent(self, event):
        self.backdrop = build_test_backdrop(max(self.width(), 10), max(self.height(), 10))
        self._clamp_center()
        super().resizeEvent(event)

    def _clamp_center(self):
        hw, hh = self.droplet_w / 2, self.droplet_h / 2
        self.cx = min(max(self.cx, hw), max(hw, self.width() - hw))
        self.cy = min(max(self.cy, hh), max(hh, self.height() - hh))

    def set_droplet_size(self, w=None, h=None):
        if w is not None:
            self.droplet_w = w
        if h is not None:
            self.droplet_h = h
        self._clamp_center()
        self.update()

    def _droplet_rect(self) -> QRect:
        x = int(self.cx - self.droplet_w / 2)
        y = int(self.cy - self.droplet_h / 2)
        return QRect(x, y, self.droplet_w, self.droplet_h)

    def _tick(self):
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now
        self.phase += dt * self.params.ripple_speed
        self.update()

    def mousePressEvent(self, event):
        rect = self._droplet_rect()
        if rect.contains(event.position().toPoint()):
            self.dragging = True
            self.drag_offset = QPointF(self.cx - event.position().x(), self.cy - event.position().y())

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.cx = event.position().x() + self.drag_offset.x()
            self.cy = event.position().y() + self.drag_offset.y()
            self._clamp_center()
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.backdrop.isNull():
            self.backdrop = build_test_backdrop(max(self.width(), 10), max(self.height(), 10))
        painter.drawPixmap(0, 0, self.backdrop)

        rect = self._droplet_rect()
        # Clamp the sample rect to backdrop bounds (defensive; center is already clamped)
        clipped = rect.intersected(self.backdrop.rect())
        if clipped.width() < 4 or clipped.height() < 4:
            return
        sub = self.backdrop.copy(clipped)

        img = self.shader.render(
            sub, clipped.width(), clipped.height(),
            dark=self.dark, accent_color=self.accent_color,
            ripple_phase=self.phase, params=self.params,
        )
        if not img.isNull():
            painter.drawImage(clipped.topLeft(), img)
        painter.end()


# ----------------------------------------------------------------------------
# Slider row helper: label + slider + live value readout
# ----------------------------------------------------------------------------
class ParamSlider(QWidget):
    def __init__(self, name, minval, maxval, value, decimals, on_change):
        super().__init__()
        self.decimals = decimals
        self.minval = minval
        self.maxval = maxval
        self.scale = 10 ** decimals
        self.on_change = on_change

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(1)

        row = QHBoxLayout()
        self.name_label = QLabel(name)
        self.value_label = QLabel(self._fmt(value))
        self.value_label.setStyleSheet("color: #888;")
        row.addWidget(self.name_label)
        row.addStretch()
        row.addWidget(self.value_label)
        layout.addLayout(row)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(minval * self.scale))
        self.slider.setMaximum(int(maxval * self.scale))
        self.slider.setValue(int(value * self.scale))
        self.slider.valueChanged.connect(self._changed)
        layout.addWidget(self.slider)

    def _fmt(self, v):
        return f"{v:.{self.decimals}f}" if self.decimals > 0 else f"{int(v)}"

    def _changed(self, raw):
        v = raw / self.scale
        self.value_label.setText(self._fmt(v))
        self.on_change(v)

    def set_value(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(int(v * self.scale))
        self.value_label.setText(self._fmt(v))
        self.slider.blockSignals(False)


# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Liquid Glass Shader Playground")
        self.resize(1200, 760)

        self.shader = LiquidGlassShader()
        self.params = ShaderParams()

        self.canvas = DropletCanvas(self.shader, self.params)

        central = QWidget()
        root = QHBoxLayout(central)
        root.addWidget(self.canvas, stretch=3)
        root.addWidget(self._build_control_panel(), stretch=2)
        self.setCentralWidget(central)

    # -- control panel -------------------------------------------------
    def _build_control_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(360)
        scroll.setMaximumWidth(440)

        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setSpacing(10)

        v.addWidget(self._group_refraction())
        v.addWidget(self._group_specular())
        v.addWidget(self._group_fresnel())
        v.addWidget(self._group_waves())
        v.addWidget(self._group_lights())
        v.addWidget(self._group_shape())
        v.addWidget(self._group_theme())
        v.addWidget(self._group_presets())
        v.addStretch()

        scroll.setWidget(panel)
        return scroll

    def _slider(self, layout, name, minv, maxv, value, decimals, setter):
        s = ParamSlider(name, minv, maxv, value, decimals, setter)
        layout.addWidget(s)
        return s

    def _group_refraction(self):
        g = QGroupBox("Refraction & Dispersion")
        v = QVBoxLayout(g)
        p = self.params
        self._slider(v, "Index of Refraction (IOR)", 1.0, 2.2, p.ior_liquid, 3,
                     lambda x: setattr(p, "ior_liquid", x))
        self._slider(v, "Dispersion Strength", 0.0, 5.0, p.dispersion_strength, 2,
                     lambda x: setattr(p, "dispersion_strength", x))
        self._slider(v, "Lens Thickness", 0.0, 4.0, p.lens_thickness, 2,
                     lambda x: setattr(p, "lens_thickness", x))
        return g

    def _group_specular(self):
        g = QGroupBox("Specular Reflection (Blinn-Phong)")
        v = QVBoxLayout(g)
        p = self.params
        self._slider(v, "Key Light Intensity (Dark)", 0.0, 400.0, p.spec_key_intensity_dark, 0,
                     lambda x: setattr(p, "spec_key_intensity_dark", x))
        self._slider(v, "Key Light Intensity (Light)", 0.0, 400.0, p.spec_key_intensity_light, 0,
                     lambda x: setattr(p, "spec_key_intensity_light", x))
        self._slider(v, "Key Light Shininess", 1.0, 200.0, p.spec_key_shininess, 0,
                     lambda x: setattr(p, "spec_key_shininess", x))
        self._slider(v, "Fill Light Intensity (Dark)", 0.0, 100.0, p.spec_fill_intensity_dark, 0,
                     lambda x: setattr(p, "spec_fill_intensity_dark", x))
        self._slider(v, "Fill Light Intensity (Light)", 0.0, 100.0, p.spec_fill_intensity_light, 0,
                     lambda x: setattr(p, "spec_fill_intensity_light", x))
        self._slider(v, "Fill Light Shininess", 1.0, 200.0, p.spec_fill_shininess, 0,
                     lambda x: setattr(p, "spec_fill_shininess", x))
        return g

    def _group_fresnel(self):
        g = QGroupBox("Fresnel-Schlick Reflectance")
        v = QVBoxLayout(g)
        p = self.params
        self._slider(v, "Fresnel F0 (center reflectance)", 0.0, 1.0, p.fresnel_f0, 3,
                     lambda x: setattr(p, "fresnel_f0", x))
        self._slider(v, "Fresnel Power (rim falloff)", 0.5, 10.0, p.fresnel_power, 2,
                     lambda x: setattr(p, "fresnel_power", x))
        return g

    def _group_waves(self):
        g = QGroupBox("Surface Waves & Edge")
        v = QVBoxLayout(g)
        p = self.params
        self._slider(v, "Ripple Amplitude", 0.0, 0.05, p.ripple_amplitude, 4,
                     lambda x: setattr(p, "ripple_amplitude", x))
        self._slider(v, "Ripple Speed", 0.0, 8.0, p.ripple_speed, 2,
                     lambda x: setattr(p, "ripple_speed", x))
        self._slider(v, "Edge Feather", 0.005, 0.30, p.edge_feather, 3,
                     lambda x: setattr(p, "edge_feather", x))
        return g

    def _group_lights(self):
        g = QGroupBox("Light Direction (view-space XYZ)")
        v = QVBoxLayout(g)
        p = self.params

        def make_axis(label, idx, light_attr):
            cur = list(getattr(p, light_attr))

            def setter(x):
                cur[idx] = x
                setattr(p, light_attr, tuple(cur))
            self._slider(v, label, -1.0, 1.0, cur[idx], 2, setter)

        v.addWidget(QLabel("<b>Key light</b>"))
        make_axis("Key X", 0, "key_light")
        make_axis("Key Y", 1, "key_light")
        make_axis("Key Z", 2, "key_light")
        v.addWidget(QLabel("<b>Fill light</b>"))
        make_axis("Fill X", 0, "fill_light")
        make_axis("Fill Y", 1, "fill_light")
        make_axis("Fill Z", 2, "fill_light")
        return g

    def _group_shape(self):
        g = QGroupBox("Droplet Shape")
        v = QVBoxLayout(g)
        self._slider(v, "Width", 60, 500, self.canvas.droplet_w, 0,
                     lambda x: self.canvas.set_droplet_size(w=int(x)))
        self._slider(v, "Height", 40, 300, self.canvas.droplet_h, 0,
                     lambda x: self.canvas.set_droplet_size(h=int(x)))
        return g

    def _group_theme(self):
        g = QGroupBox("Theme & Tint")
        v = QVBoxLayout(g)
        p = self.params

        dark_check = QCheckBox("Dark theme")
        dark_check.setChecked(self.canvas.dark)
        dark_check.toggled.connect(lambda checked: (setattr(self.canvas, "dark", checked), self.canvas.update()))
        v.addWidget(dark_check)

        color_btn = QPushButton("Pick accent tint color")
        def pick_color():
            c = QColorDialog.getColor(self.canvas.accent_color, self, "Accent tint color")
            if c.isValid():
                self.canvas.accent_color = c
        color_btn.clicked.connect(pick_color)
        v.addWidget(color_btn)

        self._slider(v, "Tint Strength (Dark)", 0.0, 0.5, p.tint_strength_dark, 3,
                     lambda x: setattr(p, "tint_strength_dark", x))
        self._slider(v, "Tint Strength (Light)", 0.0, 0.5, p.tint_strength_light, 3,
                     lambda x: setattr(p, "tint_strength_light", x))
        return g

    def _group_presets(self):
        g = QGroupBox("Presets")
        v = QVBoxLayout(g)

        def apply_preset(values):
            for k, val in values.items():
                setattr(self.params, k, val)
            self._refresh_all_sliders()
            self.canvas.update()

        subtle_btn = QPushButton("Subtle iOS-style glass")
        subtle_btn.clicked.connect(lambda: apply_preset(dict(
            ior_liquid=1.33, dispersion_strength=0.5, lens_thickness=0.5,
            fresnel_f0=0.05, fresnel_power=5.0, ripple_amplitude=0.0,
        )))
        v.addWidget(subtle_btn)

        heavy_btn = QPushButton("Heavy chromatic droplet")
        heavy_btn.clicked.connect(lambda: apply_preset(dict(
            ior_liquid=1.6, dispersion_strength=4.0, lens_thickness=3.0,
            fresnel_f0=0.25, fresnel_power=4.0, ripple_amplitude=0.02,
        )))
        v.addWidget(heavy_btn)

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(lambda: apply_preset(vars(ShaderParams())))
        v.addWidget(reset_btn)

        return g

    def _refresh_all_sliders(self):
        # Rebuild the whole control panel so slider positions reflect the
        # (possibly preset-changed) params object. Simple and reliable.
        old = self.centralWidget().layout().itemAt(1).widget()
        new_panel = self._build_control_panel()
        self.centralWidget().layout().replaceWidget(old, new_panel)
        old.deleteLater()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
