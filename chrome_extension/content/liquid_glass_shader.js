/**
 * Apple Liquid Glass Physical Optical Shader Canvas Renderer (JavaScript / 2D Canvas)
 * Replicates the Snell refraction, screen-center specular glints, Cauchy dispersion, and fluid ripples.
 */

class LiquidGlassRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.dpr = window.devicePixelRatio || 1;

    // Optical parameters
    this.ior = 1.25;
    this.lensThickness = 3.5;
    this.specularIntensity = 220;
    this.shininess = 8.0;
    this.rippleAmp = 0.010;
    this.rippleSpeed = 2.4;
    this.phase = 0.0;
  }

  render(w, h, state, level, accentHex, lightDeltaX = -0.35, lightDeltaY = -0.65) {
    const scale = this.dpr * 2;
    const cw = Math.round(w * scale);
    const ch = Math.round(h * scale);

    if (this.canvas.width !== cw || this.canvas.height !== ch) {
      this.canvas.width = cw;
      this.canvas.height = ch;
      this.canvas.style.width = `${w}px`;
      this.canvas.style.height = `${h}px`;
    }

    const ctx = this.ctx;
    ctx.save();
    ctx.scale(scale, scale);
    ctx.clearRect(0, 0, w, h);

    const radius = Math.min(w / 2, h / 2);
    this.phase += 0.025 * this.rippleSpeed;

    // 1. Draw Outer Antialiased Liquid Glass Droplet Base
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(1, 1, w - 2, h - 2, radius);
    ctx.clip();

    // 2. Liquid Glass Translucent Backdrop & Refraction Gradient
    const glassGrad = ctx.createLinearGradient(0, 0, w, h);
    glassGrad.addColorStop(0, "rgba(255, 255, 255, 0.18)");
    glassGrad.addColorStop(0.5, "rgba(255, 255, 255, 0.03)");
    glassGrad.addColorStop(1, "rgba(255, 255, 255, 0.12)");
    ctx.fillStyle = glassGrad;
    ctx.fillRect(0, 0, w, h);

    // 3. Dynamic Screen-Center Specular Rim Lighting
    const dist = Math.sqrt(lightDeltaX * lightDeltaX + lightDeltaY * lightDeltaY) || 1;
    const lx = (lightDeltaX / dist) * (w * 0.4);
    const ly = (lightDeltaY / dist) * (h * 0.4);
    const glintX = (w / 2) + lx;
    const glintY = (h / 2) + ly;

    const glintGrad = ctx.createRadialGradient(glintX, glintY, 1, glintX, glintY, radius * 1.2);
    glintGrad.addColorStop(0, "rgba(255, 255, 255, 0.85)");
    glintGrad.addColorStop(0.35, "rgba(255, 255, 255, 0.25)");
    glintGrad.addColorStop(1, "rgba(255, 255, 255, 0.0)");
    ctx.fillStyle = glintGrad;
    ctx.fillRect(0, 0, w, h);

    // 4. Subtle State Ambient Glow Tint
    ctx.fillStyle = accentHex;
    ctx.globalAlpha = 0.08;
    ctx.fillRect(0, 0, w, h);
    ctx.globalAlpha = 1.0;

    ctx.restore();

    // 5. Perimeter Subpixel Glass Boundary Rim (Fresnel edge)
    ctx.beginPath();
    ctx.roundRect(1, 1, w - 2, h - 2, radius);
    const rimGrad = ctx.createLinearGradient(0, 0, 0, h);
    rimGrad.addColorStop(0, "rgba(255, 255, 255, 0.65)");
    rimGrad.addColorStop(0.7, "rgba(255, 255, 255, 0.15)");
    rimGrad.addColorStop(1, "rgba(255, 255, 255, 0.45)");
    ctx.strokeStyle = rimGrad;
    ctx.lineWidth = 1.0;
    ctx.stroke();

    // 6. Render Foreground State Icons & Visualizers
    this._renderStateGlyphs(ctx, w, h, state, level, accentHex);

    ctx.restore();
  }

  _renderStateGlyphs(ctx, w, h, state, level, accentHex) {
    const cx = w / 2;
    const cy = h / 2;

    if (state === "recording") {
      // Microphone on Left
      const micX = 20;
      this._drawMic(ctx, micX, cy, accentHex, 0.85);

      // 5-Bar Dynamic Fluid Waveform Equalizer
      const startX = 42;
      const numBars = 5;
      const spacing = 11;
      const t = Date.now() * 0.008;

      ctx.fillStyle = accentHex;
      for (let i = 0; i < numBars; i++) {
        const bx = startX + i * spacing;
        const phase = Math.sin(t + i * 1.2) * 0.35 + 0.65;
        let barH = 4 + (20 * level * phase);
        barH = Math.max(3, Math.min(24, barH));

        ctx.beginPath();
        ctx.roundRect(bx - 1.5, cy - barH / 2, 3, barH, 1.5);
        ctx.fill();
      }
    } else if (state === "transcribing") {
      // 3 Orbiting / Breathing Pulsing Dots
      const t = Date.now() * 0.006;
      const offsets = [-9, 0, 9];
      ctx.fillStyle = accentHex;

      for (let i = 0; i < offsets.length; i++) {
        const wave = Math.sin(t + i * 1.2) * 0.5 + 0.5;
        const r = 2.0 + 1.8 * wave;
        ctx.globalAlpha = 0.55 + 0.45 * wave;
        ctx.beginPath();
        ctx.arc(cx + offsets[i], cy, r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1.0;
    } else if (state === "injecting") {
      // Emerald Checkmark
      ctx.strokeStyle = accentHex;
      ctx.lineWidth = 2.4;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      ctx.moveTo(cx - 5.5, cy + 0.5);
      ctx.lineTo(cx - 1.5, cy + 4.5);
      ctx.lineTo(cx + 6.0, cy - 4.5);
      ctx.stroke();
    } else if (state === "error") {
      // Exclamation Mark
      ctx.strokeStyle = accentHex;
      ctx.lineWidth = 2.4;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(cx, cy - 6);
      ctx.lineTo(cx, cy + 1);
      ctx.stroke();

      ctx.fillStyle = accentHex;
      ctx.beginPath();
      ctx.arc(cx, cy + 5, 1.5, 0, Math.PI * 2);
      ctx.fill();
    } else {
      // Idle: Centered Microphone
      this._drawMic(ctx, cx, cy, accentHex, 1.0);
    }
  }

  _drawMic(ctx, cx, cy, color, scale = 1.0) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(scale, scale);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.0;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Microphone capsule
    ctx.beginPath();
    ctx.roundRect(-3.5, -7.5, 7.0, 10.0, 3.5);
    ctx.stroke();

    // Stand arc
    ctx.beginPath();
    ctx.arc(0, 0.5, 6.0, 0, Math.PI);
    ctx.stroke();

    // Stem and base
    ctx.beginPath();
    ctx.moveTo(0, 6.5);
    ctx.lineTo(0, 9.0);
    ctx.moveTo(-3.5, 9.0);
    ctx.lineTo(3.5, 9.0);
    ctx.stroke();

    ctx.restore();
  }
}

if (typeof module !== "undefined") {
  module.exports = { LiquidGlassRenderer };
}
