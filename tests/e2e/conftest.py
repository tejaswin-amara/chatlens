"""Shared pytest fixtures for the E2E acceptance test suite."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.e2e.harness import (
    PROJECT_ROOT,
    CaddyfileParser,
    ComposeParser,
    E2EClient,
    NginxConfParser,
    celery_worker,
    main,
    setup_in_memory_backend_db,
    setup_isolated_spark_db,
)


@pytest.fixture
def isolated_spark_db(tmp_path: Path) -> Generator[Path, None, None]:
    """Provides an isolated SQLite database matching SPARK PA schema in WAL mode."""
    db_file = tmp_path / "spark_e2e.db"
    conn = setup_isolated_spark_db(db_file)
    conn.close()

    with patch.dict(
        os.environ,
        {"SPARK_DB": str(db_file), "SPARK_MODE": "confirm"},
    ):
        yield db_file


@pytest.fixture
def in_memory_db():
    """Provides an in-memory SQLite backend database with StaticPool and mocked sessions."""
    engine, _, override_async_session_local = setup_in_memory_backend_db()

    with patch.object(celery_worker, "AsyncSessionLocal", override_async_session_local):
        yield engine

    main.app.dependency_overrides.clear()


@pytest.fixture
def e2e_client(in_memory_db, isolated_spark_db: Path) -> E2EClient:
    """Provides a configured E2E client (offline simulation or live target)."""
    return E2EClient(engine=in_memory_db, spark_db=isolated_spark_db)


@pytest.fixture
def compose_config() -> dict:
    """Parses root compose.yaml."""
    return ComposeParser.parse(PROJECT_ROOT / "compose.yaml")


@pytest.fixture
def caddyfile_config() -> dict:
    """Parses root Caddyfile."""
    return CaddyfileParser.parse(PROJECT_ROOT / "Caddyfile")


@pytest.fixture
def nginx_config() -> dict:
    """Parses chatlens-v2/frontend/nginx.conf."""
    return NginxConfParser.parse(PROJECT_ROOT / "chatlens-v2" / "frontend" / "nginx.conf")
