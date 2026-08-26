#pragma once
#include <string>
#include <QString>
#include <QColor>

namespace Dictate {
namespace Theme {

// ---------------------------------------------------------------------------
// 1. PILL GEOMETRY & MORPHING DIMENSIONS
// ---------------------------------------------------------------------------
inline constexpr int PILL_HEIGHT = 60;
inline constexpr int WIDTH_IDLE = 60;
inline constexpr int WIDTH_RECORDING = 120;
inline constexpr int WIDTH_TRANSCRIBING = 60;
inline constexpr int WIDTH_INJECTING = 60;
inline constexpr int WIDTH_LOADING = 60;
inline constexpr int WIDTH_ERROR = 60;

// ---------------------------------------------------------------------------
// 2. MOTION & ANIMATION TIMINGS
// ---------------------------------------------------------------------------
inline constexpr int MORPH_DURATION_MS = 240;
inline constexpr int EXIT_DURATION_MS = 300;
inline constexpr double MORPH_OVERSHOOT = 0.8;

inline constexpr int PULSE_DURATION_MS = 800;
inline constexpr int SHAKE_DURATION_MS = 300;
inline constexpr int SHAKE_DISTANCE_PX = 5;

inline constexpr double METER_SMOOTHING = 0.10;
inline constexpr int BACKDROP_UPDATE_MS = 15;

// ---------------------------------------------------------------------------
// 3. COLOR PALETTES & STATE STYLES (Deeper, darker, contrasty jewel tones)
// ---------------------------------------------------------------------------
inline const QString SYSTEM_RED_DARK    = "#B91C1C";
inline const QString SYSTEM_RED_LIGHT   = "#DC2626";

inline const QString SYSTEM_GREEN_DARK  = "#15803D";
inline const QString SYSTEM_GREEN_LIGHT = "#16A34A";

inline const QString SYSTEM_TEAL_DARK   = "#0369A1";
inline const QString SYSTEM_TEAL_LIGHT  = "#0284C7";

inline const QString SYSTEM_ROSE_DARK   = "#BE123C";
inline const QString SYSTEM_ROSE_LIGHT  = "#E11D48";

inline const QString SYSTEM_PURPLE_DARK = "#6D28D9";
inline const QString SYSTEM_PURPLE_LIGHT= "#7C3AED";

// Background Colors
inline const QString BG_DARK  = "#0F172A";
inline const QString BG_LIGHT = "#F8FAFC";

// State Icon Colors
inline const QString COLOR_IDLE         = "#0284C7"; // Sapphire Teal
inline const QString COLOR_RECORDING    = "#E11D48"; // Crimson Rose
inline const QString COLOR_TRANSCRIBING = "#7C3AED"; // Royal Purple
inline const QString COLOR_INJECTING    = "#16A34A"; // Emerald Green
inline const QString COLOR_LOADING      = "#0284C7"; // Cyan
inline const QString COLOR_ERROR        = "#DC2626"; // Bold Red

} // namespace Theme
} // namespace Dictate
