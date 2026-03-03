"""
Windows Service wrapper for Java Log Viewer.

Usage (run as Administrator):
    log-viewer.exe install   -- register as a Windows service
    log-viewer.exe start     -- start the service
    log-viewer.exe stop      -- stop the service
    log-viewer.exe remove    -- uninstall the service
    log-viewer.exe debug     -- run in foreground (useful for testing)

The service starts the Flask app on http://localhost:5000.
Set the LOG_DIR environment variable on the service to point to your log
directory (defaults to a "logs" folder next to the executable).
"""

import sys
import os
import threading

import win32serviceutil  # pywin32
import win32service
import win32event
import servicemanager

# ---------------------------------------------------------------------------
# Locate bundled resources when running as a PyInstaller one-file exe
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # Running inside a PyInstaller bundle
    _BASE_DIR = sys._MEIPASS  # noqa: SLF001 – internal PyInstaller attr
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Make sure Flask can find the templates folder
os.environ.setdefault("FLASK_TEMPLATE_DIR", os.path.join(_BASE_DIR, "templates"))

# Default log directory: "logs" folder next to the exe (or script)
_EXE_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
os.environ.setdefault("LOG_DIR", os.path.join(_EXE_DIR, "logs"))
# Config file lives next to the exe so settings persist across service restarts
os.environ.setdefault("CONFIG_DIR", _EXE_DIR)


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

SERVICE_NAME = "LogViewerService"
SERVICE_DISPLAY_NAME = "Java Log Viewer"
SERVICE_DESCRIPTION = "Serves the Java Log Viewer web interface on http://localhost:5000"

_SERVER_LOCK = threading.Lock()
_server_instance = None  # holds the Werkzeug server once started


class LogViewerService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._server_thread = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self._stop_event)
        with _SERVER_LOCK:
            server = _server_instance
        if server is not None:
            server.shutdown()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self._run_flask()
        win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)
        # Wait for the server thread to finish (up to 10 s) for graceful shutdown
        if self._server_thread is not None:
            self._server_thread.join(timeout=10)

    def _run_flask(self):
        # Import here so the service can start before the app is fully loaded
        from app import app as flask_app  # noqa: PLC0415

        port = int(os.environ.get("PORT", 5000))

        def _serve():
            global _server_instance  # noqa: PLW0603
            from werkzeug.serving import make_server  # noqa: PLC0415

            server = make_server("0.0.0.0", port, flask_app)
            with _SERVER_LOCK:
                _server_instance = server
            try:
                server.serve_forever()
            finally:
                with _SERVER_LOCK:
                    _server_instance = None

        # Non-daemon thread so in-flight requests can complete on shutdown
        self._server_thread = threading.Thread(target=_serve, daemon=False)
        self._server_thread.start()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Called by the SCM (Service Control Manager) — hand off to pywin32
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(LogViewerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Called from command line: install / start / stop / remove / debug
        win32serviceutil.HandleCommandLine(LogViewerService)
