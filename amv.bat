@echo off
chcp 65001 >nul
set "AMV_ORIGINAL_DIR=%cd%"
pushd "%~dp0"
set "PATH=%~dp0.venv\Scripts;%PATH%"
.venv\Scripts\python.exe main.py %*
popd
