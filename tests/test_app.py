"""
Tests for the Java Log Viewer Flask application.
"""

import os
import sys
import pytest

# Make sure the repo root is on the path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as log_app  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    """Flask test client backed by a temporary log directory."""
    app_dir = tmp_path / "my-app"
    app_dir.mkdir()

    log1 = app_dir / "2024-01-15_10-00-00.log"
    log1.write_text(
        "2024-01-15 10:00:01.000 [main] INFO  c.example.App - Application started\n"
        "2024-01-15 10:01:00.000 [exec-1] WARN  c.example.App - Low memory\n"
        "2024-01-15 10:02:00.000 [exec-2] ERROR c.example.App - Unhandled exception\n"
        "java.lang.NullPointerException: something was null\n"
        "\tat c.example.App.process(App.java:42)\n"
        "2024-01-15 10:03:00.000 [exec-3] DEBUG c.example.App - Debug message\n",
        encoding="utf-8",
    )

    log2 = app_dir / "2024-01-16_08-00-00.log"
    log2.write_text(
        "2024-01-16 08:00:01.000 [main] INFO  c.example.App - Application started\n"
        "2024-01-16 08:05:00.000 [exec-1] ERROR c.example.App - DB connection failed\n"
        "java.sql.SQLException: Connection pool exhausted\n"
        "\tat com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:213)\n",
        encoding="utf-8",
    )

    original = log_app.LOG_DIR
    log_app.LOG_DIR = tmp_path
    log_app.app.config["TESTING"] = True

    with log_app.app.test_client() as c:
        yield c

    log_app.LOG_DIR = original


# ---------------------------------------------------------------------------
# /api/apps
# ---------------------------------------------------------------------------

class TestListApps:
    def test_returns_list(self, client):
        r = client.get("/api/apps")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "my-app"
        assert data[0]["log_count"] == 2

    def test_empty_when_no_apps(self, client, tmp_path):
        empty = tmp_path / "empty_logs"
        empty.mkdir()
        original = log_app.LOG_DIR
        log_app.LOG_DIR = empty
        r = client.get("/api/apps")
        log_app.LOG_DIR = original
        assert r.status_code == 200
        assert r.get_json() == []


# ---------------------------------------------------------------------------
# /api/apps/<app>/logs
# ---------------------------------------------------------------------------

class TestListLogs:
    def test_returns_files_newest_first(self, client):
        r = client.get("/api/apps/my-app/logs")
        assert r.status_code == 200
        files = r.get_json()
        assert len(files) == 2
        assert files[0]["name"] == "2024-01-16_08-00-00.log"
        assert files[1]["name"] == "2024-01-15_10-00-00.log"
        assert "size" in files[0]
        assert "modified" in files[0]

    def test_unknown_app_returns_404(self, client):
        r = client.get("/api/apps/nonexistent/logs")
        assert r.status_code == 404

    def test_path_traversal_rejected(self, client):
        r = client.get("/api/apps/../../../etc/logs")
        assert r.status_code in (400, 404)


# ---------------------------------------------------------------------------
# /api/apps/<app>/logs/<file>
# ---------------------------------------------------------------------------

class TestLogContent:
    def test_returns_all_lines(self, client):
        r = client.get("/api/apps/my-app/logs/2024-01-15_10-00-00.log")
        assert r.status_code == 200
        data = r.get_json()
        assert data["total_lines"] == 6
        assert len(data["lines"]) == 6

    def test_level_filter_error_only(self, client):
        r = client.get("/api/apps/my-app/logs/2024-01-15_10-00-00.log?level=ERROR")
        assert r.status_code == 200
        data = r.get_json()
        levels = {l["level"] for l in data["lines"]}
        assert levels <= {"ERROR", "WARN", "FATAL", "SEVERE"}

    def test_level_filter_warn_includes_error(self, client):
        r = client.get("/api/apps/my-app/logs/2024-01-15_10-00-00.log?level=WARN")
        assert r.status_code == 200
        data = r.get_json()
        line_texts = [l["text"] for l in data["lines"]]
        assert any("WARN" in t for t in line_texts)
        assert any("ERROR" in t for t in line_texts)
        assert not any("INFO" in t and "started" in t.lower() for t in line_texts)

    def test_text_search(self, client):
        r = client.get("/api/apps/my-app/logs/2024-01-15_10-00-00.log?search=memory")
        assert r.status_code == 200
        data = r.get_json()
        assert data["total_lines"] == 1
        assert "memory" in data["lines"][0]["text"].lower()

    def test_exception_filter(self, client):
        r = client.get(
            "/api/apps/my-app/logs/2024-01-15_10-00-00.log?exception=NullPointerException"
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["total_lines"] >= 1
        assert any("NullPointerException" in l["text"] for l in data["lines"])

    def test_exceptions_list_in_response(self, client):
        r = client.get("/api/apps/my-app/logs/2024-01-15_10-00-00.log")
        assert r.status_code == 200
        data = r.get_json()
        assert "java.lang.NullPointerException" in data["exceptions"]

    def test_pagination(self, client):
        r = client.get(
            "/api/apps/my-app/logs/2024-01-15_10-00-00.log?per_page=2&page=1"
        )
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["lines"]) == 2
        assert data["total_pages"] == 3
        assert data["page"] == 1

    def test_unknown_file_returns_404(self, client):
        r = client.get("/api/apps/my-app/logs/does_not_exist.log")
        assert r.status_code == 404

    def test_stacktrace_lines_flagged(self, client):
        r = client.get("/api/apps/my-app/logs/2024-01-15_10-00-00.log")
        assert r.status_code == 200
        stacktrace_lines = [l for l in r.get_json()["lines"] if l["is_stacktrace"]]
        assert len(stacktrace_lines) >= 1


# ---------------------------------------------------------------------------
# /api/search
# ---------------------------------------------------------------------------

class TestGlobalSearch:
    def test_search_finds_match(self, client):
        r = client.get("/api/search?q=Application+started")
        assert r.status_code == 200
        data = r.get_json()
        assert data["total"] >= 2
        assert any(res["app"] == "my-app" for res in data["results"])

    def test_search_exception(self, client):
        r = client.get("/api/search?exception=NullPointerException")
        assert r.status_code == 200
        data = r.get_json()
        assert data["total"] >= 1

    def test_empty_search_returns_empty(self, client):
        r = client.get("/api/search")
        assert r.status_code == 200
        assert r.get_json()["results"] == []

    def test_no_match_returns_empty(self, client):
        r = client.get("/api/search?q=XYZ_DOES_NOT_EXIST_ANYWHERE")
        assert r.status_code == 200
        assert r.get_json()["total"] == 0


# ---------------------------------------------------------------------------
# detect_level helper
# ---------------------------------------------------------------------------

class TestDetectLevel:
    def test_info(self):
        assert log_app.detect_level("2024-01-15 10:00:00 INFO  c.example.App - started") == "INFO"

    def test_warn(self):
        assert log_app.detect_level("2024-01-15 10:00:00 WARN  c.example.App - slow") == "WARN"

    def test_warning_normalized(self):
        assert log_app.detect_level("2024-01-15 10:00:00 WARNING slow response") == "WARN"

    def test_error(self):
        assert log_app.detect_level("2024-01-15 10:00:00 ERROR c.example.App - fail") == "ERROR"

    def test_debug(self):
        assert log_app.detect_level("2024-01-15 10:00:00 DEBUG c.example.App - trace") == "DEBUG"

    def test_stacktrace_line(self):
        assert log_app.detect_level("\tat c.example.App.process(App.java:42)") == "ERROR"

    def test_caused_by_line(self):
        assert log_app.detect_level("Caused by: java.io.IOException: broken pipe") == "ERROR"

    def test_default_is_info(self):
        assert log_app.detect_level("some generic log line without level") == "INFO"


# ---------------------------------------------------------------------------
# find_exceptions helper
# ---------------------------------------------------------------------------

class TestFindExceptions:
    def test_finds_null_pointer(self):
        line = "java.lang.NullPointerException: Cannot invoke method"
        assert "java.lang.NullPointerException" in log_app.find_exceptions(line)

    def test_finds_multiple(self):
        line = "Caused by: java.io.IOException wrapping java.sql.SQLException"
        excs = log_app.find_exceptions(line)
        assert "java.io.IOException" in excs
        assert "java.sql.SQLException" in excs

    def test_no_exception(self):
        assert log_app.find_exceptions("INFO Application started normally") == []

    def test_deduplicated(self):
        line = "NullPointerException ... NullPointerException"
        excs = log_app.find_exceptions(line)
        assert excs.count("NullPointerException") == 1
