/**
 * Dictate Floating Shape-Shifting Liquid Glass Pill Component (Shadow DOM)
 */

class DictatePillOverlay {
  constructor(onToggleCallback) {
    this.onToggle = onToggleCallback;
    this.state = "idle";
    this.width = 40;
    this.targetWidth = 40;
    this.height = 40;
    this.audioLevel = 0.0;
    this.targetAudioLevel = 0.0;
    this.isDragging = false;
    this.dragMoved = false;
    this.dragOffset = { x: 0, y: 0 };
    this.pos = { x: window.innerWidth - 76, y: window.innerHeight - 76 };

    this.stateStyles = {
      idle: { width: 40, accent: "#0284C7", label: "Dictate (Click or Ctrl+Shift+P)" },
      recording: { width: 108, accent: "#E11D48", label: "Listening…" },
      transcribing: { width: 42, accent: "#7C3AED", label: "Polishing speech…" },
      injecting: { width: 38, accent: "#16A34A", label: "Pasted!" },
      error: { width: 38, accent: "#DC2626", label: "Error" }
    };

    this._initDom();
    this._restoreSavedPosition();
    this._startRenderLoop();
  }

  _initDom() {
    this.host = document.createElement("div");
    this.host.id = "dictate-pill-host";
    this.shadow = this.host.attachShadow({ mode: "open" });

    // Inject styles directly
    const style = document.createElement("style");
    style.textContent = `
      :host {
        all: initial;
        z-index: 2147483647;
        position: fixed;
        pointer-events: none;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      }
      .dictate-pill-wrapper {
        position: fixed;
        bottom: 36px;
        right: 36px;
        pointer-events: auto;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: width 0.24s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.15s ease;
        filter: drop-shadow(0 12px 28px rgba(0, 0, 0, 0.45));
        user-select: none;
        z-index: 2147483647;
      }
      .dictate-pill-wrapper:hover {
        transform: scale(1.04);
      }
      .dictate-pill-wrapper:active {
        cursor: grabbing;
      }
      .dictate-canvas {
        display: block;
        pointer-events: none;
      }
      .dictate-tooltip {
        position: absolute;
        bottom: calc(100% + 10px);
        left: 50%;
        transform: translateX(-50%) translateY(4px);
        background: rgba(15, 23, 42, 0.92);
        color: #F8FAFC;
        font-size: 11px;
        font-weight: 600;
        padding: 5px 10px;
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(10px);
        white-space: nowrap;
        pointer-events: none;
        opacity: 0;
        transition: all 0.18s ease;
      }
      .dictate-pill-wrapper:hover .dictate-tooltip {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
      }
    `;
    this.shadow.appendChild(style);

    // Pill wrapper
    this.wrapper = document.createElement("div");
    this.wrapper.className = "dictate-pill-wrapper";

    // Canvas
    this.canvas = document.createElement("canvas");
    this.canvas.className = "dictate-canvas";
    this.wrapper.appendChild(this.canvas);

    // Tooltip
    this.tooltip = document.createElement("div");
    this.tooltip.className = "dictate-tooltip";
    this.tooltip.textContent = "Dictate";
    this.wrapper.appendChild(this.tooltip);

    this.shadow.appendChild(this.wrapper);
    document.body.appendChild(this.host);

    this.renderer = new LiquidGlassRenderer(this.canvas);

    this._bindEvents();
  }

  _bindEvents() {
    this.wrapper.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return;
      e.preventDefault(); // Preserve focus on the active input/editor
      this.isDragging = true;
      this.dragMoved = false;
      this.dragOffset.x = e.clientX - this.pos.x;
      this.dragOffset.y = e.clientY - this.pos.y;
    });

    window.addEventListener("mousemove", (e) => {
      if (!this.isDragging) return;
      const dx = Math.abs(e.clientX - this.pos.x - this.dragOffset.x);
      const dy = Math.abs(e.clientY - this.pos.y - this.dragOffset.y);
      if (dx > 4 || dy > 4) {
        this.dragMoved = true;
      }
      this.pos.x = Math.max(10, Math.min(window.innerWidth - this.width - 10, e.clientX - this.dragOffset.x));
      this.pos.y = Math.max(10, Math.min(window.innerHeight - this.height - 10, e.clientY - this.dragOffset.y));
      this._updatePosition();
    });

    window.addEventListener("mouseup", (e) => {
      if (!this.isDragging) return;
      this.isDragging = false;
      if (!this.dragMoved) {
        if (this.onToggle) this.onToggle();
      } else {
        this._savePosition();
      }
    });

    window.addEventListener("resize", () => {
      this.pos.x = Math.min(this.pos.x, window.innerWidth - this.width - 10);
      this.pos.y = Math.min(this.pos.y, window.innerHeight - this.height - 10);
      this._updatePosition();
    });
  }

  _updatePosition() {
    this.wrapper.style.left = `${this.pos.x}px`;
    this.wrapper.style.top = `${this.pos.y}px`;
    this.wrapper.style.bottom = "auto";
    this.wrapper.style.right = "auto";
  }

  _restoreSavedPosition() {
    chrome.storage.local.get(["dictate_pill_pos"], (res) => {
      if (res.dictate_pill_pos) {
        this.pos.x = Math.min(res.dictate_pill_pos.x, window.innerWidth - 60);
        this.pos.y = Math.min(res.dictate_pill_pos.y, window.innerHeight - 60);
      } else {
        this.pos.x = window.innerWidth - 70;
        this.pos.y = window.innerHeight - 70;
      }
      this._updatePosition();
    });
  }

  _savePosition() {
    chrome.storage.local.set({ dictate_pill_pos: { x: this.pos.x, y: this.pos.y } });
  }

  setState(newState, detail = "") {
    if (!this.stateStyles[newState]) newState = "idle";
    this.state = newState;
    const style = this.stateStyles[newState];
    this.targetWidth = style.width;
    this.tooltip.textContent = detail ? `${style.label} (${detail})` : style.label;
  }

  setAudioLevel(rms) {
    this.targetAudioLevel = Math.max(0.0, Math.min(1.0, rms * 8.0));
  }

  _startRenderLoop() {
    const loop = () => {
      // Smooth width morphing
      this.width += (this.targetWidth - this.width) * 0.22;
      // Smooth audio visualizer level
      this.audioLevel += (this.targetAudioLevel - this.audioLevel) * 0.18;

      const style = this.stateStyles[this.state] || this.stateStyles.idle;

      // Vector pointing towards screen center for dynamic lighting
      const screenCx = window.innerWidth / 2;
      const screenCy = window.innerHeight / 2;
      const pillCx = this.pos.x + this.width / 2;
      const pillCy = this.pos.y + this.height / 2;
      const lightDx = screenCx - pillCx;
      const lightDy = screenCy - pillCy;

      this.renderer.render(
        Math.round(this.width),
        this.height,
        this.state,
        this.audioLevel,
        style.accent,
        lightDx,
        lightDy
      );

      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  setVisible(visible) {
    this.host.style.display = visible ? "block" : "none";
  }
}
