@echo off
:: ============================================================
:: uninstall-service.bat — Stop and remove the Log Viewer
:: Windows service.  Must be run as Administrator.
:: ============================================================

echo Stopping Java Log Viewer service...
"%~dp0log-viewer.exe" stop

echo Removing Java Log Viewer service...
"%~dp0log-viewer.exe" remove

echo.
echo  Java Log Viewer service has been removed.
