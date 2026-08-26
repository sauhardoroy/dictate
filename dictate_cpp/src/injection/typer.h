#pragma once
#include <windows.h>
#include <string>
#include <vector>
#include <QApplication>
#include <QClipboard>

namespace Dictate {
namespace Injection {

class Typer {
public:
    static bool pasteText(const std::string& text, int delayMs = 150, bool restoreClipboard = true) {
        if (text.empty()) return false;

        QClipboard* clipboard = QApplication::clipboard();
        QString originalClipboard = clipboard->text();

        // 1. Set text to Windows clipboard
        clipboard->setText(QString::fromStdString(text));
        Sleep(delayMs);

        // 2. Synthesize Ctrl+V keystroke via Win32 SendInput
        std::vector<INPUT> inputs(4);
        memset(inputs.data(), 0, sizeof(INPUT) * inputs.size());

        // Press Ctrl
        inputs[0].type = INPUT_KEYBOARD;
        inputs[0].ki.wVk = VK_CONTROL;

        // Press V
        inputs[1].type = INPUT_KEYBOARD;
        inputs[1].ki.wVk = 'V';

        // Release V
        inputs[2].type = INPUT_KEYBOARD;
        inputs[2].ki.wVk = 'V';
        inputs[2].ki.dwFlags = KEYEVENTF_KEYUP;

        // Release Ctrl
        inputs[3].type = INPUT_KEYBOARD;
        inputs[3].ki.wVk = VK_CONTROL;
        inputs[3].ki.dwFlags = KEYEVENTF_KEYUP;

        SendInput(static_cast<UINT>(inputs.size()), inputs.data(), sizeof(INPUT));

        // 3. Optional Clipboard Restoration
        if (restoreClipboard) {
            Sleep(delayMs);
            clipboard->setText(originalClipboard);
        }

        return true;
    }
};

} // namespace Injection
} // namespace Dictate
