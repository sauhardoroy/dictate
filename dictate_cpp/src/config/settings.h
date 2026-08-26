#pragma once
#include <QObject>
#include <QString>
#include <QJsonObject>
#include <QJsonDocument>
#include <QFile>
#include <QStandardPaths>
#include <QDir>

namespace Dictate {
namespace Config {

class Settings : public QObject {
    Q_OBJECT
public:
    explicit Settings(QObject* parent = nullptr) : QObject(parent) {
        load();
    }

    QString configPath() const {
        QString dir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
        QDir().mkpath(dir);
        return dir + "/settings.json";
    }

    void load() {
        QFile file(configPath());
        if (file.open(QIODevice::ReadOnly)) {
            QJsonDocument doc = QJsonDocument::fromJson(file.readAll());
            if (doc.isObject()) {
                m_data = doc.object();
            }
        }
        applyDefaults();
    }

    void save() {
        QFile file(configPath());
        if (file.open(QIODevice::WriteOnly)) {
            QJsonDocument doc(m_data);
            file.write(doc.toJson(QJsonDocument::Indented));
        }
    }

    void applyDefaults() {
        setDef("trigger_key", "ctrl+shift+p");
        setDef("mode", "toggle");
        setDef("engine", "whisper");
        setDef("model", "small.en");
        setDef("compute_type", "int8");
        setDef("device", "auto");
        setDef("cpu_threads", 0);
        setDef("initial_prompt", "");
        setDef("language", "en");
        setDef("vad_filter", true);
        setDef("auto_stop", true);
        setDef("vad_silence_seconds", 1.4);
        setDef("ai_polish", false);
        setDef("ai_polish_api_key", "");
        setDef("ai_polish_base_url", "https://integrate.api.nvidia.com/v1");
        setDef("ai_polish_model", "nvidia/nemotron-3-nano-30b-a3b");
        setDef("injection_delay_ms", 150);
        setDef("restore_clipboard", true);
        setDef("show_pill", true);
        setDef("autostart", false);
        setDef("voice_commands", true);
        setDef("pill_x", 800);
        setDef("pill_y", 300);
    }

    QJsonObject data() const { return m_data; }
    void setData(const QJsonObject& obj) {
        m_data = obj;
        save();
        emit settingsChanged();
    }

    QJsonValue value(const QString& key, const QJsonValue& def = QJsonValue()) const {
        return m_data.value(key).isUndefined() ? def : m_data.value(key);
    }

    void setValue(const QString& key, const QJsonValue& val) {
        m_data[key] = val;
        save();
        emit settingsChanged();
    }

signals:
    void settingsChanged();

private:
    void setDef(const QString& key, const QJsonValue& val) {
        if (!m_data.contains(key)) m_data[key] = val;
    }
    QJsonObject m_data;
};

} // namespace Config
} // namespace Dictate
