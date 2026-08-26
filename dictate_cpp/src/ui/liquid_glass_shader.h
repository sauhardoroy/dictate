#pragma once
#include <QImage>
#include <QPointF>
#include <cmath>
#include <algorithm>
#include <vector>

namespace Dictate {
namespace UI {

class LiquidGlassShader {
public:
    LiquidGlassShader() = default;

    static QImage render(
        const QImage& backdrop,
        int w,
        int h,
        double audioLevel = 0.0,
        double animPhase = 0.0,
        double lightDeltaX = -0.35,
        double lightDeltaY = -0.65,
        int supersampleFactor = 2
    ) {
        int rw = w * supersampleFactor;
        int rh = h * supersampleFactor;
        if (rw <= 0 || rh <= 0) return QImage();

        QImage result(rw, rh, QImage::Format_ARGB32_Premultiplied);
        result.setDevicePixelRatio(supersampleFactor);

        // Normalize 3D dynamic key light vector pointing towards screen center
        double zKey = 0.10;
        double normKey = std::sqrt(lightDeltaX * lightDeltaX + lightDeltaY * lightDeltaY + zKey * zKey);
        if (normKey < 1e-6) normKey = 1.0;
        double lx = lightDeltaX / normKey;
        double ly = lightDeltaY / normKey;
        double lz = zKey / normKey;

        // Optical constants
        const double ior = 1.25;
        const double eta = 1.0 / ior;
        const double fresnelF0 = 0.04;
        const double fresnelPower = 4.5;
        const double lensThickness = 3.5;
        const double specIntensity = 240.0;
        const double shininess = 8.0;

        double radius = std::min(rw, rh) * 0.5;
        double halfW = (rw - 2.0 * radius) * 0.5;
        double cx = rw * 0.5;
        double cy = rh * 0.5;

        // Bilinear backdrop sample helper
        auto sampleBackdrop = [&](double fx, double fy) -> QRgb {
            if (backdrop.isNull()) return qRgba(15, 23, 42, 220);
            int bw = backdrop.width();
            int bh = backdrop.height();
            fx = std::clamp(fx, 0.0, static_cast<double>(bw - 1.001));
            fy = std::clamp(fy, 0.0, static_cast<double>(bh - 1.001));
            int x0 = static_cast<int>(fx);
            int y0 = static_cast<int>(fy);
            int x1 = std::min(bw - 1, x0 + 1);
            int y1 = std::min(bh - 1, y0 + 1);
            double wx = fx - x0;
            double wy = fy - y0;

            QRgb c00 = backdrop.pixel(x0, y0);
            QRgb c10 = backdrop.pixel(x1, y0);
            QRgb c01 = backdrop.pixel(x0, y1);
            QRgb c11 = backdrop.pixel(x1, y1);

            auto interp = [&](int s00, int s10, int s01, int s11) {
                return (1.0 - wx) * (1.0 - wy) * s00 +
                       wx * (1.0 - wy) * s10 +
                       (1.0 - wx) * wy * s01 +
                       wx * wy * s11;
            };

            int r = std::clamp(static_cast<int>(interp(qRed(c00), qRed(c10), qRed(c01), qRed(c11))), 0, 255);
            int g = std::clamp(static_cast<int>(interp(qGreen(c00), qGreen(c10), qGreen(c01), qGreen(c11))), 0, 255);
            int b = std::clamp(static_cast<int>(interp(qBlue(c00), qBlue(c10), qBlue(c01), qBlue(c11))), 0, 255);
            return qRgba(r, g, b, 255);
        };

        for (int y = 0; y < rh; ++y) {
            QRgb* line = reinterpret_cast<QRgb*>(result.scanLine(y));
            double py = (y + 0.5) - cy;

            for (int x = 0; x < rw; ++x) {
                double px = (x + 0.5) - cx;

                // 2D Capsule Signed Distance Field
                double qx = std::max(0.0, std::abs(px) - halfW);
                double d = std::sqrt(qx * qx + py * py) - radius;

                if (d > 1.5) {
                    line[x] = qRgba(0, 0, 0, 0);
                    continue;
                }

                // Smooth Meniscus Antialiasing Alpha
                double alpha = std::clamp(1.0 - (d / 1.5), 0.0, 1.0);

                // Surface normal from 3D dome profile
                double h_dome = (d < 0.0) ? std::sqrt(std::max(0.0, radius * radius - (d + radius) * (d + radius))) : 0.0;
                double h_norm = h_dome / radius;

                // Normals
                double nx = (qx > 0.0) ? ((px > 0 ? 1 : -1) * qx) : 0.0;
                double ny = py;
                double nlen = std::sqrt(nx * nx + ny * ny + 1e-6);
                nx = (nx / nlen) * (1.0 - h_norm);
                ny = (ny / nlen) * (1.0 - h_norm);
                double nz = std::sqrt(std::max(0.05, 1.0 - nx * nx - ny * ny));

                // Fluid harmonic wave displacement
                if (audioLevel > 0.01) {
                    double wave = std::sin(animPhase + d * 0.15) * audioLevel * 0.08;
                    nx += wave;
                    ny += wave;
                }

                // Snell's Law Refraction
                double cosI = nz; // Eye vector = (0, 0, 1)
                double sinT2 = eta * eta * (1.0 - cosI * cosI);
                double cosT = std::sqrt(std::max(0.0, 1.0 - sinT2));
                double rx = -eta * nx;
                double ry = -eta * ny;

                // Chromatic Dispersion (Cauchy)
                double dRed = 1.0 - 0.018;
                double dGreen = 1.0;
                double dBlue = 1.0 + 0.024;

                double bgX = (static_cast<double>(x) / supersampleFactor);
                double bgY = (static_cast<double>(y) / supersampleFactor);

                QRgb colR = sampleBackdrop(bgX + rx * lensThickness * dRed, bgY + ry * lensThickness * dRed);
                QRgb colG = sampleBackdrop(bgX + rx * lensThickness * dGreen, bgY + ry * lensThickness * dGreen);
                QRgb colB = sampleBackdrop(bgX + rx * lensThickness * dBlue, bgY + ry * lensThickness * dBlue);

                // Blinn-Phong Specular Highlight (Key light tracking screen center)
                double hx = lx;
                double hy = ly;
                double hz = lz + 1.0;
                double hLen = std::sqrt(hx * hx + hy * hy + hz * hz);
                hx /= hLen; hy /= hLen; hz /= hLen;

                double NdotH = std::max(0.0, nx * hx + ny * hy + nz * hz);
                double spec = std::pow(NdotH, shininess) * specIntensity;

                // Fresnel reflection
                double fresnel = fresnelF0 + (1.0 - fresnelF0) * std::pow(1.0 - nz, fresnelPower);

                int outR = std::clamp(static_cast<int>(qRed(colR) * (1.0 - fresnel) + spec), 0, 255);
                int outG = std::clamp(static_cast<int>(qGreen(colG) * (1.0 - fresnel) + spec), 0, 255);
                int outB = std::clamp(static_cast<int>(qBlue(colB) * (1.0 - fresnel) + spec), 0, 255);
                int outA = static_cast<int>(255 * alpha);

                line[x] = qRgba(outR, outG, outB, outA);
            }
        }

        return result;
    }
};

} // namespace UI
} // namespace Dictate
