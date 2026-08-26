@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

echo ========================================================
echo   Compiling Dictate C++ Native Windows Direct2D App     
echo ========================================================

cd /d "c:\Dodo Drive\Hermes Agent\Projects\dictate\dictate_cpp"
if not exist bin mkdir bin

cl.exe /nologo /std:c++20 /O2 /W3 /EHsc src\dictate_win32.cpp /Fe:bin\dictate_cpp.exe /link /SUBSYSTEM:WINDOWS user32.lib gdi32.lib shell32.lib d2d1.lib dwrite.lib dxgi.lib

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   BUILD SUCCESSFUL! Built: bin\dictate_cpp.exe
    echo ========================================================
) else (
    echo.
    echo BUILD FAILED with error code %ERRORLEVEL%
)
