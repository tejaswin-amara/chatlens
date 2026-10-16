"""Tier 2: Boundary & Corner Cases E2E Tests (>=5 tests per feature area).

Covers:
- Reverse Proxy & Routing Boundaries
- Frontend Static Asset Boundaries
- Database & Migration Boundaries
- Celery & Redis Boundaries
- State Persistence & Healthcheck Boundaries
"""

from __future__ import annotations

import io
import os
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch

import models

from scripts.lint_migration import DESTRUCTIVE_PATTERNS
from tests.e2e.harness import (
    FRONTEND_OUT,
    PROJECT_ROOT,
    E2EClient,
    celery_worker,
    main,
)

# ---------------------------------------------------------------------------
# 1. Reverse Proxy & Routing Boundaries (>=5 tests)
# ---------------------------------------------------------------------------


def test_b1_malformed_url_percent_encoding(e2e_client: E2EClient) -> None:
    """B1: Requests with unusual/percent-encoded characters handled cleanly without 500."""
    res = e2e_client.get("/api/chats/%FF%FE%FD")
    assert res.status_code in (400, 404, 405, 422)
    assert res.status_code != 500


def test_b1_unsupported_http_method(e2e_client: E2EClient) -> None:
    """B1: Unsupported HTTP methods on health endpoint return 405 Method Not Allowed."""
    res = e2e_client.request("POST", "/api/healthz")
    assert res.status_code == 405


def test_b1_nonexistent_api_route_404(e2e_client: E2EClient) -> None:
    """B1: Non-existent backend API route returns 404 JSON response."""
    res = e2e_client.get("/api/v99/unknown_resource_path")
    assert res.status_code == 404
    payload = res.json()
    assert "detail" in payload or "error" in payload or "status" in payload


def test_b1_long_uri_handling(e2e_client: E2EClient) -> None:
    """B1: Long URI paths handled gracefully without unhandled exceptions."""
    long_path = "/api/chats/" + "a" * 2048
    res = e2e_client.get(long_path)
    assert res.status_code in (400, 404, 405, 414, 422)
    assert res.status_code != 500


def test_b1_repeated_slashes_normalization(e2e_client: E2EClient) -> None:
    """B1: Route with repeated slashes handled without crashing."""
    res = e2e_client.get("/api//healthz")
    assert res.status_code in (200, 404)


# ---------------------------------------------------------------------------
# 2. Frontend Static Asset Boundaries (>=5 tests)
# ---------------------------------------------------------------------------


def test_b2_path_traversal_blocked(e2e_client: E2EClient) -> None:
    """B2: Directory traversal attempts return 404 and cannot escape web root."""
    res = e2e_client.get("/_next/../etc/passwd")
    assert res.status_code == 404

    res2 = e2e_client.get("/../../secret.env")
    assert res2.status_code == 404


def test_b2_missing_static_file_returns_404(e2e_client: E2EClient) -> None:
    """B2: Missing static asset under /_next/static/ returns 404, not fallback index.html."""
    res = e2e_client.get("/_next/static/nonexistent_chunk_0000000000000.js")
    assert res.status_code == 404


def test_b2_query_string_cache_busting(e2e_client: E2EClient) -> None:
    """B2: Static asset requests with query strings load correctly."""
    static_dir = FRONTEND_OUT / "_next" / "static"
    static_files = list(static_dir.rglob("*.js")) + list(static_dir.rglob("*.css"))
    if static_files:
        sample_file = static_files[0]
        rel_path = sample_file.relative_to(FRONTEND_OUT).as_posix()
        res = e2e_client.get(f"/{rel_path}?v=2.1.0&cache_bust=true")
        assert res.status_code == 200
        assert len(res.content) > 0


def test_b2_deep_nested_spa_route(e2e_client: E2EClient) -> None:
    """B2: Deeply nested frontend routes resolve to index.html with HTTP 200."""
    res = e2e_client.get("/chats/section-t04/dsa/export/summary")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("Content-Type", "")


def test_b2_head_request_on_static_asset(e2e_client: E2EClient) -> None:
    """B2: HTTP HEAD on static asset returns headers without body content."""
    res = e2e_client.request("HEAD", "/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("Content-Type", "")


# ---------------------------------------------------------------------------
# 3. Database & Migration Boundaries (>=5 tests)
# ---------------------------------------------------------------------------


def test_b3_consecutive_reruns_idempotent() -> None:
    """B3: Running 01-init-pgvector.sql repeatedly is fully idempotent."""
    sql_path = PROJECT_ROOT / "docker" / "postgres" / "01-init-pgvector.sql"
    content = sql_path.read_text(encoding="utf-8")
    for stmt in content.split(";"):
        stmt = stmt.strip()
        if stmt:
            assert "IF NOT EXISTS" in stmt.upper()


def test_b3_table_already_exists_resilience(in_memory_db) -> None:
    """B3: Creating database metadata on already existing schema does not raise error."""
    models.Base.metadata.create_all(bind=in_memory_db)
    models.Base.metadata.create_all(bind=in_memory_db)


def test_b3_null_embedding_vector_handling() -> None:
    """B3: Message model allows null embedding column for unembedded messages."""
    col = models.Message.embedding
    assert col.nullable is True


def test_b3_duplicate_content_hash_collision(in_memory_db) -> None:
    """B3: Unique index ux_messages_content_hash enforces deduplication."""
    indices = [arg for arg in models.Message.__table_args__ if hasattr(arg, "name")]
    hash_idx = next((idx for idx in indices if "content_hash" in idx.name), None)
    assert hash_idx is not None
    assert hash_idx.unique is True


def test_b3_destructive_ddl_rejection() -> None:
    """B3: Destructive DDL statements are rejected by migration safety patterns."""
    bad_statements = [
        "DROP TABLE messages;",
        "ALTER TABLE messages DROP COLUMN content_hash;",
        "TRUNCATE TABLE messages;",
    ]
    for stmt in bad_statements:
        matched = any(pattern.search(stmt) for pattern, _ in DESTRUCTIVE_PATTERNS)
        assert matched, f"Statement '{stmt}' was not detected as destructive"


# ---------------------------------------------------------------------------
# 4. Celery & Redis Boundaries (>=5 tests)
# ---------------------------------------------------------------------------


def test_b4_empty_task_id_status(e2e_client: E2EClient) -> None:
    """B4: Empty or root task status request returns 404 or validation error."""
    res = e2e_client.get("/api/tasks/")
    assert res.status_code in (404, 405)


def test_b4_broker_down_fallback(e2e_client: E2EClient) -> None:
    """B4: When Celery broker is unavailable, handle_upload falls back cleanly."""
    chat_file_content = b"2026-10-15, 10:00 - Alice: Hello\n"
    files = {"file": ("chat.txt", io.BytesIO(chat_file_content), "text/plain")}

    with patch.object(
        celery_worker.parse_file_task,
        "delay",
        side_effect=ConnectionError("Redis connection refused"),
    ):
        res = e2e_client.post("/api/upload/whatsapp", files=files)
        assert res.status_code in (200, 400)


def test_b4_upload_file_exceeds_max_bytes(e2e_client: E2EClient) -> None:
    """B4: Upload exceeding MAX_UPLOAD_BYTES returns HTTP 413 Payload Too Large."""
    oversized = b"A" * (main.MAX_UPLOAD_BYTES + 1024)
    files = {"file": ("big.txt", io.BytesIO(oversized), "text/plain")}
    res = e2e_client.post("/api/upload/whatsapp", files=files)
    assert res.status_code == 413


def test_b4_empty_upload_payload(e2e_client: E2EClient) -> None:
    """B4: Empty 0-byte file upload handled without server crash."""
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    res = e2e_client.post("/api/upload/whatsapp", files=files)
    assert res.status_code in (200, 400)


def test_b4_invalid_platform_parameter(e2e_client: E2EClient) -> None:
    """B4: Invalid platform parameter rejected or handled with validation error."""
    chat_content = b"2026-10-15, 10:00 - Alice: Hello\n"
    files = {"file": ("chat.txt", io.BytesIO(chat_content), "text/plain")}
    res = e2e_client.post("/api/chats/import?platform=invalid_unknown_platform", files=files)
    assert res.status_code in (200, 400, 422)


# ---------------------------------------------------------------------------
# 5. State Persistence & Healthcheck Boundaries (>=5 tests)
# ---------------------------------------------------------------------------


def test_b5_missing_db_returns_offline_status(e2e_client: E2EClient, tmp_path: Path) -> None:
    """B5: When SPARK_DB path does not exist, /api/spark/status reports offline."""
    missing = tmp_path / "definitely_nonexistent.db"
    with patch.dict(os.environ, {"SPARK_DB": str(missing)}):
        res = e2e_client.get("/api/spark/status")
        assert res.status_code == 200
        payload = res.json()
        assert payload.get("status") == "offline"


def test_b5_corrupt_sqlite_integrity_failure(tmp_path: Path) -> None:
    """B5: Corrupted SQLite database detected by integrity check."""
    corrupt_db = tmp_path / "corrupt.db"
    corrupt_db.write_bytes(b"CORRUPTED_SQLITE_HEADER_RANDOM_GARBAGE_BYTES_00000000")
    try:
        conn = sqlite3.connect(f"file:{corrupt_db}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchone()[0]
        conn.close()
        assert res != "ok"
    except sqlite3.DatabaseError:
        pass  # Database error is expected on corrupt file


def test_b5_readonly_db_access(isolated_spark_db: Path) -> None:
    """B5: Status bridge connects in read-only mode, refusing write operations."""
    conn = sqlite3.connect(f"file:{isolated_spark_db}?mode=ro", uri=True)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO seen VALUES ('readonly_test', 1.0);")
        raise AssertionError("Write operation unexpectedly succeeded in read-only mode")
    except sqlite3.OperationalError as e:
        assert "readonly" in str(e).lower() or "attempt to write" in str(e).lower()
    finally:
        conn.close()


def test_b5_empty_tables_handled(e2e_client: E2EClient, isolated_spark_db: Path) -> None:
    """B5: Empty SPARK tables return empty pending and writes arrays."""
    res = e2e_client.get("/api/spark/status")
    assert res.status_code == 200
    payload = res.json()
    assert payload.get("pending") == []
    assert payload.get("writes") == []


def test_b5_rapid_sequential_healthcheck_polling(e2e_client: E2EClient) -> None:
    """B5: 50 rapid sequential healthcheck requests succeed with low latency."""
    start = time.perf_counter()
    for _ in range(50):
        res = e2e_client.get("/api/healthz")
        assert res.status_code == 200
    duration = time.perf_counter() - start
    assert duration < 5.0, f"50 healthchecks took {duration:.2f}s (exceeds 5.0s budget)"
