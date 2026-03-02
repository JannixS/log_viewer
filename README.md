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
