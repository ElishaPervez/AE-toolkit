@echo off
setlocal
:: ═══════════════════════════════════════════════════════════════════════════════
:: AMV Toolkit - Setup Wizard
:: ═══════════════════════════════════════════════════════════════════════════════

echo.
echo   Creating/Updating Virtual Environment...
if not exist .venv (
    python -m venv .venv
    echo   [OK] Virtual Environment created.
) else (
    echo   [!] Virtual Environment already exists.
)

echo.
echo   Installing Base Dependencies...
echo   [1/1] Installing requirements.txt...
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo   [SUCCESS] Setup complete!
echo   Device-specific PyTorch (CPU/GPU) is installed from the app:
echo   Settings ^> Check dependencies
echo   You can now run the toolkit using 'amv' or './amv.bat'
echo ═══════════════════════════════════════════════════════════════════════════════
echo.
pause
