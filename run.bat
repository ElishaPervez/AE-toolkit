@echo off
REM AMV Toolkit - Quick Launcher
REM Activates venv and runs the TUI

cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py
