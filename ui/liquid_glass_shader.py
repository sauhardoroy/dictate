"""Real-time Apple Liquid Glass Refraction & Reflection Shader Engine.

==============================================================================
TUNABLE PARAMETERS FOR LIQUID GLASS OPTICS, LIGHTING & MOTION
(Modify any of the values below to customize the look and feel)
==============================================================================
"""
import math
import time
import numpy as np

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

# ----------------------------------------------------------------------------
# 1. OPTICAL REFRACTION & CHROMATIC DISPERSION PARAMETERS
# ----------------------------------------------------------------------------
# Index of Refraction (IOR): 1.0 = no bending, 1.333 = water/liquid glass, 1.50 = dense crystal
IOR_LIQUID = 1.25

# Dispersion (Chromatic Aberration): controls how much red and blue split at the meniscus edge
# 0.0 = no color fringing, 0.5 - 1.0 = subtle realism, 3.0+ = strong prism chromatic effect
DISPERSION_STRENGTH = 0.2

# Lens Thickness Factor: Controls how thick the liquid dome is (0.25 = crisp & clean, 0.5+ = heavy magnification)
LENS_THICKNESS = 3.5

# ----------------------------------------------------------------------------
# 2. SPECULAR REFLECTION & LIGHTING MODEL (Blinn-Phong)
# ----------------------------------------------------------------------------
# Key Light Specular Glint (Overhead light glint)
SPECULAR_KEY_INTENSITY_DARK = 220.0   # Brightness of the crisp glint (0.0 to 255.0)
SPECULAR_KEY_INTENSITY_LIGHT = 190.0  # Brightness on light theme (0.0 to 255.0)
SPECULAR_KEY_SHININESS = 8.0          # Exponent: higher (50+) = sharp/pinpoint glint, lower (10) = cloudy/broad

# Secondary Fill / Bottom Caustic Bounce (Subtle upward reflection pool)
SPECULAR_FILL_INTENSITY_DARK = 0.0    # Keep low (10-25) to avoid cloudy fogging
SPECULAR_FILL_INTENSITY_LIGHT = 0.0
SPECULAR_FILL_SHININESS = 1.0

# Fresnel Reflectance: F0 at normal incidence (looking straight through center)
FRESNEL_F0 = 0.000
FRESNEL_POWER = 4.0                  # Higher (4.0-6.0) restricts reflections strictly to the outer rim

# ----------------------------------------------------------------------------
# 3. ORGANIC FLUID UNDULATION & SURFACE WAVES
# ----------------------------------------------------------------------------
# Wave Amplitude: 0.0 = completely smooth solid glass, 0.010 = subtle organic liquid surface
RIPPLE_AMPLITUDE = 0.010
RIPPLE_SPEED = 2.4                   # Speed of fluid wave animation

# Edge Feathering (Subpixel Anti-Aliasing)
EDGE_FEATHER = 0.20                  # Smoothness of the outer perimeter boundary

# ----------------------------------------------------------------------------
# 4. LIGHT SOURCE VECTORS & SCREEN-CENTER POSITIONAL TRACKING
# ----------------------------------------------------------------------------
# Key Light Z elevation (fixed at 0.1 for grazing edge meniscus lighting)
KEY_LIGHT_Z = 0.10

# Default baseline Key Light vector
DEFAULT_KEY_LIGHT = np.array([-0.35, -0.65, KEY_LIGHT_Z], dtype=np.float32)
DEFAULT_KEY_LIGHT /= np.linalg.norm(DEFAULT_KEY_LIGHT)

FILL_LIGHT = np.array([0.30, 0.60, 0.74], dtype=np.float32)
FILL_LIGHT /= np.linalg.norm(FILL_LIGHT)

VIEW_VECTOR = np.array([0.0, 0.0, 1.0], dtype=np.float32)

HALF_FILL = FILL_LIGHT + VIEW_VECTOR
HALF_FILL /= np.linalg.norm(HALF_FILL)


def _bilinear_sample_2d(channel_2d: np.ndarray, fx: np.ndarray, fy: np.ndarray, w: int, h: int) -> np.ndarray:
    """High-Definition Bilinear Subpixel Sampling for continuous, silky-smooth optical refraction."""
    fx_c = np.clip(fx, 0.0, float(w - 1.001))
    fy_c = np.clip(fy, 0.0, float(h - 1.001))

    x0 = fx_c.astype(np.int32)
    y0 = fy_c.astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)

    wx = (fx_c - x0).astype(np.float32)
    wy = (fy_c - y0).astype(np.float32)

    top = (1.0 - wx) * channel_2d[y0, x0] + wx * channel_2d[y0, x1]
    bot = (1.0 - wx) * channel_2d[y1, x0] + wx * channel_2d[y1, x1]
    return (1.0 - wy) * top + wy * bot


class LiquidGlassShader:
    """High-performance vectorized shader engine for real-time liquid glass rendering with HD supersampling."""

    def __init__(self):
        self._cached_w = 0
        self._cached_h = 0
        self._cached_radius = 0.0
        self._cached_grid = None

    def _build_geometry_grid(self, w: int, h: int, corner_radius: float = None):
        """Precomputes normalized coordinate meshes and rounded-rectangle distance fields."""
        if corner_radius is None:
            r = min((w - 1.0) / 2.0, (h - 1.0) / 2.0)
        else:
            r = min(float(corner_radius), (w - 1.0) / 2.0, (h - 1.0) / 2.0)

        if w == self._cached_w and h == self._cached_h and abs(r - self._cached_radius) < 1e-3 and self._cached_grid is not None:
            return self._cached_grid

        y_idx, x_idx = np.indices((h, w), dtype=np.float32)
        
        # Distance to rounded rectangle spine box [(r, r), (w - 1 - r, h - 1 - r)]
        seg_x0 = r
        seg_x1 = max(r, (w - 1.0) - r)
        seg_y0 = r
        seg_y1 = max(r, (h - 1.0) - r)

        clamped_x = np.clip(x_idx, seg_x0, seg_x1)
        clamped_y = np.clip(y_idx, seg_y0, seg_y1)
        dx = x_idx - clamped_x
        dy = y_idx - clamped_y
        dist = np.sqrt(dx**2 + dy**2)
        u = dist / max(1.0, r)  # Normalized distance: 0 at interior, 1 at perimeter

        # Subpixel smoothstep antialiased edge mask
        edge_t = np.clip((1.0 - u) / EDGE_FEATHER, 0.0, 1.0)
        edge_alpha = edge_t * edge_t * (3.0 - 2.0 * edge_t)

        # Spherical dome profile z0 = sqrt(max(0, 1 - u^2))
        u_clamped = np.clip(u, 0.0, 1.0)
        z0 = np.sqrt(np.maximum(0.0, 1.0 - u_clamped**2))

        # Analytical distance field gradient
        dist_safe = np.maximum(dist, 1e-4)
        grad_x = np.where(u <= 1.05, dx / dist_safe, 0.0)
        grad_y = np.where(u <= 1.05, dy / dist_safe, 0.0)

        self._cached_w = w
        self._cached_h = h
        self._cached_radius = r
        self._cached_grid = (x_idx, y_idx, u, edge_alpha, z0, grad_x, grad_y, r)
        return self._cached_grid

    def render(self, backdrop: QPixmap, w: int, h: int, dark: bool = True,
               accent_color: QColor = None, ripple_phase: float = 0.0,
               screen_center_delta: tuple[float, float] = None,
               supersample_factor: int = 2,
               corner_radius: float = None,
               black_tint: float = 0.0) -> QImage:
        """Executes Pass 2: High-Definition Fragment shader evaluation over screen backdrop buffer."""
        if w <= 4 or h <= 4:
            return QImage()

        # Render at 2x Retina resolution for razor-sharp, silky edges
        scale = max(1, supersample_factor)
        render_w = int(w * scale)
        render_h = int(h * scale)

        # Step 1: Backdrop texture buffer extraction
        if backdrop is None or backdrop.isNull():
            bg_img = QImage(render_w, render_h, QImage.Format.Format_ARGB32_Premultiplied)
            p = QPainter(bg_img)
            grad = QLinearGradient(0, 0, render_w, render_h)
            if dark:
                grad.setColorAt(0.0, QColor("#1E293B"))
                grad.setColorAt(1.0, QColor("#0F172A"))
            else:
                grad.setColorAt(0.0, QColor("#F8FAFC"))
                grad.setColorAt(1.0, QColor("#E2E8F0"))
            p.fillRect(bg_img.rect(), grad)
            p.end()
        else:
            bg_img = backdrop.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            if bg_img.width() != render_w or bg_img.height() != render_h:
                bg_img = bg_img.scaled(render_w, render_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

        ptr = bg_img.bits()
        ptr.setsize(render_h * render_w * 4)
        bg_arr = np.frombuffer(ptr, np.uint8).reshape((render_h, render_w, 4))  # BGRA buffer

        # Step 2: Surface Geometry & Undulating Liquid Normal Map (at 2x HD resolution)
        scaled_r = corner_radius * scale if corner_radius is not None else None
        x_idx, y_idx, u, edge_alpha, z0, grad_x, grad_y, radius = self._build_geometry_grid(render_w, render_h, scaled_r)

        # Dynamic harmonic ripple undulation
        ripple = RIPPLE_AMPLITUDE * np.sin((x_idx / scale) * 0.16 + ripple_phase) * np.cos((y_idx / scale) * 0.20 + ripple_phase * 0.7) * (1.0 - np.clip(u, 0, 1)**2)
        z = np.clip(z0 + ripple, 0.0, 1.0)

        # Surface Normal Vector N = normalize(-dz/dx, -dz/dy, 1)
        dz_du = np.where(z0 > 1e-4, u / np.maximum(z0, 0.1), 0.0)
        nx = grad_x * dz_du
        ny = grad_y * dz_du
        nz = np.ones_like(nx)

        norm_len = np.sqrt(nx**2 + ny**2 + nz**2)
        nx /= norm_len
        ny /= norm_len
        nz /= norm_len

        # Step 3: Converging Snell's Law Refraction & Edge Lensing Multiplier
        boundary_taper = np.clip(1.0 - u**2, 0.0, 1.0)
        thickness = radius * LENS_THICKNESS * z * boundary_taper

        # Vectorized Snell Refraction displacement coordinates (float subpixels)
        def compute_channel_coords(ior: float):
            eta_inv = 1.0 / ior
            disp_x = -nx * (1.0 - eta_inv) * thickness
            disp_y = -ny * (1.0 - eta_inv) * thickness
            return x_idx + disp_x, y_idx + disp_y

        # Cauchy dispersion: Wavelength split (Red bends slightly less, Blue bends slightly more)
        ior_red = IOR_LIQUID - (0.015 * DISPERSION_STRENGTH)
        ior_blue = IOR_LIQUID + (0.015 * DISPERSION_STRENGTH)

        rx, ry = compute_channel_coords(ior_red)
        gx, gy = compute_channel_coords(IOR_LIQUID)
        bx, by = compute_channel_coords(ior_blue)

        # High-Definition Bilinear Subpixel Sampling (Smooth, non-pixelated sampling)
        b_channel = bg_arr[..., 0].astype(np.float32)
        g_channel = bg_arr[..., 1].astype(np.float32)
        r_channel = bg_arr[..., 2].astype(np.float32)

        refracted_r = _bilinear_sample_2d(r_channel, rx, ry, render_w, render_h)
        refracted_g = _bilinear_sample_2d(g_channel, gx, gy, render_w, render_h)
        refracted_b = _bilinear_sample_2d(b_channel, bx, by, render_w, render_h)

        # Step 4: Dynamic Screen-Center Key Light Calculation
        if screen_center_delta is not None:
            cdx, cdy = screen_center_delta
            cdist = math.sqrt(cdx * cdx + cdy * cdy)
            if cdist > 1.0:
                key_l = np.array([cdx / cdist, cdy / cdist, KEY_LIGHT_Z], dtype=np.float32)
                key_l /= np.linalg.norm(key_l)
            else:
                key_l = DEFAULT_KEY_LIGHT
        else:
            key_l = DEFAULT_KEY_LIGHT

        half_key = key_l + VIEW_VECTOR
        half_key /= np.linalg.norm(half_key)

        # Key Light Specular Glint (Edge weighted with u^2.5)
        n_dot_h_key = np.maximum(0.0, nx * half_key[0] + ny * half_key[1] + nz * half_key[2])
        spec_key_intensity = SPECULAR_KEY_INTENSITY_DARK if dark else SPECULAR_KEY_INTENSITY_LIGHT
        spec_key = (n_dot_h_key**SPECULAR_KEY_SHININESS) * spec_key_intensity * (u**2.5)

        # Fill / Bottom Caustic Bounce Specular
        n_dot_h_fill = np.maximum(0.0, nx * HALF_FILL[0] + ny * HALF_FILL[1] + nz * HALF_FILL[2])
        spec_fill_intensity = SPECULAR_FILL_INTENSITY_DARK if dark else SPECULAR_FILL_INTENSITY_LIGHT
        spec_fill = (n_dot_h_fill**SPECULAR_FILL_SHININESS) * spec_fill_intensity

        # Step 5: Fresnel-Schlick Angle-Dependent Reflectance
        fresnel = FRESNEL_F0 + (1.0 - FRESNEL_F0) * ((1.0 - nz)**FRESNEL_POWER)

        # Step 6: Final Composite with Premultiplied Alpha
        out_r = refracted_r * (1.0 - fresnel * 0.1) + spec_key + spec_fill * 0.3 + (fresnel * 40.0)
        out_g = refracted_g * (1.0 - fresnel * 0.1) + spec_key + spec_fill * 0.3 + (fresnel * 40.0)
        out_b = refracted_b * (1.0 - fresnel * 0.1) + spec_key + spec_fill * 0.4 + (fresnel * 55.0)

        # Subtle state tint
        if accent_color:
            t_r, t_g, t_b = accent_color.red(), accent_color.green(), accent_color.blue()
            tint_fac = 0.03 if dark else 0.02
            out_r = out_r * (1.0 - tint_fac) + t_r * tint_fac
            out_g = out_g * (1.0 - tint_fac) + t_g * tint_fac
            out_b = out_b * (1.0 - tint_fac) + t_b * tint_fac

        # Dark blackish obsidian glass tint for recording state
        if black_tint > 0.0:
            smoke_r = 10.0
            smoke_g = 12.0
            smoke_b = 18.0
            b_fac = np.clip(black_tint, 0.0, 1.0)
            out_r = out_r * (1.0 - b_fac * 0.50) + smoke_r * (b_fac * 0.50)
            out_g = out_g * (1.0 - b_fac * 0.50) + smoke_g * (b_fac * 0.50)
            out_b = out_b * (1.0 - b_fac * 0.50) + smoke_b * (b_fac * 0.50)

        # Multiply color by edge_alpha for proper ARGB32 Premultiplied compositing
        norm_alpha = np.clip(edge_alpha, 0.0, 1.0)
        out_r = np.clip(out_r * norm_alpha, 0.0, 255.0)
        out_g = np.clip(out_g * norm_alpha, 0.0, 255.0)
        out_b = np.clip(out_b * norm_alpha, 0.0, 255.0)
        out_a = np.clip(norm_alpha * 255.0, 0.0, 255.0)

        # Assemble output BGRA buffer
        out_arr = np.zeros((render_h, render_w, 4), dtype=np.uint8)
        out_arr[..., 0] = out_b.astype(np.uint8)  # B
        out_arr[..., 1] = out_g.astype(np.uint8)  # G
        out_arr[..., 2] = out_r.astype(np.uint8)  # R
        out_arr[..., 3] = out_a.astype(np.uint8)  # A

        hd_image = QImage(out_arr.data, render_w, render_h, render_w * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()
        hd_image.setDevicePixelRatio(scale)
        return hd_image


# Global shader engine singleton
shader_engine = LiquidGlassShader()
