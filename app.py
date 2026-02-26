"""
Java Log Viewer - Flask web application for browsing and analyzing Java application logs.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request, abort

app = Flask(__name__)

# Base directory for log files; can be overridden via LOG_DIR environment variable.
LOG_DIR = Path(os.environ.get("LOG_DIR", os.path.join(os.path.dirname(__file__), "logs")))

# ---------------------------------------------------------------------------
# Log-level detection
# ---------------------------------------------------------------------------

LOG_LEVEL_RE = re.compile(
    r'\b(TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|SEVERE)\b',
    re.IGNORECASE,
)

EXCEPTION_RE = re.compile(
    r'([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*(?:Exception|Error|Throwable))',
)

STACKTRACE_LINE_RE = re.compile(r'^\s+at\s+|^\s*Caused by:|^\s*\.\.\.\s+\d+ more')


def detect_level(line: str) -> str:
    """Return the first log level keyword found in *line*, upper-cased."""
    match = LOG_LEVEL_RE.search(line)
    if match:
        level = match.group(1).upper()
        return "WARN" if level == "WARNING" else level
    if STACKTRACE_LINE_RE.match(line):
        return "ERROR"
    return "INFO"


def find_exceptions(line: str) -> list[str]:
    """Return all exception / error class names found in *line*."""
    return list(dict.fromkeys(EXCEPTION_RE.findall(line)))


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def _safe_path(app_name: str, filename: str | None = None) -> Path:
    """
    Resolve a log path and verify it stays within LOG_DIR to prevent path
    traversal attacks.
    """
    base = (LOG_DIR / app_name).resolve()
    if not str(base).startswith(str(LOG_DIR.resolve())):
        abort(400, description="Invalid application name.")
    if filename is None:
        return base
    full = (base / filename).resolve()
    if not str(full).startswith(str(base)):
        abort(400, description="Invalid filename.")
    return full


def list_apps() -> list[dict]:
    """Return all application directories inside LOG_DIR."""
    if not LOG_DIR.exists():
        return []
    apps = []
    for entry in sorted(LOG_DIR.iterdir()):
        if entry.is_dir() and not entry.name.startswith('.'):
            log_count = sum(1 for f in entry.iterdir() if f.is_file())
            apps.append({"name": entry.name, "log_count": log_count})
    return apps


def list_logs(app_name: str) -> list[dict]:
    """Return metadata for all log files of an application, newest first."""
    app_dir = _safe_path(app_name)
    if not app_dir.is_dir():
        abort(404, description=f"Application '{app_name}' not found.")
    files = []
    for f in sorted(app_dir.iterdir(), reverse=True):
        if f.is_file() and not f.name.startswith('.'):
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return files


def read_log(app_name: str, filename: str,
             level_filter: str | None = None,
             search: str | None = None,
             exception_filter: str | None = None,
             page: int = 1,
             per_page: int = 500) -> dict:
    """
    Read and filter a log file.

    Returns a dict with:
      - lines      : list of annotated line objects for the current page
      - total_lines: total number of matching lines
      - page       : current page
      - per_page   : lines per page
      - total_pages: total pages
      - exceptions : distinct exception types found across *all* matching lines
    """
    path = _safe_path(app_name, filename)
    if not path.is_file():
        abort(404, description="Log file not found.")

    level_upper = level_filter.upper() if level_filter else None
    search_lower = search.lower() if search else None
    exc_lower = exception_filter.lower() if exception_filter else None

    # Levels that are "at least" the requested level (ordered by severity)
    LEVEL_ORDER = ["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL", "SEVERE"]

    matched: list[dict] = []
    all_exceptions: set[str] = set()

    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for raw_lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.rstrip("\n\r")
                level = detect_level(line)
                exceptions_in_line = find_exceptions(line)
                all_exceptions.update(exceptions_in_line)

                # Level filter
                if level_upper and level_upper in LEVEL_ORDER:
                    min_idx = LEVEL_ORDER.index(level_upper)
                    cur_idx = LEVEL_ORDER.index(level) if level in LEVEL_ORDER else 0
                    if cur_idx < min_idx:
                        continue

                # Text search filter
                if search_lower and search_lower not in line.lower():
                    continue

                # Exception filter
                if exc_lower and not any(exc_lower in e.lower() for e in exceptions_in_line):
                    continue

                matched.append({
                    "lineno": raw_lineno,
                    "text": line,
                    "level": level,
                    "exceptions": exceptions_in_line,
                    "is_stacktrace": bool(STACKTRACE_LINE_RE.match(line)),
                })
    except OSError as exc:
        abort(500, description=f"Could not read log file: {exc}")

    total = len(matched)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    page_lines = matched[start: start + per_page]

    return {
        "lines": page_lines,
        "total_lines": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "exceptions": sorted(all_exceptions),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/apps")
def api_apps():
    return jsonify(list_apps())


@app.route("/api/apps/<app_name>/logs")
def api_logs(app_name: str):
    return jsonify(list_logs(app_name))


@app.route("/api/apps/<app_name>/logs/<path:filename>")
def api_log_content(app_name: str, filename: str):
    level = request.args.get("level") or None
    search = request.args.get("search") or None
    exception = request.args.get("exception") or None
    try:
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 500)), 2000)
    except ValueError:
        page, per_page = 1, 500

    data = read_log(app_name, filename, level, search, exception, page, per_page)
    return jsonify(data)


@app.route("/api/search")
def api_search():
    """Search across all applications and log files."""
    search = request.args.get("q", "").strip()
    level = request.args.get("level") or None
    exception = request.args.get("exception") or None
    if not search and not exception:
        return jsonify({"results": [], "total": 0})

    results = []
    for app_info in list_apps():
        for log_info in list_logs(app_info["name"]):
            data = read_log(
                app_info["name"],
                log_info["name"],
                level_filter=level,
                search=search or None,
                exception_filter=exception,
                page=1,
                per_page=100,
            )
            if data["total_lines"] > 0:
                results.append({
                    "app": app_info["name"],
                    "file": log_info["name"],
                    "match_count": data["total_lines"],
                    "sample_lines": data["lines"][:5],
                })

    return jsonify({"results": results, "total": sum(r["match_count"] for r in results)})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_error(exc):
    return jsonify({"error": str(exc.description)}), exc.code


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
