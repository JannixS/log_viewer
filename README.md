# log_viewer

Java Log Viewer — a web application for browsing and analyzing logs from multiple Java applications.

## Running with Docker (recommended — no Python required)

The easiest way to run the app on any machine is with [Docker](https://docs.docker.com/get-docker/) (and optionally Docker Compose). No Python installation is needed on the host.

### Option A — Docker Compose (one command)

```bash
# 1. Place your log files under ./logs/<app-name>/<timestamp>.log
# 2. Start the app
docker compose up --build
```

Open <http://localhost:5000> in your browser.

To stop: `docker compose down`

### Option B — plain Docker

```bash
docker build -t log-viewer .
docker run -p 5000:5000 -v "$(pwd)/logs:/app/logs:ro" log-viewer
```

Open <http://localhost:5000> in your browser.

### Environment variables

| Variable      | Default     | Description                                   |
|---------------|-------------|-----------------------------------------------|
| `LOG_DIR`     | `/app/logs` | Path to the root log directory inside the container |
| `FLASK_DEBUG` | `0`         | Set to `1` to enable Flask debug mode (dev only) |

---

## Running as a Windows service (no Python, no Docker required)

Build a standalone `log-viewer.exe` on a Windows machine using PyInstaller.
The resulting file bundles Python, Flask, and all dependencies — nothing needs
to be installed on the target machine.

### Step 1 — Build the exe (one-time, on any Windows PC with Python)

```bat
build-windows.bat
```

This installs PyInstaller + pywin32, runs the build, and produces
`dist\log-viewer.exe` (~30 MB).

### Step 2 — Deploy to target machine

Copy the following files to any folder (e.g. `C:\LogViewer\`):

```
dist\log-viewer.exe
install-service.bat
uninstall-service.bat
logs\            ← your <app-name>\<timestamp>.log files go here
```

### Step 3 — Install and start the service (run as Administrator)

```bat
install-service.bat
```

This registers `LogViewerService` as a Windows service that **starts
automatically with Windows** and serves the UI at <http://localhost:5000>.

To use a custom log directory:

```bat
install-service.bat "D:\my-logs"
```

### Manage the service

| Action | Command (as Administrator) |
|---|---|
| Install & start | `install-service.bat` |
| Stop & remove | `uninstall-service.bat` |
| Start manually | `log-viewer.exe start` |
| Stop manually | `log-viewer.exe stop` |
| Test in foreground | `log-viewer.exe debug` |

---

## Running locally (requires Python 3.10+)

```bash
pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000>.

## Log directory structure

```
logs/
  my-service/
    2024-01-15_08-00-00.log
    2024-01-16_09-30-00.log
  another-service/
    2024-01-15_10-00-00.log
```

## Running tests

```bash
pip install -r requirements.txt pytest
pytest tests/
```
