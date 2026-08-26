@echo off
rem Launch Dictate without a console window.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" main.py
