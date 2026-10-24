from datetime import datetime
from pathlib import Path

import pytest

from src.config import settings
from src.governance.audit import audit_logger
from src.utils import clock
from src.utils.deduplication import deduplicator


@pytest.fixture(autouse=True)
def isolate_spark_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Ensure every test runs with an isolated temporary SQLite database."""
    db_file = str(tmp_path / "spark_test.db")
    monkeypatch.setattr(settings, "spark_db", db_file)
    monkeypatch.setenv("SPARK_DB", db_file)
    deduplicator.db_path = db_file
    deduplicator._ensure_db()
    audit_logger.db_path = db_file
    audit_logger._ensure_schema()
    yield
    deduplicator.db_path = None
    audit_logger.db_path = None


@pytest.fixture
def frozen_clock(monkeypatch):
    def _freeze(iso: str):
        fixed = datetime.fromisoformat(iso)
        monkeypatch.setattr(clock, "now_ist", lambda: fixed.astimezone(clock.IST))

    return _freeze
