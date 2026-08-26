#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <windowsx.h>
#include <shellapi.h>
#include <d2d1.h>
#include <dwrite.h>
#include <cmath>
#include <string>
#include <vector>
#include <algorithm>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "d2d1.lib")
#pragma comment(lib, "dwrite.lib")

// Window dimensions
constexpr int PILL_HEIGHT = 60;
constexpr int WIDTH_IDLE = 60;
constexpr int WIDTH_RECORDING = 120;
constexpr UINT WM_TRAYICON = WM_USER + 1;
constexpr UINT_PTR TIMER_ANIM = 1;

enum class PillState {
    Idle,
    Recording,
    Transcribing,
    Injecting,
    Error
};

class LiquidGlassPillApp {
public:
    HWND hwnd = NULL;
    NOTIFYICONDATA nid = {};
    ID2D1Factory* pD2DFactory = NULL;
    ID2D1HwndRenderTarget* pRenderTarget = NULL;
    IDWriteFactory* pDWriteFactory = NULL;

    PillState state = PillState::Idle;
    float currentWidth = static_cast<float>(WIDTH_IDLE);
    float targetWidth = static_cast<float>(WIDTH_IDLE);
    float animPhase = 0.0f;
    float audioLevel = 0.0f;
    bool isDragging = false;
    POINT dragOffset = {0, 0};

    static LiquidGlassPillApp* s_instance;

    LiquidGlassPillApp() {
        s_instance = this;
    }

    bool init(HINSTANCE hInstance, int nCmdShow) {
        // Initialize Direct2D & DirectWrite
        if (FAILED(D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, &pD2DFactory))) {
            return false;
        }
        if (FAILED(DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED, __uuidof(IDWriteFactory), reinterpret_cast<IUnknown**>(&pDWriteFactory)))) {
            return false;
        }

        // Register Window Class
        WNDCLASSEX wc = {sizeof(WNDCLASSEX)};
        wc.lpfnWndProc = WndProc;
        wc.hInstance = hInstance;
        wc.lpszClassName = L"DictateCppLiquidGlassClass";
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        RegisterClassEx(&wc);

        // Calculate initial centered position
        int screenW = GetSystemMetrics(SM_CXSCREEN);
        int screenH = GetSystemMetrics(SM_CYSCREEN);
        int initX = (screenW - WIDTH_IDLE) / 2;
        int initY = screenH - 140;

        hwnd = CreateWindowEx(
            WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TOOLWINDOW,
            wc.lpszClassName,
            L"Dictate C++",
            WS_POPUP,
            initX, initY, WIDTH_IDLE, PILL_HEIGHT,
            NULL, NULL, hInstance, NULL
        );

        if (!hwnd) return false;

        // Register Global Hotkey: Ctrl + Shift + P
        RegisterHotKey(hwnd, 1001, MOD_CONTROL | MOD_SHIFT, 'P');

        // Setup System Tray Icon
        nid.cbSize = sizeof(NOTIFYICONDATA);
        nid.hWnd = hwnd;
        nid.uID = 1;
        nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
        nid.uCallbackMessage = WM_TRAYICON;
        nid.hIcon = LoadIcon(NULL, IDI_APPLICATION);
        wcscpy_s(nid.szTip, L"Dictate (C++ Native 120 FPS)");
        Shell_NotifyIcon(NIM_ADD, &nid);

        // 120 FPS Timer
        SetTimer(hwnd, TIMER_ANIM, 8, NULL);

        ShowWindow(hwnd, nCmdShow);
        UpdateWindow(hwnd);
        return true;
    }

    void cleanup() {
        KillTimer(hwnd, TIMER_ANIM);
        UnregisterHotKey(hwnd, 1001);
        Shell_NotifyIcon(NIM_DELETE, &nid);

        if (pRenderTarget) { pRenderTarget->Release(); pRenderTarget = NULL; }
        if (pDWriteFactory) { pDWriteFactory->Release(); pDWriteFactory = NULL; }
        if (pD2DFactory) { pD2DFactory->Release(); pD2DFactory = NULL; }
    }

    void toggleRecording() {
        if (state == PillState::Idle) {
            state = PillState::Recording;
            targetWidth = static_cast<float>(WIDTH_RECORDING);
        } else if (state == PillState::Recording) {
            state = PillState::Injecting;
            targetWidth = static_cast<float>(WIDTH_IDLE);

            // Synthesize typing checkmark, then return to idle
            SetTimer(hwnd, 2001, 750, [](HWND h, UINT, UINT_PTR id, DWORD) {
                KillTimer(h, id);
                if (s_instance) {
                    s_instance->state = PillState::Idle;
                }
            });
        }
    }

    void render() {
        RECT rc;
        GetClientRect(hwnd, &rc);
        int w = rc.right - rc.left;
        int h = rc.bottom - rc.top;

        if (w <= 0 || h <= 0) return;

        // Animate width
        currentWidth += (targetWidth - currentWidth) * 0.22f;
        animPhase += 0.06f;

        if (std::abs(currentWidth - targetWidth) > 0.5f) {
            SetWindowPos(hwnd, NULL, 0, 0, static_cast<int>(currentWidth), PILL_HEIGHT, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
        }

        // Create RenderTarget if needed
        if (!pRenderTarget) {
            D2D1_SIZE_U size = D2D1::SizeU(w, h);
            pD2DFactory->CreateHwndRenderTarget(
                D2D1::RenderTargetProperties(D2D1_RENDER_TARGET_TYPE_DEFAULT, D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_PREMULTIPLIED)),
                D2D1::HwndRenderTargetProperties(hwnd, size),
                &pRenderTarget
            );
        }

        if (!pRenderTarget) return;

        pRenderTarget->BeginDraw();
        pRenderTarget->Clear(D2D1::ColorF(0, 0, 0, 0.0f));

        D2D1_ROUNDED_RECT roundedRect = D2D1::RoundedRect(
            D2D1::RectF(1.0f, 1.0f, static_cast<float>(w) - 1.0f, static_cast<float>(h) - 1.0f),
            static_cast<float>(h) / 2.0f,
            static_cast<float>(h) / 2.0f
        );

        // 1. Frosted Liquid Glass Body
        ID2D1SolidColorBrush* pBgBrush = NULL;
        pRenderTarget->CreateSolidColorBrush(D2D1::ColorF(0x0F, 0x17, 0x2A, 0.88f), &pBgBrush);

        ID2D1SolidColorBrush* pBorderBrush = NULL;
        pRenderTarget->CreateSolidColorBrush(D2D1::ColorF(0xFF, 0xFF, 0xFF, 0.20f), &pBorderBrush);

        if (pBgBrush && pBorderBrush) {
            pRenderTarget->FillRoundedRectangle(&roundedRect, pBgBrush);
            pRenderTarget->DrawRoundedRectangle(&roundedRect, pBorderBrush, 1.2f);
            pBgBrush->Release();
            pBorderBrush->Release();
        }

        // 2. State-Specific Glyphs and Equalizers
        float cx = w / 2.0f;
        float cy = h / 2.0f;

        if (state == PillState::Recording) {
            // Equalizer Bars in Rose Red
            ID2D1SolidColorBrush* pBarBrush = NULL;
            pRenderTarget->CreateSolidColorBrush(D2D1::ColorF(0xE1, 0x1D, 0x48, 1.0f), &pBarBrush);
            if (pBarBrush) {
                int numBars = 5;
                float startX = cx - 24.0f;
                for (int i = 0; i < numBars; ++i) {
                    float bx = startX + i * 12.0f;
                    float wave = std::sin(animPhase * 2.2f + i * 1.2f) * 0.5f + 0.5f;
                    float barH = 6.0f + 26.0f * wave;
                    D2D1_ROUNDED_RECT barRect = D2D1::RoundedRect(
                        D2D1::RectF(bx - 2.0f, cy - barH / 2.0f, bx + 2.0f, cy + barH / 2.0f),
                        2.0f, 2.0f
                    );
                    pRenderTarget->FillRoundedRectangle(&barRect, pBarBrush);
                }
                pBarBrush->Release();
            }
        } else if (state == PillState::Injecting) {
            // Emerald Checkmark
            ID2D1SolidColorBrush* pGreenBrush = NULL;
            pRenderTarget->CreateSolidColorBrush(D2D1::ColorF(0x16, 0xA3, 0x4A, 1.0f), &pGreenBrush);
            if (pGreenBrush) {
                pRenderTarget->DrawLine(D2D1::Point2F(cx - 7, cy + 1), D2D1::Point2F(cx - 2, cy + 6), pGreenBrush, 2.8f);
                pRenderTarget->DrawLine(D2D1::Point2F(cx - 2, cy + 6), D2D1::Point2F(cx + 8, cy - 6), pGreenBrush, 2.8f);
                pGreenBrush->Release();
            }
        } else {
            // Idle Microphone in Sapphire Blue
            ID2D1SolidColorBrush* pBlueBrush = NULL;
            pRenderTarget->CreateSolidColorBrush(D2D1::ColorF(0x02, 0x84, 0xC7, 1.0f), &pBlueBrush);
            if (pBlueBrush) {
                D2D1_ROUNDED_RECT micCapsule = D2D1::RoundedRect(
                    D2D1::RectF(cx - 4.5f, cy - 9.0f, cx + 4.5f, cy + 4.0f),
                    4.5f, 4.5f
                );
                pRenderTarget->DrawRoundedRectangle(&micCapsule, pBlueBrush, 2.2f);
                pRenderTarget->DrawLine(D2D1::Point2F(cx, cy + 6.0f), D2D1::Point2F(cx, cy + 11.0f), pBlueBrush, 2.2f);
                pRenderTarget->DrawLine(D2D1::Point2F(cx - 4.5f, cy + 11.0f), D2D1::Point2F(cx + 4.5f, cy + 11.0f), pBlueBrush, 2.2f);
                pBlueBrush->Release();
            }
        }

        pRenderTarget->EndDraw();
    }

    static LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam) {
        if (!s_instance) return DefWindowProc(hWnd, message, wParam, lParam);

        switch (message) {
        case WM_HOTKEY:
            if (wParam == 1001) {
                s_instance->toggleRecording();
            }
            break;

        case WM_TIMER:
            if (wParam == TIMER_ANIM) {
                s_instance->render();
            }
            break;

        case WM_LBUTTONDOWN:
            s_instance->isDragging = true;
            SetCapture(hWnd);
            GetCursorPos(&s_instance->dragOffset);
            RECT rect;
            GetWindowRect(hWnd, &rect);
            s_instance->dragOffset.x -= rect.left;
            s_instance->dragOffset.y -= rect.top;
            break;

        case WM_MOUSEMOVE:
            if (s_instance->isDragging) {
                POINT pt;
                GetCursorPos(&pt);
                SetWindowPos(hWnd, NULL, pt.x - s_instance->dragOffset.x, pt.y - s_instance->dragOffset.y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);
            }
            break;

        case WM_LBUTTONUP:
            if (s_instance->isDragging) {
                s_instance->isDragging = false;
                ReleaseCapture();
            }
            s_instance->toggleRecording();
            break;

        case WM_TRAYICON:
            if (lParam == WM_RBUTTONUP) {
                POINT curPoint;
                GetCursorPos(&curPoint);
                HMENU hMenu = CreatePopupMenu();
                InsertMenu(hMenu, 0, MF_BYPOSITION | MF_STRING, 201, L"Toggle Dictation (Ctrl+Shift+P)");
                InsertMenu(hMenu, 1, MF_BYPOSITION | MF_SEPARATOR, 0, NULL);
                InsertMenu(hMenu, 2, MF_BYPOSITION | MF_STRING, 202, L"Quit Dictate C++");

                SetForegroundWindow(hWnd);
                int cmd = TrackPopupMenu(hMenu, TPM_RETURNCMD | TPM_NONOTIFY, curPoint.x, curPoint.y, 0, hWnd, NULL);
                DestroyMenu(hMenu);

                if (cmd == 201) {
                    s_instance->toggleRecording();
                } else if (cmd == 202) {
                    PostQuitMessage(0);
                }
            } else if (lParam == WM_LBUTTONUP) {
                s_instance->toggleRecording();
            }
            break;

        case WM_DESTROY:
            PostQuitMessage(0);
            break;

        default:
            return DefWindowProc(hWnd, message, wParam, lParam);
        }
        return 0;
    }
};

LiquidGlassPillApp* LiquidGlassPillApp::s_instance = nullptr;

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR, int nCmdShow) {
    // Single instance mutex
    HANDLE hMutex = CreateMutex(NULL, TRUE, L"DictateCppSingleInstanceMutex");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        MessageBox(NULL, L"Dictate C++ is already running in your system tray!", L"Dictate C++", MB_ICONINFORMATION);
        return 0;
    }

    LiquidGlassPillApp app;
    if (!app.init(hInstance, nCmdShow)) {
        return 1;
    }

    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    app.cleanup();
    if (hMutex) CloseHandle(hMutex);
    return static_cast<int>(msg.wParam);
}
