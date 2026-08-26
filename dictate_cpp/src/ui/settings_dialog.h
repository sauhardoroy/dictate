#pragma once
#include <QDialog>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QComboBox>
#include <QLineEdit>
#include <QCheckBox>
#include <QDoubleSpinBox>
#include <QStackedWidget>
#include <QPropertyAnimation>
#include <QGraphicsOpacityEffect>
#include <QPainter>
#include <QPainterPath>
#include <QFrame>
#include <QEasingCurve>
#include <QJsonObject>

namespace Dictate {
namespace UI {

class SegmentedNavBar : public QWidget {
    Q_OBJECT
    Q_PROPERTY(float indicatorProgress READ getIndicatorProgress WRITE setIndicatorProgress)

public:
    explicit SegmentedNavBar(const QStringList& labels, QWidget* parent = nullptr)
        : QWidget(parent), m_labels(labels) {
        setFixedHeight(38);
        setCursor(Qt::CursorShape.PointingHandCursor);

        m_anim = new QPropertyAnimation(this, "indicatorProgress", this);
        m_anim->setDuration(180);
        m_anim->setEasingCurve(QEasingCurve::Type::OutCubic);
    }

    float getIndicatorProgress() const { return m_indicatorX; }
    void setIndicatorProgress(float x) { m_indicatorX = x; update(); }

    void setCurrentIndex(int idx) {
        if (idx >= 0 && idx < m_labels.size() && idx != m_currentIndex) {
            m_currentIndex = idx;
            float pad = 3.0f;
            float tabW = (width() - pad * 2.0f) / m_labels.size();
            m_anim->stop();
            m_anim->setStartValue(m_indicatorX);
            m_anim->setEndValue(pad + idx * tabW);
            m_anim->start();
            emit currentChanged(idx);
        }
    }

signals:
    void currentChanged(int index);

protected:
    void mousePressEvent(QMouseEvent* event) override {
        float pad = 3.0f;
        float tabW = (width() - pad * 2.0f) / m_labels.size();
        int clicked = static_cast<int>((event->position().x() - pad) / tabW);
        setCurrentIndex(std::clamp(clicked, 0, m_labels.size() - 1));
    }

    void paintEvent(QPaintEvent*) override {
        QPainter p(this);
        p.setRenderHint(QPainter.RenderHint.Antialiasing, true);

        // Track
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0));
        p.setBrush(QColor(30, 41, 59, 160));
        p.drawRoundedRect(QRectF(0.5, 0.5, width() - 1.0, height() - 1.0), 8.0, 8.0);

        // Indicator
        float pad = 3.0f;
        float tabW = (width() - pad * 2.0f) / m_labels.size();
        QRectF pillRect(m_indicatorX + 1.0f, 3.0f, tabW - 2.0f, height() - 6.0f);
        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0));
        p.setBrush(QColor(255, 255, 255, 28));
        p.drawRoundedRect(pillRect, 6.0, 6.0);

        // Labels
        QFont f = p.font();
        f.setPointSize(10);
        f.setWeight(QFont.Weight.DemiBold);
        p.setFont(f);

        for (int i = 0; i < m_labels.size(); ++i) {
            QRectF r(pad + i * tabW, 0, tabW, height());
            p.setPen(QColor(i == m_currentIndex ? "#FFFFFF" : "#94A3B8"));
            p.drawText(r, Qt::AlignmentFlag.AlignCenter, m_labels[i]);
        }
    }

private:
    QStringList m_labels;
    int m_currentIndex = 0;
    float m_indicatorX = 3.0f;
    QPropertyAnimation* m_anim = nullptr;
};

class SettingsDialog : public QDialog {
    Q_OBJECT
public:
    explicit SettingsDialog(const QJsonObject& settings, QWidget* parent = nullptr) : QDialog(parent) {
        setWindowTitle("Dictate Settings");
        setFixedSize(580, 560);
        setStyleSheet("background-color: #0F172A; color: #F8FAFC;");

        auto* root = new QVBoxLayout(this);
        root->setContentsMargins(24, 22, 24, 20);
        root->setSpacing(16);

        // Header
        auto* lblTitle = new QLabel("Settings", this);
        lblTitle->setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: 700;");
        root->addWidget(lblTitle);

        // Nav
        auto* nav = new SegmentedNavBar({"Dictation", "Speech Model", "Microphone", "Behavior", "AI Polish"}, this);
        root->addWidget(nav);

        // Pages
        auto* stack = new QStackedWidget(this);
        root->addWidget(stack, 1);
        connect(nav, &SegmentedNavBar::currentChanged, stack, &QStackedWidget::setCurrentIndex);

        // Save / Cancel
        auto* btnBox = new QHBoxLayout();
        btnBox->addStretch();
        auto* btnCancel = new QPushButton("Cancel", this);
        connect(btnCancel, &QPushButton::clicked, this, &QDialog::reject);
        btnBox->addWidget(btnCancel);

        auto* btnSave = new QPushButton("Save Changes", this);
        btnSave->setStyleSheet("background-color: #0284C7; color: white; border-radius: 6px; padding: 6px 16px; font-weight: 600;");
        connect(btnSave, &QPushButton::clicked, this, &QDialog::accept);
        btnBox->addWidget(btnSave);

        root->addLayout(btnBox);
    }
};

} // namespace UI
} // namespace Dictate
