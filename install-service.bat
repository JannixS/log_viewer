@echo off
:: ============================================================
:: install-service.bat — Install and start the Log Viewer
:: Windows service.  Must be run as Administrator.
:: ============================================================

:: Default log directory: "logs" folder next to the exe
set "LOG_DIR=%~dp0logs"

:: Allow override via first argument
if not "%~1"=="" set "LOG_DIR=%~1"

echo Installing Java Log Viewer as a Windows service...
echo Log directory: %LOG_DIR%
echo.

:: Register the service
"%~dp0log-viewer.exe" install
if errorlevel 1 (
    echo ERROR: Could not install service. Make sure you are running as Administrator.
    exit /b 1
)

:: Set the LOG_DIR environment variable on the service
reg add "HKLM\SYSTEM\CurrentControlSet\Services\LogViewerService\Environment" /v "LOG_DIR" /t REG_SZ /d "%LOG_DIR%" /f
if errorlevel 1 (
    echo WARNING: Could not set LOG_DIR in registry. The service will use its default log directory.
)

:: Start the service
"%~dp0log-viewer.exe" start
if errorlevel 1 (
    echo ERROR: Service installed but could not be started.
    exit /b 1
)

echo.
echo  Java Log Viewer is running at http://localhost:5000
echo  The service starts automatically with Windows.
echo.
echo  To stop the service:   uninstall-service.bat
