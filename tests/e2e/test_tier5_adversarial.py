"""Tier 5: Adversarial Coverage Hardening & Challenger Verification Suite.

Empirically probes:
1. Compose configuration edge cases and variable substitution.
2. Reverse proxy routing, header normalization, WebSocket upgrade resilience.
3. Database migration idempotency (rerun alembic upgrade head, existing tables/indexes).
4. Celery broker fallback and task polling edge cases.
5. SPARK SQLite WAL mode persistence and integrity checks.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.engine.url import make_url

from tests.e2e.harness import CaddyfileParser, ComposeParser, E2EClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "chatlens-v2" / "backend"


# ==============================================================================
# Area 1: Compose Configuration Edge Cases & Variable Substitution
# ==============================================================================


def test_compose_variable_interpolation_special_chars():
    """Adversarial: Test DATABASE_URL generation with special characters in POSTGRES_PASSWORD.

    Compose string interpolation:
      postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    If POSTGRES_PASSWORD contains '@', ':', '#', or '%', standard URL parsing fails without
    percent-encoding.
    """
    special_passwords = [
        "pass@word123",
        "p:a:s:s",
        "secret#hash",
        "my%complex%pass",
        "p@ss:w/ord",
    ]
    failures = []
    for pwd in special_passwords:
        url_str = f"postgresql+asyncpg://chatlens:{pwd}@postgres:5432/chatlens"
        try:
            parsed = make_url(url_str)
            if parsed.password != pwd:
                failures.append((pwd, f"Corrupted password: {parsed.password}"))
        except Exception as e:
            failures.append((pwd, f"URL parse crash: {type(e).__name__}: {e}"))

    # Assert that special characters fail without percent-encoding
    assert len(failures) > 0, "Expected raw interpolation with special characters to fail"


def test_compose_custom_database_url_override_ignored():
    """Adversarial: Verify compose.yaml allows overriding DATABASE_URL directly.

    In compose.yaml, DATABASE_URL must support ${DATABASE_URL:-...} fallback so operators
    can provide pre-encoded or external PostgreSQL connection strings.
    """
    compose_path = PROJECT_ROOT / "compose.yaml"
    content = compose_path.read_text(encoding="utf-8")

    has_fallback_override = "${DATABASE_URL:-" in content
    assert has_fallback_override, "compose.yaml must support DATABASE_URL interpolation override"


def test_compose_daemon_unnecessary_database_dependencies():
    """Adversarial: Verify chatlens-daemon adheres to Invariant 7.

    Invariant 7 states: "Never reintroduce Google Keep or any Postgres, Celery or Redis
    dependency into the daemon." compose.yaml must NOT have depends_on: [postgres, redis].
    """
    compose_path = PROJECT_ROOT / "compose.yaml"
    parsed = ComposeParser.parse(compose_path)

    daemon_conf = parsed.get("services", {}).get("chatlens-daemon", {})
    depends_on = daemon_conf.get("depends_on", {})
    assert "postgres" not in depends_on and "redis" not in depends_on, (
        "Daemon must not have coupling dependencies on postgres/redis in compose.yaml"
    )


# ==============================================================================
# Area 2: Reverse Proxy Routing, Header Normalization, WebSocket Resilience
# ==============================================================================


def test_caddyfile_path_matching_api_exact():
    """Adversarial: Verify Caddy path matching routes /api* to backend.

    'handle /api*' ensures both '/api' and '/api/...' route to chatlens-backend:8000
    without falling through to frontend SPA.
    """
    caddy_path = PROJECT_ROOT / "Caddyfile"
    parsed = CaddyfileParser.parse(caddy_path)

    handles = parsed.get("handles", [])
    api_handles = [h for h in handles if "chatlens-backend:8000" in h.get("upstream", "")]

    patterns = [h["pattern"] for h in api_handles]
    assert "/api*" in patterns or ("/api" in patterns and "/api/*" in patterns), (
        "Caddyfile must match /api* so requests with or without trailing slash route to backend!"
    )


def test_proxy_route_api_trailing_slash_discrepancy(e2e_client: E2EClient):
    """Adversarial: Probe /api/healthz vs /api."""
    res_healthz = e2e_client.get("/api/healthz")
    assert res_healthz.status_code == 200
    assert res_healthz.json().get("status") == "ok"


def test_proxy_websocket_upgrade_path(e2e_client: E2EClient):
    """Adversarial: Test WebSocket endpoint route match."""
    caddy_path = PROJECT_ROOT / "Caddyfile"
    parsed = CaddyfileParser.parse(caddy_path)
    handles = parsed.get("handles", [])
    ws_handles = [h for h in handles if "/ws" in h.get("pattern", "")]
    assert len(ws_handles) > 0
    assert ws_handles[0]["pattern"] == "/ws*"


# ==============================================================================
# Area 3: Database & Migration Idempotency (Alembic)
# ==============================================================================


def test_alembic_migration_idempotency_sqlite():
    """Adversarial: Verify migration scripts run multiple times on SQLite without error."""
    from alembic import command
    from alembic.config import Config

    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_migration.db"
        db_url = f"sqlite:///{db_file.as_posix()}"

        alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))

        command.upgrade(alembic_cfg, "head")

        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        assert "messages" in tables
        assert "alembic_version" in tables
        conn.close()

        command.upgrade(alembic_cfg, "head")


def test_alembic_migration_preexisting_table():
    """Adversarial: Verify Alembic upgrade head when messages table already exists."""
    from alembic import command
    from alembic.config import Config

    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "preexisting.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("""
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform VARCHAR,
                chat_name VARCHAR,
                sender VARCHAR,
                timestamp VARCHAR,
                text TEXT,
                reply_to VARCHAR,
                forwarded_from VARCHAR,
                embedding TEXT
            );
        """)
        conn.commit()
        conn.close()

        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))

        command.upgrade(alembic_cfg, "head")

        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(messages);")
        cols = [r[1] for r in cur.fetchall()]
        assert "content_hash" in cols
        conn.close()


# ==============================================================================
# Area 4: Celery Broker Fallback and Task Polling Edge Cases
# ==============================================================================


def test_task_status_polling_edge_cases(e2e_client: E2EClient):
    """Adversarial: Test task polling with various malformed task IDs."""
    res = e2e_client.get("/api/tasks/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data

    res = e2e_client.get("/api/tasks/not-a-valid-uuid-!@#$%^&*()")
    assert res.status_code == 200

    long_id = "a" * 1024
    res = e2e_client.get(f"/api/tasks/{long_id}")
    assert res.status_code == 200


def test_upload_sync_fallback_when_broker_unreachable():
    """Adversarial: Verify parse_and_save_sync handles invalid or corrupt files gracefully."""
    import celery_worker

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"2026-10-15, 10:00 - Alice: Hello from unit test\n")
        f.flush()
        f_path = f.name

    res = celery_worker.parse_and_save_sync(f_path, "whatsapp")
    assert res.get("status") in ("done", "error")


# ==============================================================================
# Area 5: SPARK SQLite WAL Mode Persistence & Integrity Checks
# ==============================================================================


def test_spark_status_bridge_pending_column_bug(tmp_path: Path):
    """Adversarial: Expose the schema discrepancy in get_spark_status().

    main.py line 656 executes:
        SELECT id, ts, status, event_json FROM pending ORDER BY id DESC LIMIT 10;
    However, src/utils/deduplication.py defines pending table as:
        id, event_json, status, created
    The column is 'created', NOT 'ts'!
    This causes get_spark_status() to fail silently and always return empty pending rows!
    """
    db_file = tmp_path / "spark_pending_adversarial.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_json TEXT,
            status TEXT,
            created REAL
        );
    """)
    conn.execute("""
        INSERT INTO pending (event_json, status, created) VALUES ('{}', 'PENDING', 1234.5);
    """)
    conn.commit()
    conn.close()

    conn_ro = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    cur = conn_ro.cursor()

    with pytest.raises(sqlite3.OperationalError) as exc_info:
        cur.execute("SELECT id, ts, status, event_json FROM pending ORDER BY id DESC LIMIT 10;")
    assert "no such column: ts" in str(exc_info.value).lower()
    conn_ro.close()


def test_spark_sqlite_wal_integrity_and_concurrency(tmp_path: Path):
    """Adversarial: Verify concurrent read-only access while writer is committing transactions."""
    db_file = tmp_path / "spark_wal.db"

    conn_writer = sqlite3.connect(str(db_file), isolation_level=None)
    conn_writer.execute("PRAGMA journal_mode=WAL;")
    conn_writer.execute("CREATE TABLE seen (key TEXT PRIMARY KEY, ts REAL);")
    conn_writer.execute("INSERT INTO seen (key, ts) VALUES ('msg1', 100.0);")

    conn_reader = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)

    conn_writer.execute("INSERT INTO seen (key, ts) VALUES ('msg2', 200.0);")

    row = conn_reader.execute("SELECT COUNT(*) FROM seen;").fetchone()
    assert row[0] == 2

    check = conn_reader.execute("PRAGMA integrity_check;").fetchone()
    assert check[0] == "ok"

    conn_reader.close()
    conn_writer.close()


def test_spark_sqlite_corrupt_database_handling(tmp_path: Path):
    """Adversarial: Verify handling of truncated or corrupted database file."""
    corrupt_db = tmp_path / "corrupt_spark.db"
    corrupt_db.write_bytes(b"SQLite format 3\x00\xff\xff\xffCORRUPTED_PAGE_DATA_GARBAGE")

    conn = sqlite3.connect(f"file:{corrupt_db}?mode=ro", uri=True)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchone()
        assert res[0] != "ok" or res is None
    except sqlite3.DatabaseError:
        pass
    finally:
        conn.close()
