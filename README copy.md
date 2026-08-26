# Liquid Glass Shader Playground

Interactive test bench for tuning the liquid-glass shader parameters live.

## Setup
```
pip install -r requirements.txt
python app.py
```

## Usage
- Drag the droplet (the pill/capsule shape) around the dark backdrop with your mouse.
- Every parameter from the original shader is a slider on the right: refraction/IOR,
  chromatic dispersion, lens thickness, specular key/fill lighting + shininess,
  Fresnel F0/power, ripple amplitude/speed, edge feathering, key/fill light direction
  (XYZ), droplet width/height, dark/light theme, and tint color/strength.
- Only the small region of the backdrop under the droplet is re-rendered each frame
  (not the whole window), so it stays responsive (60+ fps) even while dragging or
  scrubbing sliders. Tested at ~336 fps for a 220x150 droplet and ~76 fps at the
  largest allowed size (500x300).
- Three preset buttons at the bottom (subtle iOS-style glass / heavy chromatic
  droplet / reset to defaults) for quick reference points.

## Files
- `shader.py` — the shader engine, refactored so all parameters live on a
  `ShaderParams` dataclass instance instead of module-level constants, so slider
  changes take effect on the very next frame without any cache invalidation.
- `app.py` — the PyQt6 GUI: draggable canvas + scrollable slider panel.
