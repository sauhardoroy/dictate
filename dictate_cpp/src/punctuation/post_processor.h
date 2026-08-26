#pragma once
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonDocument>
#include <QEventLoop>
#include <QString>
#include "semantic_vad.h"
#include "voice_commands.h"

namespace Dictate {
namespace Punctuation {

class PostProcessor {
public:
    static QString polish(
        const QString& rawText,
        bool enableAi = false,
        const QString& apiKey = "",
        const QString& baseUrl = "https://integrate.api.nvidia.com/v1",
        const QString& model = "nvidia/nemotron-3-nano-30b-a3b",
        bool enableVoiceCommands = true
    ) {
        if (rawText.trimmed().isEmpty()) return "";

        std::string processed = rawText.toStdString();

        // 1. Voice commands punctuation formatting
        if (enableVoiceCommands) {
            processed = apply_voice_commands(processed);
        }

        // 2. Optional NVIDIA AI Cloud Polish
        if (enableAi && !apiKey.trimmed().isEmpty()) {
            QString aiResult = requestNvidiaPolish(QString::fromStdString(processed), apiKey, baseUrl, model);
            if (!aiResult.trimmed().isEmpty()) {
                return aiResult;
            }
        }

        return QString::fromStdString(processed);
    }

private:
    static QString requestNvidiaPolish(
        const QString& text,
        const QString& apiKey,
        const QString& baseUrl,
        const QString& model
    ) {
        QNetworkAccessManager manager;
        QNetworkRequest request(QUrl(baseUrl + "/chat/completions"));
        request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
        request.setRawHeader("Authorization", QString("Bearer %1").arg(apiKey).toUtf8());
        request.setRawHeader("User-Agent", "Dictate-Cpp/2.0");

        QJsonObject root;
        root["model"] = model;
        root["temperature"] = 0.2;
        root["top_p"] = 0.7;
        root["max_tokens"] = 1024;

        QJsonArray messages;
        QJsonObject sysMsg;
        sysMsg["role"] = "system";
        sysMsg["content"] = "You are an expert dictation assistant. Clean up the raw speech transcript. Remove filler words (um, uh, like) and ensure perfect grammar and punctuation. Output ONLY the cleaned text and nothing else.";
        messages.append(sysMsg);

        QJsonObject userMsg;
        userMsg["role"] = "user";
        userMsg["content"] = text;
        messages.append(userMsg);

        root["messages"] = messages;

        QByteArray postData = QJsonDocument(root).toJson();
        QNetworkReply* reply = manager.post(request, postData);

        QEventLoop loop;
        QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
        loop.exec();

        if (reply->error() == QNetworkReply::NoError) {
            QJsonDocument resDoc = QJsonDocument::fromJson(reply->readAll());
            QJsonObject resObj = resDoc.object();
            QJsonArray choices = resObj["choices"].toArray();
            if (!choices.isEmpty()) {
                QString content = choices[0].toObject()["message"].toObject()["content"].toString();
                reply->deleteLater();
                return content.trimmed();
            }
        }

        reply->deleteLater();
        return text;
    }
};

} // namespace Punctuation
} // namespace Dictate
