#include <QApplication>
#include <QSystemTrayIcon>
#include <QMenu>
#include "config/settings.h"
#include "ui/pill.h"
#include "ui/settings_dialog.h"

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setQuitOnLastWindowClosed(false);

    Dictate::Config::Settings settings;

    // Floating Liquid Glass Pill
    Dictate::UI::Pill pill;
    if (settings.value("show_pill", true).toBool()) {
        pill.show();
    }

    // System Tray
    QSystemTrayIcon tray;
    tray.setIcon(QIcon("assets/icon32.png"));
    
    QMenu menu;
    auto* actSettings = menu.addAction("Preferences…");
    auto* actQuit = menu.addAction("Quit Dictate");

    QObject::connect(actSettings, &QAction::triggered, [&]() {
        Dictate::UI::SettingsDialog dlg(settings.data());
        if (dlg.exec() == QDialog::Accepted) {
            settings.load();
        }
    });

    QObject::connect(actQuit, &QAction::triggered, &app, &QCoreApplication::quit);

    tray.setContextMenu(&menu);
    tray.show();

    return app.exec();
}
