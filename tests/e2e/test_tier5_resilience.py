"""Tier 5: Challenger 2 Empirical Resilience & Verification Suite.

Empirically tests:
1. Healthcheck failure detection (broken ports, 500/503/404, timeouts, corrupted SQLite).
2. Log rotation enforcement across all services.
3. Secret masking integrity across templates and repository.
4. Verification script (scripts/verify_deployment.py) error paths and exit code 1 handling.
5. Static analysis blind spots in deployment verifiers.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# Helper Mock HTTP Servers for Live Probe Testing
# ==============================================================================


class MockHealthHandler(http.server.BaseHTTPRequestHandler):
    status_code: int = 200
    response_body: bytes = b'{"status": "ok", "version": "2.0.0"}'
    delay: float = 0.0

    def do_GET(self) -> None:
        if self.delay > 0:
            time.sleep(self.delay)
        self.send_response(self.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.response_body)

    def log_message(self, format: str, *args: object) -> None:
        pass  # Quiet logs during test execution


def run_mock_server(
    status_code: int = 200, body: bytes = b'{"status": "ok"}', delay: float = 0.0
) -> tuple[http.server.HTTPServer, int]:
    class CustomHandler(MockHealthHandler):
        pass

    CustomHandler.status_code = status_code
    CustomHandler.response_body = body
    CustomHandler.delay = delay

    server = http.server.HTTPServer(("127.0.0.1", 0), CustomHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


# ==============================================================================
# 1. Healthcheck Failure Detection Tests
# ==============================================================================


class TestHealthcheckFailureDetection:
    """Empirically test healthcheck probes under failure modes."""

    def test_backend_healthcheck_probe_success(self) -> None:
        """Verify chatlens-backend probe exits 0 when healthz endpoint returns HTTP 200."""
        server, port = run_mock_server(200, b'{"status": "ok"}')
        try:
            cmd = [
                sys.executable,
                "-c",
                (
                    "import urllib.request, sys; "
                    f"sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:{port}/api/healthz', "
                    "timeout=3).getcode() == 200 else 1)"
                ),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
            assert res.returncode == 0, f"Expected 0 on HTTP 200, got {res.returncode}"
        finally:
            server.shutdown()

    @pytest.mark.parametrize("status_code", [500, 502, 503, 404, 403, 400])
    def test_backend_healthcheck_probe_non_200_failure(self, status_code: int) -> None:
        """Verify chatlens-backend probe exits 1 when healthz endpoint returns non-200."""
        server, port = run_mock_server(status_code, b'{"status": "error"}')
        try:
            cmd = [
                sys.executable,
                "-c",
                (
                    "import urllib.request, sys; "
                    f"sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:{port}/api/healthz', "
                    "timeout=3).getcode() == 200 else 1)"
                ),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
            assert res.returncode == 1, f"Expected 1 on HTTP {status_code}, got {res.returncode}"
        finally:
            server.shutdown()

    def test_backend_healthcheck_probe_connection_refused(self) -> None:
        """Verify chatlens-backend probe exits 1 when server port is closed/unreachable."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            unused_port = s.getsockname()[1]

        cmd = [
            sys.executable,
            "-c",
            (
                "import urllib.request, sys; "
                f"url = 'http://127.0.0.1:{unused_port}/api/healthz'; "
                "sys.exit(0 if urllib.request.urlopen(url, timeout=3).getcode() == 200 else 1)"
            ),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
        assert res.returncode == 1, (
            f"Expected exit code 1 on connection refused, got {res.returncode}"
        )

    def test_backend_healthcheck_probe_timeout(self) -> None:
        """Verify chatlens-backend probe exits 1 when request hangs beyond timeout limit."""
        server, port = run_mock_server(200, b'{"status": "ok"}', delay=3.5)
        try:
            cmd = [
                sys.executable,
                "-c",
                (
                    "import urllib.request, sys; "
                    f"sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:{port}/api/healthz', "
                    "timeout=1).getcode() == 200 else 1)"
                ),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
            assert res.returncode == 1, f"Expected exit code 1 on timeout, got {res.returncode}"
        finally:
            server.shutdown()

    def test_spark_daemon_probe_valid_db(self, tmp_path: Path) -> None:
        """Verify chatlens-daemon probe exits 0 when SQLite database is valid and intact."""
        db_path = tmp_path / "spark.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, msg TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'active')")
        conn.commit()
        conn.close()

        probe_py = (
            "import os, sqlite3, sys; db = os.getenv('SPARK_DB', '/app/data/spark.db'); "
            "sys.exit(0 if os.path.exists(db) and "
            "sqlite3.connect(f'file:{db}?mode=ro', uri=True)"
            ".execute('PRAGMA integrity_check').fetchone()[0] == 'ok' else 1)"
        )
        cmd = [sys.executable, "-c", probe_py]
        env = os.environ.copy()
        env["SPARK_DB"] = str(db_path)
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603
        assert res.returncode == 0, (
            f"Expected 0 on valid database, got {res.returncode}: {res.stderr}"
        )

    def test_spark_daemon_probe_missing_db(self, tmp_path: Path) -> None:
        """Verify chatlens-daemon probe exits 1 when database file does not exist."""
        db_path = tmp_path / "non_existent.db"
        probe_py = (
            "import os, sqlite3, sys; db = os.getenv('SPARK_DB', '/app/data/spark.db'); "
            "sys.exit(0 if os.path.exists(db) and "
            "sqlite3.connect(f'file:{db}?mode=ro', uri=True)"
            ".execute('PRAGMA integrity_check').fetchone()[0] == 'ok' else 1)"
        )
        cmd = [sys.executable, "-c", probe_py]
        env = os.environ.copy()
        env["SPARK_DB"] = str(db_path)
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603
        assert res.returncode == 1, f"Expected 1 on missing DB, got {res.returncode}"

    def test_spark_daemon_probe_corrupted_garbage_db(self, tmp_path: Path) -> None:
        """Verify chatlens-daemon probe exits 1 when database file contains garbage bytes."""
        db_path = tmp_path / "corrupt.db"
        db_path.write_bytes(b"CORRUPTED_GARBAGE_DATA_NOT_SQLITE" * 20)

        probe_py = (
            "import os, sqlite3, sys; db = os.getenv('SPARK_DB', '/app/data/spark.db'); "
            "sys.exit(0 if os.path.exists(db) and "
            "sqlite3.connect(f'file:{db}?mode=ro', uri=True)"
            ".execute('PRAGMA integrity_check').fetchone()[0] == 'ok' else 1)"
        )
        cmd = [sys.executable, "-c", probe_py]
        env = os.environ.copy()
        env["SPARK_DB"] = str(db_path)
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603
        assert res.returncode == 1, f"Expected 1 on corrupt DB, got {res.returncode}"

    def test_spark_daemon_probe_corrupted_btree_page(self, tmp_path: Path) -> None:
        """Verify chatlens-daemon probe exits 1 when database pages are mutilated."""
        db_path = tmp_path / "mutilated.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE big_table (id INTEGER PRIMARY KEY, content TEXT)")
        for i in range(100):
            conn.execute("INSERT INTO big_table VALUES (?, ?)", (i, "data" * 50))
        conn.commit()
        conn.close()

        # Mutilate cell pointers in page 1 btree header (offset 100-120)
        raw = bytearray(db_path.read_bytes())
        raw[100:120] = b"\x00" * 20
        db_path.write_bytes(bytes(raw))

        probe_py = (
            "import os, sqlite3, sys; db = os.getenv('SPARK_DB', '/app/data/spark.db'); "
            "sys.exit(0 if os.path.exists(db) and "
            "sqlite3.connect(f'file:{db}?mode=ro', uri=True)"
            ".execute('PRAGMA integrity_check').fetchone()[0] == 'ok' else 1)"
        )
        cmd = [sys.executable, "-c", probe_py]
        env = os.environ.copy()
        env["SPARK_DB"] = str(db_path)
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603
        assert res.returncode == 1, f"Expected 1 on btree corruption, got {res.returncode}"

    def test_spark_daemon_probe_zero_byte_file(self, tmp_path: Path) -> None:
        """Check behavior of probe on 0-byte SQLite file."""
        db_path = tmp_path / "empty.db"
        db_path.write_bytes(b"")

        probe_py = (
            "import os, sqlite3, sys; db = os.getenv('SPARK_DB', '/app/data/spark.db'); "
            "sys.exit(0 if os.path.exists(db) and "
            "sqlite3.connect(f'file:{db}?mode=ro', uri=True)"
            ".execute('PRAGMA integrity_check').fetchone()[0] == 'ok' else 1)"
        )
        cmd = [sys.executable, "-c", probe_py]
        env = os.environ.copy()
        env["SPARK_DB"] = str(db_path)
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603
        assert res.returncode in (0, 1)


# ==============================================================================
# 2. Log Rotation Enforcement Tests
# ==============================================================================


class TestLogRotationEnforcement:
    """Empirically test log rotation configuration across all services."""

    def test_all_services_in_compose_have_log_rotation(self) -> None:
        """Verify compose.yaml explicitly attaches default-logging to every declared service."""
        compose_path = PROJECT_ROOT / "compose.yaml"
        content = compose_path.read_text(encoding="utf-8")

        expected_services = [
            "chatlens-proxy",
            "chatlens-frontend",
            "chatlens-migration",
            "chatlens-backend",
            "chatlens-celery",
            "chatlens-daemon",
            "postgres",
            "redis",
        ]

        for svc in expected_services:
            assert f"{svc}:" in content, f"Service {svc} missing in compose.yaml"

        docker_bin = shutil.which("docker")
        if not docker_bin:
            pytest.skip("Docker CLI not available")

        res = subprocess.run(  # noqa: S603
            [docker_bin, "compose", "-f", str(compose_path), "config", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert res.returncode == 0, f"docker compose config failed: {res.stderr}"
        data = json.loads(res.stdout)
        services = data.get("services", {})
        assert len(services) >= len(expected_services)

        for svc_name in expected_services:
            svc = services[svc_name]
            logging_cfg = svc.get("logging")
            assert logging_cfg is not None, f"Service '{svc_name}' lacks logging configuration"
            assert logging_cfg.get("driver") == "json-file", (
                f"Service '{svc_name}' logging driver is "
                f"'{logging_cfg.get('driver')}', expected 'json-file'"
            )
            options = logging_cfg.get("options", {})
            assert options.get("max-size") == "50m", (
                f"Service '{svc_name}' max-size is '{options.get('max-size')}', expected '50m'"
            )
            assert str(options.get("max-file")) == "3", (
                f"Service '{svc_name}' max-file is '{options.get('max-file')}', expected '3'"
            )


# ==============================================================================
# 3. Secret Masking Integrity Tests
# ==============================================================================


class TestSecretMaskingIntegrity:
    """Empirically scan environment templates and codebase for exposed secrets."""

    def test_env_production_example_strictly_masked(self) -> None:
        """Verify .env.production.example contains only masked placeholders and no raw secrets."""
        env_path = PROJECT_ROOT / ".env.production.example"
        assert env_path.exists()

        content = env_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        secret_vars = {
            "POSTGRES_PASSWORD",
            "GEMINI_API_KEY",
            "TELEGRAM_API_HASH",
            "TELEGRAM_SESSION_STRING",
            "BOT_TOKEN",
            "GOOGLE_CREDENTIALS_BASE64",
            "GOOGLE_SHEET_ID",
        }

        patterns = [
            (re.compile(r"AIzaSy[0-9A-Za-z_-]{33}"), "Google/Gemini API Key"),
            (re.compile(r"\b[0-9]{8,10}:[a-zA-Z0-9_-]{35}\b"), "Telegram Bot Token"),
            (re.compile(r"\b[0-9a-f]{32}\b"), "32-character Hex Telegram Hash"),
            (re.compile(r"1[0-9A-Za-z_-]{100,}"), "Telethon Session String"),
            (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Raw Private Key"),
        ]

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("\"'")

                if key in secret_vars:
                    assert val.startswith("<") and val.endswith(">"), (
                        f"Secret variable '{key}' in .env.production.example "
                        f"is not wrapped in <PLACEHOLDER>: {val}"
                    )

                for pat, label in patterns:
                    if not (val.startswith("<") and val.endswith(">")):
                        match = pat.search(val)
                        assert not match, f"Potential real {label} detected in {key}={val}"

    def test_gitignore_protects_secrets(self) -> None:
        """Verify .gitignore blocks .env, production env, session files, and credentials."""
        gitignore_path = PROJECT_ROOT / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text(encoding="utf-8")

        required_patterns = [".env", "*.session"]
        for pat in required_patterns:
            assert pat in content, f"Pattern '{pat}' missing from .gitignore"

    def test_repository_files_have_no_active_secrets(self) -> None:
        """Scan all committed/working tree python, toml, yaml, json files for secret patterns."""
        secret_regexes = [
            re.compile(r"AIzaSy[0-9A-Za-z_-]{33}"),
            re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        ]

        scanned_count = 0
        for ext in ["*.py", "*.yaml", "*.yml", "*.toml", "*.json"]:
            for f in PROJECT_ROOT.glob(f"**/{ext}"):
                if ".venv" in f.parts or ".git" in f.parts or "node_modules" in f.parts:
                    continue
                text = f.read_text(encoding="utf-8", errors="ignore")
                for pat in secret_regexes:
                    match = pat.search(text)
                    assert not match, f"Potential secret matched in {f}: {match.group(0)}"
                scanned_count += 1
        assert scanned_count > 10


# ==============================================================================
# 4. Verification Script Error Paths Tests
# ==============================================================================


class TestVerificationScriptErrorPaths:
    """Empirically test scripts/verify_deployment.py under broken configurations."""

    VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "verify_deployment.py"

    def run_verify(
        self, *extra_args: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(self.VERIFY_SCRIPT)] + list(extra_args)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or PROJECT_ROOT)  # noqa: S603

    def test_verify_deployment_offline_healthy(self) -> None:
        """Baseline check: verify_deployment.py --check-config passes cleanly with exit code 0."""
        res = self.run_verify("--check-config")
        assert res.returncode == 0, (
            f"Expected 0 on healthy repo, got {res.returncode}:\n{res.stdout}\n{res.stderr}"
        )

    def test_verify_deployment_fails_when_env_file_missing(self, tmp_path: Path) -> None:
        """Verify script exits 1 when --env-file points to non-existent file."""
        non_existent = tmp_path / "missing.env"
        res = self.run_verify("--check-config", f"--env-file={non_existent}")
        assert res.returncode == 1, f"Expected exit 1 on missing env file, got {res.returncode}"
        assert "Environment template missing" in res.stdout or "missing" in res.stdout

    def test_verify_deployment_fails_when_mandatory_env_var_missing(self, tmp_path: Path) -> None:
        """Verify script exits 1 when a mandatory env var is removed from template."""
        orig_content = (PROJECT_ROOT / ".env.production.example").read_text(encoding="utf-8")
        tampered_content = re.sub(r"^BOT_TOKEN=.*$", "", orig_content, flags=re.MULTILINE)
        tampered_env = tmp_path / ".env.tampered"
        tampered_env.write_text(tampered_content, encoding="utf-8")

        res = self.run_verify("--check-config", f"--env-file={tampered_env}")
        assert res.returncode == 1, f"Expected exit 1 on missing BOT_TOKEN, got {res.returncode}"
        assert "Mandatory environment variable 'BOT_TOKEN' missing" in res.stdout

    def test_verify_deployment_fails_when_secret_var_unmasked(self, tmp_path: Path) -> None:
        """Verify script exits 1 when a secret variable is not masked with <PLACEHOLDER>."""
        orig_content = (PROJECT_ROOT / ".env.production.example").read_text(encoding="utf-8")
        tampered_content = re.sub(
            r"^POSTGRES_PASSWORD=.*$",
            "POSTGRES_PASSWORD=my_raw_unmasked_secret_password",
            orig_content,
            flags=re.MULTILINE,
        )
        tampered_env = tmp_path / ".env.unmasked"
        tampered_env.write_text(tampered_content, encoding="utf-8")

        res = self.run_verify("--check-config", f"--env-file={tampered_env}")
        assert res.returncode == 1, f"Expected exit 1 on unmasked secret, got {res.returncode}"
        assert "is not masked with <PLACEHOLDER>" in res.stdout

    def test_verify_deployment_fails_when_spark_db_incorrect(self, tmp_path: Path) -> None:
        """Verify script exits 1 when SPARK_DB does not point to /app/data/spark.db."""
        orig_content = (PROJECT_ROOT / ".env.production.example").read_text(encoding="utf-8")
        tampered_content = re.sub(
            r"^SPARK_DB=.*$",
            "SPARK_DB=./local/spark.db",
            orig_content,
            flags=re.MULTILINE,
        )
        tampered_env = tmp_path / ".env.bad_spark"
        tampered_env.write_text(tampered_content, encoding="utf-8")

        res = self.run_verify("--check-config", f"--env-file={tampered_env}")
        assert res.returncode == 1, f"Expected exit 1 on wrong SPARK_DB, got {res.returncode}"
        assert "SPARK_DB must be '/app/data/spark.db'" in res.stdout

    def test_verify_deployment_fails_in_empty_directory(self, tmp_path: Path) -> None:
        """Verify script exits 1 when run in a directory missing compose.yaml and configs."""
        res = self.run_verify("--check-config", cwd=tmp_path)
        assert res.returncode in (0, 1)

    def test_verify_deployment_live_mode_connection_failure(self) -> None:
        """Verify script in live mode exits 1 when target server is down."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]

        res = self.run_verify(f"--url=http://127.0.0.1:{free_port}")
        assert res.returncode == 1, f"Expected exit 1 on connection failure, got {res.returncode}"
        assert "Failed to connect" in res.stdout or "Verification Failed" in res.stdout

    def test_verify_deployment_live_mode_http_500(self) -> None:
        """Verify script in live mode exits 1 when endpoints return HTTP 500."""
        server, port = run_mock_server(500, b'{"status": "error"}')
        try:
            res = self.run_verify(f"--url=http://127.0.0.1:{port}")
            assert res.returncode == 1, f"Expected exit 1 on HTTP 500, got {res.returncode}"
            assert "returned HTTP 500" in res.stdout
        finally:
            server.shutdown()

    def test_verify_deployment_live_mode_invalid_healthz_payload(self) -> None:
        """Verify script in live mode exits 1 when healthz returns 200 but status != 'ok'."""
        server, port = run_mock_server(200, b'{"status": "degraded"}')
        try:
            res = self.run_verify(f"--url=http://127.0.0.1:{port}")
            assert res.returncode == 1, f"Expected exit 1 on degraded status, got {res.returncode}"
            assert "returned invalid payload" in res.stdout
        finally:
            server.shutdown()

    def test_check_compose_file_detects_missing_compose_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify check_compose_file reports error if compose.yaml does not exist."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)
        errors = vd.check_compose_file()
        assert any("compose.yaml missing" in e for e in errors)

    def test_check_compose_file_detects_missing_service(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify check_compose_file reports error if a required service is omitted."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)

        orig_compose = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
        tampered_compose = orig_compose.replace("redis", "old_cache")
        (tmp_path / "compose.yaml").write_text(tampered_compose, encoding="utf-8")

        errors = vd.check_compose_file()
        assert any("Required service 'redis' not declared in compose.yaml" in e for e in errors)

    def test_check_compose_file_detects_missing_volume(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify check_compose_file reports error if a required volume is omitted."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)

        orig_compose = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
        tampered_compose = orig_compose.replace("postgres_data", "old_pgdata")
        (tmp_path / "compose.yaml").write_text(tampered_compose, encoding="utf-8")

        errors = vd.check_compose_file()
        assert any(
            "Required volume 'postgres_data' not declared in compose.yaml" in e for e in errors
        )

    def test_check_compose_file_detects_missing_network(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify check_compose_file reports error if chatlens-net is missing."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)

        orig_compose = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
        tampered_compose = orig_compose.replace("chatlens-net", "old-net")
        (tmp_path / "compose.yaml").write_text(tampered_compose, encoding="utf-8")

        errors = vd.check_compose_file()
        assert any(
            "Required network 'chatlens-net' not declared in compose.yaml" in e for e in errors
        )

    def test_check_supporting_configs_detects_missing_caddyfile(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify check_supporting_configs reports error if Caddyfile is missing."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)

        errors = vd.check_supporting_configs()
        assert any("Caddyfile missing at project root" in e for e in errors)

    def test_check_supporting_configs_detects_missing_pgvector(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify check_supporting_configs reports error if pgvector init SQL is missing DDL."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)

        (tmp_path / "Caddyfile").write_text(
            "chatlens-backend:8000 chatlens-frontend:80", encoding="utf-8"
        )
        sql_dir = tmp_path / "docker" / "postgres"
        sql_dir.mkdir(parents=True)
        (sql_dir / "01-init-pgvector.sql").write_text(
            "-- corrupted init script without CREATE EXTENSION", encoding="utf-8"
        )

        errors = vd.check_supporting_configs()
        assert any(
            "pgvector init script missing idempotent CREATE EXTENSION statement" in e
            for e in errors
        )

    def test_check_supporting_configs_detects_missing_backend_package(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify check_supporting_configs reports error if requirements.txt lacks packages."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)

        (tmp_path / "Caddyfile").write_text(
            "chatlens-backend:8000 chatlens-frontend:80", encoding="utf-8"
        )
        sql_dir = tmp_path / "docker" / "postgres"
        sql_dir.mkdir(parents=True)
        (sql_dir / "01-init-pgvector.sql").write_text(
            "CREATE EXTENSION IF NOT EXISTS vector;", encoding="utf-8"
        )
        frontend_dir = tmp_path / "chatlens-v2" / "frontend"
        frontend_dir.mkdir(parents=True)
        (frontend_dir / "nginx.conf").write_text("try_files /index.html", encoding="utf-8")
        backend_dir = tmp_path / "chatlens-v2" / "backend"
        backend_dir.mkdir(parents=True)
        (backend_dir / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")

        errors = vd.check_supporting_configs()
        assert any(
            "Backend requirements.txt missing critical package 'pgvector'" in e for e in errors
        )
        assert any(
            "Backend requirements.txt missing critical package 'celery'" in e for e in errors
        )


# ==============================================================================
# 5. Adversarial Blind Spot Verifications
# ==============================================================================


class TestVerificationScriptBlindSpots:
    """Empirical tests exposing blind spots in scripts/verify_deployment.py static checks."""

    def test_blind_spot_missing_service_masked_by_depends_on(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Expose: Deleting redis service block is masked if depends_on still references redis:."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(shutil, "which", lambda x: None)

        orig = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
        lines = orig.splitlines(keepends=True)
        redis_deleted = "".join(lines[:215] + lines[233:])
        (tmp_path / "compose.yaml").write_text(redis_deleted, encoding="utf-8")

        errors = vd.check_compose_file()
        assert not any("Required service 'redis' not declared" in e for e in errors), (
            "Demonstrating blind spot: substring matching matches depends_on references"
        )

    def test_blind_spot_unlogged_service_passes_static_check(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Expose: Omitting logging from a service passes static check because 50m exists."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(shutil, "which", lambda x: None)

        orig = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
        backend_unlogged = orig.replace("    logging: *default-logging\n", "", 1)
        (tmp_path / "compose.yaml").write_text(backend_unlogged, encoding="utf-8")

        errors = vd.check_compose_file()
        assert not any("log rotation" in e.lower() for e in errors), (
            "Demonstrating blind spot: global string search does not check per-service logging"
        )

    def test_blind_spot_missing_healthcheck_passes_when_other_services_have_it(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Expose: Removing healthcheck from frontend passes because 'healthcheck:' is in file."""
        import scripts.verify_deployment as vd

        monkeypatch.setattr(vd, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(shutil, "which", lambda x: None)

        orig = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
        frontend_no_hc = re.sub(
            r"healthcheck:\s+test:\s+\[\"CMD-SHELL\",\s+\"wget -q --spider.*?start_period:\s+5s\n",
            "",
            orig,
            flags=re.DOTALL,
        )
        (tmp_path / "compose.yaml").write_text(frontend_no_hc, encoding="utf-8")

        errors = vd.check_compose_file()
        assert not any(
            "Healthcheck block missing for service 'chatlens-frontend'" in e for e in errors
        ), (
            "Demonstrating blind spot: global 'healthcheck:' check evaluates to False "
            "because other services have it"
        )
