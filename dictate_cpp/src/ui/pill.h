#pragma once
#include <QWidget>
#include <QScreen>
#include <QPainter>
#include <QPainterPath>
#include <QTimer>
#include <QPropertyAnimation>
#include <QEasingCurve>
#include <QGuiApplication>
#include <QMouseEvent>
#include "liquid_glass_shader.h"
#include "theme.h"

namespace Dictate {
namespace UI {

class Pill : public QWidget {
    Q_OBJECT
    Q_PROPERTY(int pillWidth READ pillWidth WRITE setPillWidth)
    Q_PROPERTY(double shakeOffset READ shakeOffset WRITE setShakeOffset)

public:
    explicit Pill(QWidget* parent = nullptr) : QWidget(parent) {
        setWindowFlags(
            Qt::WindowType::FramelessWindowHint |
            Qt::WindowType::WindowStaysOnTopHint |
            Qt::WindowType::Tool |
            Qt::WindowType::SubWindow
        );
        setAttribute(Qt::WidgetAttribute::WA_TranslucentBackground, true);
        setAttribute(Qt::WidgetAttribute::WA_ShowWithoutActivating, true);
        setAttribute(Qt::WidgetAttribute::WA_Hover, true);

        m_width = Theme::WIDTH_IDLE;
        resize(m_width, Theme::PILL_HEIGHT);

        // Animation Timers
        m_visTimer = new QTimer(this);
        m_visTimer->setInterval(8); // 120 FPS
        connect(m_visTimer, &QTimer::timeout, this, &Pill::onVisTick);
        m_visTimer->start();

        m_bgTimer = new QTimer(this);
        m_bgTimer->setInterval(Theme::BACKDROP_UPDATE_MS);
        connect(m_bgTimer, &QTimer::timeout, this, &Pill::onBackdropUpdate);
        m_bgTimer->start();
    }

    int pillWidth() const { return m_width; }
    void setPillWidth(int w) {
        m_width = w;
        resize(m_width, Theme::PILL_HEIGHT);
        update();
    }

    double shakeOffset() const { return m_shakeOffset; }
    void setShakeOffset(double offset) {
        m_shakeOffset = offset;
        update();
    }

    void setState(const QString& state, const QString& detail = "") {
        m_state = state;
        m_detail = detail;

        int targetWidth = Theme::WIDTH_IDLE;
        if (state == "recording") targetWidth = Theme::WIDTH_RECORDING;
        else if (state == "transcribing") targetWidth = Theme::WIDTH_TRANSCRIBING;
        else if (state == "injecting") targetWidth = Theme::WIDTH_INJECTING;
        else if (state == "loading") targetWidth = Theme::WIDTH_LOADING;
        else if (state == "error") targetWidth = Theme::WIDTH_ERROR;

        if (targetWidth != m_width) {
            auto anim = new QPropertyAnimation(this, "pillWidth", this);
            anim->setDuration(targetWidth > m_width ? Theme::MORPH_DURATION_MS : Theme::EXIT_DURATION_MS);
            anim->setStartValue(m_width);
            anim->setEndValue(targetWidth);
            anim->setEasingCurve(QEasingCurve::Type::OutBack);
            anim->start(QAbstractAnimation::DeleteWhenStopped);
        }
        update();
    }

    void setLevel(double level) {
        m_targetAudioLevel = std::clamp(level * 8.0, 0.0, 1.0);
    }

signals:
    void clicked();
    void positionChanged(int x, int y);

protected:
    void mousePressEvent(QMouseEvent* event) override {
        if (event->button() == Qt::MouseButton.LeftButton) {
            m_dragging = true;
            m_dragMoved = false;
            m_dragStartPos = event->globalPosition().toPoint() - frameGeometry().topLeft();
        }
    }

    void mouseMoveEvent(QMouseEvent* event) override {
        if (m_dragging) {
            QPoint newPos = event->globalPosition().toPoint() - m_dragStartPos;
            if ((newPos - pos()).manhattanLength() > 4) {
                m_dragMoved = true;
            }
            move(newPos);
            emit positionChanged(newPos.x(), newPos.y());
        }
    }

    void mouseReleaseEvent(QMouseEvent* event) override {
        if (event->button() == Qt::MouseButton.LeftButton) {
            m_dragging = false;
            if (!m_dragMoved) {
                emit clicked();
            }
        }
    }

    void paintEvent(QPaintEvent*) override {
        QPainter p(this);
        p.setRenderHint(QPainter.RenderHint.Antialiasing, true);
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, true);

        // Vector from pill center to active screen center
        QScreen* screen = QGuiApplication::screenAt(geometry().center());
        if (!screen) screen = QGuiApplication::primaryScreen();
        QPoint sCenter = screen->geometry().center();
        QPoint pCenter = geometry().center();
        double lightDx = sCenter.x() - pCenter.x();
        double lightDy = sCenter.y() - pCenter.y();

        // 1. Render Optical Liquid Glass Surface
        QImage glass = LiquidGlassShader::render(
            m_bgImage, width(), height(), m_audioLevel, m_animPhase, lightDx, lightDy, 2
        );
        p.drawImage(0, 0, glass);

        // 2. Draw Foreground Icons and Dynamic Equalizer
        drawGlyphs(p);
    }

private slots:
    void onVisTick() {
        m_audioLevel += (m_targetAudioLevel - m_audioLevel) * Theme::METER_SMOOTHING;
        m_animPhase += 0.05;
        update();
    }

    void onBackdropUpdate() {
        QScreen* screen = QGuiApplication::screenAt(geometry().center());
        if (screen) {
            QPixmap pix = screen->grabWindow(0, x(), y(), width(), height());
            m_bgImage = pix.toImage();
        }
    }

private:
    void drawGlyphs(QPainter& p) {
        int cx = width() / 2;
        int cy = height() / 2;

        if (m_state == "recording") {
            // Left Microphone + 5-Bar Equalizer
            drawMic(p, 24, cy, QColor(Theme::COLOR_RECORDING), 0.9);

            int startX = 46;
            int numBars = 5;
            int spacing = 12;
            p.setPen(Qt::PenStyle::NoPen);
            p.setBrush(QColor(Theme::COLOR_RECORDING));

            for (int i = 0; i < numBars; ++i) {
                int bx = startX + i * spacing;
                double phase = std::sin(m_animPhase * 2.0 + i * 1.2) * 0.35 + 0.65;
                int barH = static_cast<int>(std::clamp(4.0 + 24.0 * m_audioLevel * phase, 4.0, 32.0));
                p.drawRoundedRect(bx - 2, cy - barH / 2, 4, barH, 2, 2);
            }
        } else if (m_state == "transcribing") {
            // 3 Orbiting Breathing Dots
            p.setPen(Qt::PenStyle::NoPen);
            p.setBrush(QColor(Theme::COLOR_TRANSCRIBING));
            int offsets[3] = {-12, 0, 12};
            for (int i = 0; i < 3; ++i) {
                double wave = std::sin(m_animPhase * 2.5 + i * 1.2) * 0.5 + 0.5;
                double r = 2.5 + 2.0 * wave;
                p.drawEllipse(QPointF(cx + offsets[i], cy), r, r);
            }
        } else if (m_state == "injecting") {
            // Emerald Checkmark
            p.setPen(QPen(QColor(Theme::COLOR_INJECTING), 3.0, Qt::PenStyle::SolidLine, Qt::PenCapStyle::RoundCap, Qt::PenJoinStyle::RoundJoin));
            p.drawLine(QPointF(cx - 7, cy + 1), QPointF(cx - 2, cy + 6));
            p.drawLine(QPointF(cx - 2, cy + 6), QPointF(cx + 8, cy - 6));
        } else if (m_state == "error") {
            // Crimson Exclamation
            p.setPen(QPen(QColor(Theme::COLOR_ERROR), 3.0, Qt::PenStyle::SolidLine, Qt::PenCapStyle::RoundCap));
            p.drawLine(QPointF(cx, cy - 8), QPointF(cx, cy + 2));
            p.setPen(Qt::PenStyle::NoPen);
            p.setBrush(QColor(Theme::COLOR_ERROR));
            p.drawEllipse(QPointF(cx, cy + 7), 2.0, 2.0);
        } else {
            // Idle Centered Microphone
            drawMic(p, cx, cy, QColor(Theme::COLOR_IDLE), 1.0);
        }
    }

    void drawMic(QPainter& p, int cx, int cy, const QColor& color, double scale) {
        p.save();
        p.translate(cx, cy);
        p.scale(scale, scale);
        p.setPen(QPen(color, 2.2, Qt::PenStyle::SolidLine, Qt::PenCapStyle::RoundCap, Qt::PenJoinStyle::RoundJoin));
        p.setBrush(Qt::BrushStyle::NoBrush);

        p.drawRoundedRect(QRectF(-4.5, -9.0, 9.0, 13.0), 4.5, 4.5);
        p.drawArc(QRectF(-7.5, -4.5, 15.0, 11.0), 180 * 16, 180 * 16);
        p.drawLine(QPointF(0.0, 6.5), QPointF(0.0, 11.0));
        p.drawLine(QPointF(-4.5, 11.0), QPointF(4.5, 11.0));
        p.restore();
    }

    int m_width = Theme::WIDTH_IDLE;
    double m_shakeOffset = 0.0;
    QString m_state = "idle";
    QString m_detail = "";
    double m_audioLevel = 0.0;
    double m_targetAudioLevel = 0.0;
    double m_animPhase = 0.0;

    bool m_dragging = false;
    bool m_dragMoved = false;
    QPoint m_dragStartPos;

    QTimer* m_visTimer = nullptr;
    QTimer* m_bgTimer = nullptr;
    QImage m_bgImage;
};

} // namespace UI
} // namespace Dictate
