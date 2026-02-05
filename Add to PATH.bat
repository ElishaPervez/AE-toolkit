@echo off
:: ═══════════════════════════════════════════════════════════════════════════════
:: AMV Toolkit - Add to PATH
:: This script adds AMV Toolkit to your system PATH for global access
:: ═══════════════════════════════════════════════════════════════════════════════

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Get the directory where this script is located
set "AMV_DIR=%~dp0"
:: Remove trailing backslash
set "AMV_DIR=%AMV_DIR:~0,-1%"

echo.
echo ═══════════════════════════════════════════════════════════════════
echo   AMV Toolkit - Add to System PATH
echo ═══════════════════════════════════════════════════════════════════
echo.
echo   Directory: %AMV_DIR%
echo.

:: Check if already in PATH
echo %PATH% | findstr /I /C:"%AMV_DIR%" >nul
if %errorLevel% equ 0 (
    echo   [!] AMV Toolkit is already in your PATH.
    echo.
    pause
    exit /b
)

:: Add to system PATH
echo   Adding to system PATH...
setx PATH "%PATH%;%AMV_DIR%" /M >nul 2>&1

if %errorLevel% equ 0 (
    echo.
    echo   [OK] Successfully added to PATH!
    echo.
    echo   You can now run 'amv' from any directory.
    echo   Please restart your terminal for changes to take effect.
    echo.
) else (
    echo.
    echo   [ERROR] Failed to add to PATH.
    echo   Try running as administrator.
    echo.
)

pause
