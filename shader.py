"""Real-time Apple Liquid Glass Refraction & Reflection Shader Engine.

Refactored from the original constants-based version so every optical
parameter lives on a `ShaderParams` object that can be mutated at any time
(e.g. from a slider callback) and takes effect on the very next frame.
No parameter is baked into a cache that would need a resize to refresh.
"""
import numpy as np
from dataclasses import dataclass
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap


@dataclass
class ShaderParams:
    # --- 1. Optical refraction & chromatic dispersion ---
    ior_liquid: float = 1.55          # 1.0 = no bending, 1.333 = water, 1.50 = dense crystal
    dispersion_strength: float = 2.0  # 0 = no fringing, 3+ = strong prism split
    lens_thickness: float = 2.5       # 0.25 = crisp/clean, 0.5+ = heavy magnification

    # --- 2. Specular reflection (Blinn-Phong) ---
    spec_key_intensity_dark: float = 160.0
    spec_key_intensity_light: float = 180.0
    spec_key_shininess: float = 55.0
    spec_fill_intensity_dark: float = 15.0
    spec_fill_intensity_light: float = 20.0
    spec_fill_shininess: float = 35.0

    # --- Fresnel-Schlick reflectance ---
    fresnel_f0: float = 0.20
    fresnel_power: float = 5.0

    # --- 3. Organic fluid undulation ---
    ripple_amplitude: float = 0.010
    ripple_speed: float = 2.4
    edge_feather: float = 0.04

    # --- 4. Light source vectors (raw, will be normalized) ---
    key_light: tuple = (-0.35, -0.65, 0.1)
    fill_light: tuple = (0.30, 0.60, 0.74)

    # --- Extra: state tint strength (referenced inline in original code) ---
    tint_strength_dark: float = 0.03
    tint_strength_light: float = 0.02


def _normalize(v):
    v = np.array(v, dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n > 1e-8 else v


class LiquidGlassShader:
    """Vectorized shader engine for real-time liquid glass rendering.

    Geometry (the capsule distance field) is cached per (w, h) since it is
    pure shape math. Every *optical* parameter is read fresh from a
    ShaderParams instance on every call, so slider changes are visible on
    the very next frame with no cache invalidation needed.
    """

    def __init__(self):
        self._cached_w = 0
        self._cached_h = 0
        self._cached_geo = None

    def _build_geometry_grid(self, w: int, h: int):
        """Precomputes normalized coordinate meshes and capsule distance fields.

        Note: does NOT include edge_feather-dependent antialiasing — that is
        computed fresh every frame in render() since it's cheap and must be
        live-tunable.
        """
        if w == self._cached_w and h == self._cached_h and self._cached_geo is not None:
            return self._cached_geo

        y_idx, x_idx = np.indices((h, w), dtype=np.float32)
        radius = (h - 1.0) / 2.0
        cy = (h - 1.0) / 2.0
        seg_x0 = radius
        seg_x1 = max(radius, (w - 1.0) - radius)

        clamped_x = np.clip(x_idx, seg_x0, seg_x1)
        dx = x_idx - clamped_x
        dy = y_idx - cy
        dist = np.sqrt(dx**2 + dy**2)
        u = dist / max(1.0, radius)

        u_clamped = np.clip(u, 0.0, 1.0)
        z0 = np.sqrt(np.maximum(0.0, 1.0 - u_clamped**2))

        dist_safe = np.maximum(dist, 1e-4)
        grad_x = np.where(u <= 1.05, dx / dist_safe, 0.0)
        grad_y = np.where(u <= 1.05, dy / dist_safe, 0.0)

        self._cached_w = w
        self._cached_h = h
        self._cached_geo = (x_idx, y_idx, u, z0, grad_x, grad_y, radius)
        return self._cached_geo

    def render(self, backdrop, w: int, h: int, dark: bool, accent_color: QColor,
               ripple_phase: float, params: ShaderParams) -> QImage:
        """Executes fragment-shader evaluation over the screen backdrop buffer."""
        if w <= 4 or h <= 4:
            return QImage()

        # Step 1: Backdrop texture buffer extraction
        if backdrop is None or backdrop.isNull():
            bg_img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            p = QPainter(bg_img)
            grad = QLinearGradient(0, 0, w, h)
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
            if bg_img.width() != w or bg_img.height() != h:
                bg_img = bg_img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)

        ptr = bg_img.bits()
        ptr.setsize(h * w * 4)
        bg_arr = np.frombuffer(ptr, np.uint8).reshape((h, w, 4))  # BGRA buffer

        # Step 2: Surface geometry & undulating liquid normal map
        x_idx, y_idx, u, z0, grad_x, grad_y, radius = self._build_geometry_grid(w, h)

        # Live edge feathering (not cached, so the slider is instant)
        edge_t = np.clip((1.0 - u) / max(params.edge_feather, 1e-4), 0.0, 1.0)
        edge_alpha = edge_t * edge_t * (3.0 - 2.0 * edge_t)

        ripple = (params.ripple_amplitude *
                  np.sin(x_idx * 0.16 + ripple_phase) *
                  np.cos(y_idx * 0.20 + ripple_phase * 0.7) *
                  (1.0 - np.clip(u, 0, 1) ** 2))
        z = np.clip(z0 + ripple, 0.0, 1.0)

        dz_du = np.where(z0 > 1e-4, u / np.maximum(z0, 0.1), 0.0)
        nx = grad_x * dz_du
        ny = grad_y * dz_du
        nz = np.ones_like(nx)
        norm_len = np.sqrt(nx**2 + ny**2 + nz**2)
        nx /= norm_len
        ny /= norm_len
        nz /= norm_len

        # Step 3: Snell's-law refraction & edge lensing
        boundary_taper = np.clip(1.0 - u**2, 0.0, 1.0)
        thickness = radius * params.lens_thickness * z * boundary_taper

        def compute_channel_displacement(ior: float):
            eta_inv = 1.0 / ior
            disp_x = -nx * (1.0 - eta_inv) * thickness
            disp_y = -ny * (1.0 - eta_inv) * thickness
            sample_x = np.clip(x_idx + disp_x, 0, w - 1).astype(np.int32)
            sample_y = np.clip(y_idx + disp_y, 0, h - 1).astype(np.int32)
            return sample_x, sample_y

        ior_red = params.ior_liquid - (0.015 * params.dispersion_strength)
        ior_blue = params.ior_liquid + (0.015 * params.dispersion_strength)

        rx, ry = compute_channel_displacement(ior_red)
        gx, gy = compute_channel_displacement(params.ior_liquid)
        bx, by = compute_channel_displacement(ior_blue)

        refracted_r = bg_arr[ry, rx, 2].astype(np.float32)
        refracted_g = bg_arr[gy, gx, 1].astype(np.float32)
        refracted_b = bg_arr[by, bx, 0].astype(np.float32)

        # Step 4: Blinn-Phong specular reflections (light vectors live-tunable)
        key_light = _normalize(params.key_light)
        fill_light = _normalize(params.fill_light)
        view_vector = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        half_key = _normalize(key_light + view_vector)
        half_fill = _normalize(fill_light + view_vector)

        n_dot_h_key = np.maximum(0.0, nx * half_key[0] + ny * half_key[1] + nz * half_key[2])
        spec_key_intensity = params.spec_key_intensity_dark if dark else params.spec_key_intensity_light
        spec_key = (n_dot_h_key ** params.spec_key_shininess) * spec_key_intensity * (u ** 2.5)

        n_dot_h_fill = np.maximum(0.0, nx * half_fill[0] + ny * half_fill[1] + nz * half_fill[2])
        spec_fill_intensity = params.spec_fill_intensity_dark if dark else params.spec_fill_intensity_light
        spec_fill = (n_dot_h_fill ** params.spec_fill_shininess) * spec_fill_intensity

        # Step 5: Fresnel-Schlick
        fresnel = params.fresnel_f0 + (1.0 - params.fresnel_f0) * ((1.0 - nz) ** params.fresnel_power)

        # Step 6: Final composite
        out_r = refracted_r * (1.0 - fresnel * 0.1) + spec_key + spec_fill * 0.3 + (fresnel * 40.0)
        out_g = refracted_g * (1.0 - fresnel * 0.1) + spec_key + spec_fill * 0.3 + (fresnel * 40.0)
        out_b = refracted_b * (1.0 - fresnel * 0.1) + spec_key + spec_fill * 0.4 + (fresnel * 55.0)

        if accent_color:
            t_r, t_g, t_b = accent_color.red(), accent_color.green(), accent_color.blue()
            tint_fac = params.tint_strength_dark if dark else params.tint_strength_light
            out_r = out_r * (1.0 - tint_fac) + t_r * tint_fac
            out_g = out_g * (1.0 - tint_fac) + t_g * tint_fac
            out_b = out_b * (1.0 - tint_fac) + t_b * tint_fac

        norm_alpha = np.clip(edge_alpha, 0.0, 1.0)
        out_r = np.clip(out_r * norm_alpha, 0.0, 255.0)
        out_g = np.clip(out_g * norm_alpha, 0.0, 255.0)
        out_b = np.clip(out_b * norm_alpha, 0.0, 255.0)
        out_a = np.clip(norm_alpha * 255.0, 0.0, 255.0)

        out_arr = np.zeros((h, w, 4), dtype=np.uint8)
        out_arr[..., 0] = out_b.astype(np.uint8)
        out_arr[..., 1] = out_g.astype(np.uint8)
        out_arr[..., 2] = out_r.astype(np.uint8)
        out_arr[..., 3] = out_a.astype(np.uint8)

        return QImage(out_arr.data, w, h, w * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()
