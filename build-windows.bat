@echo off
:: ============================================================
:: build-windows.bat — Build log-viewer.exe on Windows
:: Run this script from the project root (where app.py lives).
:: Requires: Python 3.10+ on PATH
:: ============================================================

echo [1/3] Installing build dependencies...
pip install pyinstaller pywin32 flask
if errorlevel 1 (
    echo ERROR: Failed to install build dependencies.
    exit /b 1
)

echo [2/3] Building standalone executable with PyInstaller...
python -m PyInstaller log_viewer.spec --noconfirm --clean

echo [3/3] Done.
echo.
echo  The standalone executable is at: dist\log-viewer.exe
echo.
echo  To install as a Windows service (run as Administrator):
echo    dist\log-viewer.exe install
echo    dist\log-viewer.exe start
echo.
echo  Or use install-service.bat for a guided setup.
