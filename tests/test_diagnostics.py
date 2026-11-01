"""Comprehensive offline unit and integration tests for the ChatLens AI Problem-Solving Agent.

Validates subsystem health probes (PostgreSQL, Redis, Celery, SPARK SQLite, Gemini),
in-memory log ring buffering, exception triage, data consistency verification,
two-tier diagnostic engine (deterministic rules & prompt-fenced Gemini AI),
safe remediation guardrails, and FastAPI diagnostic REST endpoints.
Zero external network calls.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

backend_dir = str(Path(__file__).resolve().parent.parent / "chatlens-v2" / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import celery_worker  # noqa: E402
from database import get_db  # noqa: E402
from diagnostics import (  # noqa: E402
    DiagnosticLogBuffer,
    DiagnosticsService,
    diagnostic_buffer,
)
from models import Base, Message  # noqa: E402

import main  # noqa: E402

# --- In-Memory Database Session Wrapper for Offline Async Testing ---


class AsyncSessionMock:
    """Async session proxy around synchronous SQLite session for offline test execution."""

    def __init__(self, sync_session: Session) -> None:
        self._s = sync_session
        self.bind = sync_session.bind

    async def execute(self, stmt: Any) -> Any:
        return self._s.execute(stmt)

    async def scalar(self, stmt: Any) -> Any:
        return self._s.scalar(stmt)

    async def commit(self) -> None:
        self._s.commit()

    async def rollback(self) -> None:
        self._s.rollback()

    async def close(self) -> None:
        pass


@pytest.fixture
def in_memory_db():
    """Create an isolated in-memory SQLite database using StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db_lock = threading.Lock()

    def override_get_db():
        with db_lock:
            session = Session(engine)
            try:
                yield AsyncSessionMock(session)
            finally:
                session.close()

    @asynccontextmanager
    async def override_session_local():
        with db_lock:
            session = Session(engine)
            try:
                yield AsyncSessionMock(session)
            finally:
                session.close()

    main.app.dependency_overrides[get_db] = override_get_db

    with (
        patch("diagnostics.AsyncSessionLocal", override_session_local),
        patch("celery_worker.AsyncSessionLocal", override_session_local),
    ):
        yield engine

    main.app.dependency_overrides.clear()


@pytest.fixture
def temp_spark_db():
    """Create an isolated temporary SQLite database simulating spark.db."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_json TEXT,
            status TEXT,
            created REAL
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS seen (
            key TEXT PRIMARY KEY,
            ts REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS writes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            kind TEXT,
            event_id TEXT,
            prior_json TEXT,
            undone INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS timetable_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_date TEXT NOT NULL,
            period INTEGER,
            course_code TEXT NOT NULL,
            course_name TEXT,
            room TEXT,
            status TEXT NOT NULL,
            summary TEXT,
            created REAL
        );
        """
    )
    # Default fresh heartbeat
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('last_heartbeat', ?)",
        (str(time.time()),),
    )
    conn.commit()
    conn.close()

    old_env = os.environ.get("SPARK_DB")
    os.environ["SPARK_DB"] = db_path

    yield db_path

    if old_env is not None:
        os.environ["SPARK_DB"] = old_env
    else:
        os.environ.pop("SPARK_DB", None)

    try:
        os.remove(db_path)
    except OSError:
        pass


# --- 1. Log Buffer & Exception Triage Tests ---


def test_log_buffer_filtering_and_capacity():
    """Test that DiagnosticLogBuffer captures only WARNING/ERROR and respects max capacity."""
    buf = DiagnosticLogBuffer(capacity=10)
    test_logger = logging.getLogger("test_buffer_logger")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(buf)

    # DEBUG and INFO should be ignored
    test_logger.debug("Debug log")
    test_logger.info("Info log")
    assert len(buf.get_logs()) == 0

    # WARNING and ERROR should be captured
    test_logger.warning("Warning message 1")
    test_logger.error("Error message 1")
    assert len(buf.get_logs()) == 2

    # Verify ring buffer capacity overflow
    for i in range(15):
        test_logger.error(f"Overflow error {i}")

    logs = buf.get_logs(limit=20)
    assert len(logs) == 10
    assert logs[-1]["message"] == "Overflow error 14"

    # Test clear
    buf.clear()
    assert len(buf.get_logs()) == 0
    test_logger.removeHandler(buf)


def test_exception_triage_grouping_and_domains():
    """Test exception fingerprinting, grouping, and operational domain categorization."""
    buf = DiagnosticLogBuffer(capacity=50)
    db_logger = logging.getLogger("db.sqlite.logger")
    redis_logger = logging.getLogger("broker.redis.logger")
    db_logger.addHandler(buf)
    redis_logger.addHandler(buf)

    try:
        raise sqlite3.OperationalError("database table is locked")
    except sqlite3.OperationalError:
        for _ in range(3):
            db_logger.error("database table is locked", exc_info=True)

    try:
        raise ConnectionError("Connection refused by Redis broker")
    except ConnectionError:
        for _ in range(2):
            redis_logger.error("Connection refused by Redis broker", exc_info=True)

    triage = buf.triage_exceptions()
    assert len(triage) == 2

    # Sorted by count desc: first entry should be database error with count 3
    assert triage[0]["count"] == 3
    assert triage[0]["domain"] == "DATABASE"
    assert triage[0]["exception_type"] == "OperationalError"

    # Second entry should be redis error with count 2
    assert triage[1]["count"] == 2
    assert triage[1]["domain"] == "REDIS_CELERY"
    assert triage[1]["exception_type"] == "ConnectionError"

    db_logger.removeHandler(buf)
    redis_logger.removeHandler(buf)


# --- 2. Subsystem Health Probes Tests ---


@pytest.mark.asyncio
async def test_subsystems_health_all_healthy(in_memory_db, temp_spark_db):
    """Test subsystem check when all dependencies are healthy and reachable."""
    service = DiagnosticsService()

    with (
        patch("redis.Redis.from_url") as mock_redis,
        patch.object(celery_worker.celery_app.control, "inspect") as mock_inspect,
        patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "mock-test-key", "GEMINI_MODEL": "gemini-3.5-flash-lite"},
        ),
    ):
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.llen.return_value = 0
        mock_redis.return_value = mock_client

        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {"celery@worker1": "pong"}
        mock_inspect.return_value = mock_inspector

        with Session(in_memory_db) as sync_session:
            async_s = AsyncSessionMock(sync_session)
            report = await service.run_diagnostics(session=async_s, use_ai=False)

    assert report["overall_status"] == "healthy"
    subsystems = report["subsystems"]
    assert subsystems["database"]["status"] == "healthy"
    assert subsystems["redis"]["status"] == "healthy"
    assert subsystems["celery"]["status"] == "healthy"
    assert subsystems["celery"]["active_workers"] == 1
    assert subsystems["spark_daemon"]["status"] == "online"
    assert subsystems["spark_daemon"]["wal_mode"] is True
    assert subsystems["gemini_api"]["status"] == "configured"
    assert len(report["root_causes"]) == 0


@pytest.mark.asyncio
async def test_subsystems_redis_down(in_memory_db, temp_spark_db):
    """Test diagnosis when Redis broker is unreachable."""
    service = DiagnosticsService()

    with patch("redis.Redis.from_url") as mock_redis:
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Redis host unreachable")
        mock_redis.return_value = mock_client

        with Session(in_memory_db) as sync_session:
            async_s = AsyncSessionMock(sync_session)
            report = await service.run_diagnostics(session=async_s, use_ai=False)

    assert report["overall_status"] in ("warning", "critical")
    assert report["subsystems"]["redis"]["status"] == "unavailable"
    root_cause_codes = [rc["code"] for rc in report["root_causes"]]
    assert "REDIS_UNREACHABLE" in root_cause_codes


@pytest.mark.asyncio
async def test_subsystems_celery_worker_down(in_memory_db, temp_spark_db):
    """Test diagnosis when Redis is healthy but Celery worker fleet is inactive."""
    service = DiagnosticsService()

    with (
        patch("redis.Redis.from_url") as mock_redis,
        patch.object(celery_worker.celery_app.control, "inspect") as mock_inspect,
    ):
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.llen.return_value = 5
        mock_redis.return_value = mock_client

        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {}  # 0 workers
        mock_inspect.return_value = mock_inspector

        with Session(in_memory_db) as sync_session:
            async_s = AsyncSessionMock(sync_session)
            report = await service.run_diagnostics(session=async_s, use_ai=False)

    assert report["subsystems"]["celery"]["status"] == "no_workers"
    root_cause_codes = [rc["code"] for rc in report["root_causes"]]
    assert "CELERY_WORKER_DOWN" in root_cause_codes


@pytest.mark.asyncio
async def test_subsystems_spark_daemon_stalled(in_memory_db, temp_spark_db):
    """Test detection of stalled SPARK daemon heartbeat (>1800s)."""
    service = DiagnosticsService()

    # Set heartbeat to 3000 seconds ago
    stale_hb = time.time() - 3000
    conn = sqlite3.connect(temp_spark_db)
    conn.execute("UPDATE meta SET value = ? WHERE key = 'last_heartbeat'", (str(stale_hb),))
    conn.commit()
    conn.close()

    with Session(in_memory_db) as sync_session:
        async_s = AsyncSessionMock(sync_session)
        report = await service.run_diagnostics(session=async_s, use_ai=False)

    assert report["subsystems"]["spark_daemon"]["status"] == "stalled"
    root_cause_codes = [rc["code"] for rc in report["root_causes"]]
    assert "DAEMON_STALLED_HB" in root_cause_codes


# --- 3. Consistency Verification & Remediation Tests ---


@pytest.mark.asyncio
async def test_consistency_stalled_claimed_pending_and_remediation(temp_spark_db):
    """Test detection and safe requeuing of orphaned CLAIMED tasks."""
    service = DiagnosticsService()
    now = time.time()

    conn = sqlite3.connect(temp_spark_db)
    # Insert task claimed 600s ago
    conn.execute(
        "INSERT INTO pending (event_json, status, created) VALUES (?, 'CLAIMED', ?)",
        (json.dumps({"event": "ROOM_OVERRIDE", "room": "M001"}), now - 600),
    )
    # Insert fresh claimed task (30s ago)
    conn.execute(
        "INSERT INTO pending (event_json, status, created) VALUES (?, 'CLAIMED', ?)",
        (json.dumps({"event": "ROOM_OVERRIDE", "room": "M002"}), now - 30),
    )
    conn.commit()
    conn.close()

    consistency = await service.verify_consistency()
    assert len(consistency["stalled_claimed_pending"]) == 1
    assert consistency["stalled_claimed_pending"][0]["age_s"] >= 590

    # Test Dry Run remediation
    dry_res = await service.execute_remediation("REQUEUE_STALLED_PENDING", dry_run=True)
    assert dry_res["success"] is True
    assert dry_res["affected_count"] == 1

    # Verify status is still CLAIMED after dry run
    conn = sqlite3.connect(temp_spark_db)
    row = conn.execute("SELECT status FROM pending WHERE created < ?", (now - 500,)).fetchone()
    assert row[0] == "CLAIMED"
    conn.close()

    # Execute actual remediation
    res = await service.execute_remediation("REQUEUE_STALLED_PENDING", dry_run=False)
    assert res["success"] is True
    assert res["affected_count"] == 1

    # Verify status has transitioned to PENDING
    conn = sqlite3.connect(temp_spark_db)
    row = conn.execute("SELECT status FROM pending WHERE created < ?", (now - 500,)).fetchone()
    assert row[0] == "PENDING"
    conn.close()


@pytest.mark.asyncio
async def test_consistency_missed_academic_reminders_and_remediation(temp_spark_db):
    """Test detection and resolution of missed same-day academic reminders."""
    service = DiagnosticsService()
    today_str = service._today().isoformat()

    conn = sqlite3.connect(temp_spark_db)
    conn.execute(
        "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
        (
            json.dumps({"summary": "Operating Systems Midterm", "target_date": today_str}),
            time.time(),
        ),
    )
    conn.commit()
    conn.close()

    consistency = await service.verify_consistency()
    assert len(consistency["missed_reminders"]) == 1
    assert consistency["missed_reminders"][0]["target_date"] == today_str

    # Execute remediation to acknowledge and dispatch
    res = await service.execute_remediation("RETRY_MISSED_REMINDERS")
    assert res["success"] is True
    assert res["affected_count"] == 1

    # Subsequent consistency check should show 0 missed reminders
    new_consistency = await service.verify_consistency()
    assert len(new_consistency["missed_reminders"]) == 0


@pytest.mark.asyncio
async def test_consistency_stale_overrides_and_pruning(temp_spark_db):
    """Test detection and safe pruning of timetable overrides older than 7 days."""
    service = DiagnosticsService()
    old_date = (service._today() - timedelta(days=12)).isoformat()
    recent_date = (service._today() - timedelta(days=2)).isoformat()

    conn = sqlite3.connect(temp_spark_db)
    conn.execute(
        "INSERT INTO timetable_overrides (target_date, period, course_code, status, created) "
        "VALUES (?, 1, '23CS2101', 'OVERRIDE', ?)",
        (old_date, time.time() - 86400 * 12),
    )
    conn.execute(
        "INSERT INTO timetable_overrides (target_date, period, course_code, status, created) "
        "VALUES (?, 2, '23CS2102', 'OVERRIDE', ?)",
        (recent_date, time.time() - 86400 * 2),
    )
    conn.commit()
    conn.close()

    consistency = await service.verify_consistency()
    assert consistency["stale_overrides_count"] == 1

    # Prune stale overrides
    res = await service.execute_remediation("PRUNE_STALE_OVERRIDES")
    assert res["success"] is True
    assert res["affected_count"] == 1

    conn = sqlite3.connect(temp_spark_db)
    remaining = conn.execute("SELECT count(*) FROM timetable_overrides").fetchone()[0]
    conn.close()
    assert remaining == 1


@pytest.mark.asyncio
async def test_consistency_missing_embeddings_and_backfill(in_memory_db):
    """Test detection of unembedded messages and safe batch backfill."""
    service = DiagnosticsService()

    with Session(in_memory_db) as sync_session:
        # Insert 15 messages without embeddings
        for i in range(15):
            sync_session.add(
                Message(
                    platform="whatsapp",
                    chat_name="Academic Group",
                    sender="Student",
                    timestamp="2026-11-01 10:00:00",
                    text=f"Sample announcement text number {i}",
                    embedding=None,
                    content_hash=f"hash_{i}",
                )
            )
        sync_session.commit()

        async_s = AsyncSessionMock(sync_session)
        consistency = await service.verify_consistency(db=async_s)
        assert consistency["unembedded_messages_count"] == 15
        assert consistency["total_messages"] == 15
        assert consistency["unembedded_ratio"] == 1.0

        # Backfill embeddings with batch_size=10
        with patch("celery_worker.generate_embeddings_batch") as mock_batch:
            mock_batch.return_value = [[0.1] * 768] * 10
            res = await service.execute_remediation(
                "BACKFILL_EMBEDDINGS", params={"batch_size": 10}, db=async_s
            )
            assert res["success"] is True
            assert res["affected_count"] == 10

        # Verify 5 remain unembedded
        rem_consistency = await service.verify_consistency(db=async_s)
        assert rem_consistency["unembedded_messages_count"] == 5


# --- 4. Remediation Guardrails & Validation ---


@pytest.mark.asyncio
async def test_remediation_guardrail_unsupported_action():
    """Verify that unwhitelisted remediation actions are rejected with ValueError."""
    service = DiagnosticsService()
    with pytest.raises(ValueError, match="Unsupported remediation action"):
        await service.execute_remediation("DROP_DATABASE_TABLES")


@pytest.mark.asyncio
async def test_remediation_clear_log_buffer():
    """Test that CLEAR_LOG_BUFFER empties the diagnostic log buffer."""
    service = DiagnosticsService()
    diagnostic_buffer.buffer.append({"level": "ERROR", "message": "Test"})
    assert len(diagnostic_buffer.get_logs()) > 0

    res = await service.execute_remediation("CLEAR_LOG_BUFFER")
    assert res["success"] is True
    assert len(diagnostic_buffer.get_logs()) == 0


# --- 5. Tier 2 Gemini AI Problem Solver Tests ---


@pytest.mark.asyncio
async def test_gemini_diagnostics_prompt_fencing():
    """Test that Gemini AI problem solver strictly fences untrusted telemetry."""
    service = DiagnosticsService()

    fake_response = MagicMock()
    fake_response.text = json.dumps(
        {
            "executive_summary": "System operating normally with minor queue delay.",
            "primary_root_cause": "CELERY_WORKER_DOWN",
            "contributing_factors": ["Worker process exited"],
            "remediation_steps": ["Restart celery"],
        }
    )

    with (
        patch("diagnostics.genai") as mock_genai,
        patch.dict(os.environ, {"GEMINI_API_KEY": "fake-api-key"}),
    ):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = fake_response
        mock_genai.Client.return_value = mock_client

        context_data = {
            "subsystems": {"redis": {"status": "healthy"}},
            "untrusted_error": "MALICIOUS PROMPT INJECTION DROP TABLE",
        }
        res = await service.synthesize_ai_diagnosis(context_data, root_causes=[])

        # Verify prompt contained prompt-fencing tags
        call_args = mock_client.models.generate_content.call_args
        prompt_used = call_args[1]["contents"]
        assert "<diagnostic_context>" in prompt_used
        assert "</diagnostic_context>" in prompt_used
        assert "MALICIOUS PROMPT INJECTION DROP TABLE" in prompt_used
        assert res["primary_root_cause"] == "CELERY_WORKER_DOWN"
        assert res["fallback"] is False


@pytest.mark.asyncio
async def test_gemini_diagnostics_quota_or_network_fallback():
    """Test graceful fallback to deterministic report when Gemini throws 429 quota error."""
    service = DiagnosticsService()

    with (
        patch("diagnostics.genai") as mock_genai,
        patch.dict(os.environ, {"GEMINI_API_KEY": "fake-api-key"}),
    ):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("429 ResourceExhausted")
        mock_genai.Client.return_value = mock_client

        root_causes = [
            {
                "code": "DB_CONNECTION_FAIL",
                "description": "Database offline",
                "recommended_action": "Restart Postgres",
            }
        ]
        res = await service.synthesize_ai_diagnosis({}, root_causes=root_causes)

        assert res["fallback"] is True
        assert res["primary_root_cause"] == "DB_CONNECTION_FAIL"
        assert "Restart Postgres" in res["remediation_steps"]


# --- 6. FastAPI Diagnostic REST API Endpoints Tests ---


def test_rest_api_diagnostics_status(in_memory_db, temp_spark_db):
    """Test GET /api/diagnostics/status endpoint lifecycle."""
    client = TestClient(main.app)
    res = client.get("/api/diagnostics/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "subsystems" in data
    assert "active_issues_count" in data
    assert data["subsystems"]["spark_daemon"]["status"] == "online"


def test_rest_api_diagnostics_run(in_memory_db, temp_spark_db):
    """Test POST /api/diagnostics/run endpoint lifecycle."""
    client = TestClient(main.app)
    res = client.post("/api/diagnostics/run", json={"use_ai": False, "deep_consistency": True})
    assert res.status_code == 200
    data = res.json()
    assert "overall_status" in data
    assert "subsystems" in data
    assert "consistency" in data
    assert "root_causes" in data
    assert "exceptions_triage" in data


def test_rest_api_diagnostics_consistency(in_memory_db, temp_spark_db):
    """Test GET /api/diagnostics/consistency endpoint lifecycle."""
    client = TestClient(main.app)
    res = client.get("/api/diagnostics/consistency")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "stalled_claimed_pending" in data
    assert "overdue_pending_count" in data
    assert "missed_reminders" in data


def test_rest_api_diagnostics_remediation(in_memory_db, temp_spark_db):
    """Test POST /api/diagnostics/remediate with valid and invalid actions."""
    client = TestClient(main.app)

    # Valid action
    res = client.post(
        "/api/diagnostics/remediate",
        json={"action": "CLEAR_LOG_BUFFER", "parameters": {}, "dry_run": False},
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Invalid action rejected with 400
    bad_res = client.post(
        "/api/diagnostics/remediate",
        json={"action": "INVALID_ACTION_NAME", "parameters": {}},
    )
    assert bad_res.status_code == 400
    assert "Unsupported remediation action" in bad_res.json()["detail"]


# --- 7. Celery Diagnostics Task & Sync Fallback Tests ---


def test_celery_task_and_sync_fallback(in_memory_db, temp_spark_db):
    """Test Celery background diagnostic task and synchronous execution fallback."""
    # Test synchronous fallback
    sync_report = celery_worker.run_system_diagnostics_sync(use_ai=False, auto_remediate=False)
    assert "overall_status" in sync_report
    assert "subsystems" in sync_report

    # Test Celery task wrapper (.delay or direct call)
    task_res = celery_worker.run_system_diagnostics_task(use_ai=False, auto_remediate=False)
    assert "overall_status" in task_res
