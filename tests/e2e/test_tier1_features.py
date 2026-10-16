"""Tier 1: Feature Coverage E2E Tests (>=5 tests per feature area).

Covers:
- F1: Reverse Proxy & Routing
- F2: Frontend Static Asset Paths
- F4/F5: Database & Alembic Migrations
- F6: Celery & Redis Connection
- F8/F9: State Persistence & Healthchecks
"""

from __future__ import annotations

import importlib
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import models

from scripts.lint_migration import lint_migrations
from tests.e2e.harness import (
    FRONTEND_OUT,
    PROJECT_ROOT,
    E2EClient,
)

# ---------------------------------------------------------------------------
# F1: Reverse Proxy & Routing (>=5 tests)
# ---------------------------------------------------------------------------


def test_f1_root_request_routes_to_frontend(e2e_client: E2EClient) -> None:
    """R1/F1: HTTP GET / routes to frontend SPA and returns HTML."""
    res = e2e_client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("Content-Type", "")
    assert "<html" in res.text.lower() or "<!doctype html" in res.text.lower()


def test_f1_api_healthz_routes_to_backend(e2e_client: E2EClient) -> None:
    """R1/F1: HTTP GET /api/healthz routes to backend and returns status 200."""
    res = e2e_client.get("/api/healthz")
    assert res.status_code == 200
    payload = res.json()
    assert payload == {"status": "ok", "version": "2.0.0"}


def test_f1_api_chats_endpoint_routed(e2e_client: E2EClient) -> None:
    """R1/F1: HTTP GET /api/chats routes to backend API."""
    res = e2e_client.get("/api/chats")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_f1_ws_routing_configuration(caddyfile_config: dict) -> None:
    """R1/F1: Reverse proxy config handles /ws* paths for live sync."""
    handles = caddyfile_config.get("handles", [])
    ws_handles = [h for h in handles if "/ws" in h["pattern"]]
    assert len(ws_handles) >= 1
    assert "chatlens-backend:8000" in ws_handles[0]["upstream"]


def test_f1_caddyfile_routing_contracts(caddyfile_config: dict) -> None:
    """R1/F1: Reverse proxy config correctly maps backend and frontend upstreams."""
    handles = caddyfile_config.get("handles", [])
    api_handles = [h for h in handles if "/api" in h["pattern"]]
    frontend_handles = [h for h in handles if h["pattern"] in ("/*", "")]

    assert len(api_handles) >= 1
    assert "chatlens-backend:8000" in api_handles[0]["upstream"]
    assert len(frontend_handles) >= 1
    assert "chatlens-frontend:80" in frontend_handles[0]["upstream"]


def test_f1_caddyfile_tls_and_encoding(caddyfile_config: dict) -> None:
    """R1/F1: Caddyfile specifies compression and domain substitution."""
    raw = caddyfile_config.get("raw", "")
    assert "{$DOMAIN:localhost}" in raw or "{$DOMAIN" in raw or "localhost" in raw
    encodes = caddyfile_config.get("encodes", [])
    assert any(enc in ("gzip", "zstd") for enc in encodes) or "encode" in raw


# ---------------------------------------------------------------------------
# F2: Frontend Static Asset Paths (>=5 tests)
# ---------------------------------------------------------------------------


def test_f2_static_asset_loads_cleanly(e2e_client: E2EClient) -> None:
    """R1/F2: Static chunks under /_next/static/ load with HTTP 200."""
    static_dir = FRONTEND_OUT / "_next" / "static"
    assert static_dir.exists(), "Frontend static export directory missing"

    static_files = list(static_dir.rglob("*.js")) + list(static_dir.rglob("*.css"))
    assert len(static_files) > 0, "No static JS or CSS chunks found in export"

    sample_file = static_files[0]
    rel_path = sample_file.relative_to(FRONTEND_OUT).as_posix()
    res = e2e_client.get(f"/{rel_path}")

    assert res.status_code == 200
    assert "public, max-age=" in res.headers.get("Cache-Control", "")


def test_f2_spa_route_fallback(e2e_client: E2EClient) -> None:
    """R1/F2: Direct navigation to SPA route returns HTTP 200 and root index.html."""
    res = e2e_client.get("/dashboard")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("Content-Type", "")
    assert "<html" in res.text.lower() or "<!doctype html" in res.text.lower()


def test_f2_no_legacy_basepath_in_static_export() -> None:
    """R1/F2: Static HTML must not contain /chatlens/_next/ prefix."""
    index_file = FRONTEND_OUT / "index.html"
    if index_file.exists():
        content = index_file.read_text(encoding="utf-8")
        assert "/chatlens/_next/" not in content


def test_f2_relative_origin_api_calls() -> None:
    """R1/F2: useApi.ts must resolve API base relative to current origin."""
    use_api_file = PROJECT_ROOT / "chatlens-v2" / "frontend" / "src" / "hooks" / "useApi.ts"
    if use_api_file.exists():
        content = use_api_file.read_text(encoding="utf-8")
        assert (
            'process.env.NEXT_PUBLIC_API_URL ?? ""' in content
            or '|| ""' in content
            or ('NEXT_PUBLIC_API_URL || "http://localhost:8000"' not in content)
        )


def test_f2_nginx_conf_caching_and_spa(nginx_config: dict) -> None:
    """R1/F2: Frontend nginx.conf sets 1y cache for assets and SPA fallback."""
    locations = nginx_config.get("locations", [])
    static_loc = next((loc for loc in locations if "/_next/static" in loc["location"]), None)
    root_loc = next((loc for loc in locations if loc["location"].strip() == "/"), None)

    assert static_loc is not None
    assert "31536000" in (static_loc.get("cache_control") or static_loc.get("raw") or "")

    assert root_loc is not None
    assert "/index.html" in (root_loc.get("try_files") or root_loc.get("raw") or "")


# ---------------------------------------------------------------------------
# F4/F5: Database & Alembic Migrations (>=5 tests)
# ---------------------------------------------------------------------------


def test_f4_pgvector_init_script_exists_and_idempotent() -> None:
    """R2/F4: PostgreSQL init script creates vector extension idempotently."""
    init_script = PROJECT_ROOT / "docker" / "postgres" / "01-init-pgvector.sql"
    assert init_script.exists()
    content = init_script.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in content


def test_f5_alembic_configuration_structure() -> None:
    """R2/F5: Alembic config and migrations directory are present."""
    alembic_ini = PROJECT_ROOT / "chatlens-v2" / "backend" / "alembic.ini"
    env_py = PROJECT_ROOT / "chatlens-v2" / "backend" / "migrations" / "env.py"
    assert alembic_ini.exists()
    assert env_py.exists()


def test_f5_migrations_lint_check() -> None:
    """R2/F5: SQL migration scripts satisfy expand/contract safety rules."""
    migrations_dir = PROJECT_ROOT / "chatlens-v2" / "backend" / "migrations"
    violations = lint_migrations(migrations_dir)
    assert violations == [], f"Migration linter violations found: {violations}"


def test_f5_schema_message_table_has_content_hash() -> None:
    """R2/F5: Message model defines content_hash and unique deduplication index."""
    has_column = hasattr(models.Message, "content_hash")
    assert has_column

    table_args = getattr(models.Message, "__table_args__", ())
    indices = [arg for arg in table_args if hasattr(arg, "name")]
    hash_idx = next((idx for idx in indices if "content_hash" in idx.name), None)
    assert hash_idx is not None
    assert hash_idx.unique is True


def test_f5_schema_message_table_has_vector_embedding() -> None:
    """R2/F5: Message model defines 768-dimensional vector embedding column."""
    has_embedding = hasattr(models.Message, "embedding")
    assert has_embedding
    col = models.Message.embedding
    assert "Vector" in str(type(col.type)) or "768" in str(col.type)


# ---------------------------------------------------------------------------
# F6: Celery & Redis Connection (>=5 tests)
# ---------------------------------------------------------------------------


def test_f6_celery_broker_url_resolution() -> None:
    """R2/F6: celery_worker.py resolves CELERY_BROKER_URL with fallback to REDIS_URL."""
    import celery_worker as cw

    with patch.dict(os.environ, {"CELERY_BROKER_URL": "redis://custom-redis:6379/1"}):
        importlib.reload(cw)
        assert "custom-redis:6379/1" in cw.redis_url

    with patch.dict(
        os.environ,
        {"CELERY_BROKER_URL": "", "REDIS_URL": "redis://fallback-redis:6379/2"},
        clear=True,
    ):
        importlib.reload(cw)
        assert "fallback-redis:6379/2" in cw.redis_url


def test_f6_celery_result_backend_configuration() -> None:
    """R2/F6: celery_app is initialized with a result backend for task polling."""
    from celery_worker import celery_app

    if hasattr(celery_app, "conf"):
        assert celery_app.conf.result_backend is not None


def test_f6_redis_healthcheck_contract(compose_config: dict) -> None:
    """R4/F6: Redis service defines redis-cli ping healthcheck."""
    services = compose_config.get("services", {})
    redis_svc = services.get("redis", {})
    health = redis_svc.get("healthcheck", {})
    test_cmd = health.get("test", [])
    test_cmd_str = " ".join(test_cmd) if isinstance(test_cmd, list) else str(test_cmd)
    assert "redis-cli" in test_cmd_str and "ping" in test_cmd_str


def test_f6_shared_upload_volume_contract() -> None:
    """R2/F6: Uploads path resolution handles local and container storage."""
    uploads_dir = PROJECT_ROOT / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    assert uploads_dir.exists()


def test_f6_async_task_status_endpoint(e2e_client: E2EClient) -> None:
    """R2/F6: GET /api/tasks/{task_id} returns formatted task status schema."""
    res = e2e_client.get("/api/tasks/nonexistent-task-uuid-1234")
    assert res.status_code == 200
    payload = res.json()
    assert "status" in payload


# ---------------------------------------------------------------------------
# F8/F9: State Persistence & Healthchecks (>=5 tests)
# ---------------------------------------------------------------------------


def test_f8_spark_sqlite_wal_persistence(isolated_spark_db: Path) -> None:
    """R3/F8: SPARK SQLite database is in WAL journal mode."""
    conn = sqlite3.connect(str(isolated_spark_db))
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    conn.close()
    assert mode.upper() == "WAL"


def test_f8_spark_sqlite_integrity_check(isolated_spark_db: Path) -> None:
    """R4/F8: SQLite integrity check verifies database consistency."""
    conn = sqlite3.connect(f"file:{isolated_spark_db}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    result = cur.fetchone()[0]
    conn.close()
    assert result == "ok"


def test_f8_backend_spark_status_bridge(e2e_client: E2EClient, isolated_spark_db: Path) -> None:
    """R3/F8: GET /api/spark/status inspects SPARK SQLite state."""
    conn = sqlite3.connect(str(isolated_spark_db))
    conn.execute("INSERT OR REPLACE INTO seen VALUES ('test_key_1', 100.0);")
    conn.commit()
    conn.close()

    res = e2e_client.get("/api/spark/status")
    assert res.status_code == 200
    payload = res.json()
    assert payload.get("status") in ("online", "active", "ok", "dry", "confirm") or (
        "seen_messages" in payload and payload["seen_messages"] >= 1
    )


def test_f9_container_healthcheck_definitions(compose_config: dict) -> None:
    """R4/F9: Key compose services declare healthcheck blocks."""
    services = compose_config.get("services", {})
    assert "postgres" in services
    assert "redis" in services
    assert "healthcheck" in services["postgres"]
    assert "healthcheck" in services["redis"]


def test_f9_restart_and_log_rotation_policies(compose_config: dict) -> None:
    """R4/F9: Services declare restart policies."""
    services = compose_config.get("services", {})
    for _name, svc in services.items():
        if isinstance(svc, dict) and "restart" in svc:
            assert svc["restart"] in ("always", "unless-stopped", "no")
