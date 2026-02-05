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
echo   Installing Dependencies (CPU Optimized)...
echo   [1/2] Installing base requirements...
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo   [2/2] Installing CPU-optimized PyTorch...
echo   (This may take a moment but is faster than the GPU version)
.venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --upgrade

echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo   [SUCCESS] Setup complete!
echo   You can now run the toolkit using 'amv' or './amv.bat'
echo ═══════════════════════════════════════════════════════════════════════════════
echo.
pause
