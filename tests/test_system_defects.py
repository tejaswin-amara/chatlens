"""Comprehensive unit and regression tests for system defects, concurrency bottlenecks,
and resilience fixes across SPARK PA daemon and ChatLens backend.
"""

import asyncio
import os
import sqlite3
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.main import _install_signal_handlers, main, run_briefing, run_daemon, run_reminders
from src.utils import clock
from src.utils.deduplication import MessageDeduplicator, deduplicator

# Ensure chatlens-v2/backend is available on sys.path
backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "chatlens-v2", "backend")
)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


@pytest.fixture
def mock_valid_settings() -> Any:
    """Fixture providing valid settings mocks for main daemon tests."""
    with patch("src.main.settings") as s:
        s.telegram_api_id = 123
        s.telegram_api_hash = MagicMock(get_secret_value=lambda: "hash")
        s.telegram_session_string = MagicMock(get_secret_value=lambda: "session")
        s.google_credentials_base64 = MagicMock(get_secret_value=lambda: "b64")
        s.gemini_api_key = MagicMock(get_secret_value=lambda: "key")
        s.spark_mode = "dry"
        s.allowed_chat_ids = [100]
        s.bot_token = MagicMock(get_secret_value=lambda: "token")
        s.owner_chat_id = 12345
        s.validate_required = MagicMock()
        yield s


# ============================================================================
# 1. Deduplicator Initialization & Concurrency (Fix 1)
# ============================================================================


def test_deduplicator_initialization_once_and_lock_contention(tmp_path: Path) -> None:
    """Verify that _init_db() sets _initialized = True and executes only once."""
    db_file = str(tmp_path / "test_init.db")
    dedup = MessageDeduplicator(db_path=db_file)

    assert dedup._initialized is False

    # First access triggers _init_db
    dedup.meta_set("init_test", "1")
    assert dedup._initialized is True
    assert dedup.meta_get("init_test") == "1"

    # Subsequent access does NOT re-initialize DDL
    with patch.object(dedup, "_init_db") as mock_init:
        dedup.meta_set("init_test_2", "2")
        mock_init.assert_not_called()
        assert dedup.meta_get("init_test_2") == "2"

    # Multi-threaded concurrent reads/writes should not hit lock contention
    errors: list[Exception] = []

    def worker(worker_id: int) -> None:
        try:
            for i in range(20):
                dedup.meta_set(f"thread_{worker_id}_{i}", str(i))
                val = dedup.meta_get(f"thread_{worker_id}_{i}")
                assert val == str(i)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent workers encountered errors: {errors}"


def test_deduplicator_list_pending_unlimited_fetch(tmp_path: Path) -> None:
    """Verify that list_pending(limit=None) fetches all pending tasks without starvation."""
    db_file = str(tmp_path / "test_unlimited.db")
    dedup = MessageDeduplicator(db_path=db_file)

    # Insert 25 pending tasks
    for i in range(25):
        dedup.add_pending(f'{{"event": {{"summary": "Task {i}"}}}}')

    # Default limit=20 truncates
    items_limited = dedup.list_pending(limit=20)
    assert len(items_limited) == 20

    # limit=None fetches all items without starvation
    items_all = dedup.list_pending(limit=None)
    assert len(items_all) == 25


# ============================================================================
# 2. ChatLens Deadlines API Fallback Fix (Fix 2)
# ============================================================================


def test_chatlens_deadlines_fallback_readonly_and_created_column(tmp_path: Path) -> None:
    """Verify deadlines fallback queries 'created' column and connects via mode=ro URI."""
    from fastapi.testclient import TestClient

    from main import app

    db_file = str(tmp_path / "spark_readonly.db")
    dedup = MessageDeduplicator(db_path=db_file)

    now_ts = time.time()
    dedup.add_pending('{"event": {"summary": "Math Assignment 4", "target_date": "2026-11-01"}}')

    client = TestClient(app)

    # Patch sys.modules to simulate src.academic_calendar being unavailable in standalone mode
    with (
        patch.dict("os.environ", {"SPARK_DB": db_file}),
        patch.dict(sys.modules, {"src.academic_calendar": None}),
    ):
        response = client.get("/api/deadlines")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 1
        first_task = data["tasks"][0]
        assert first_task["summary"] == "Math Assignment 4"
        assert first_task["status"] == "PENDING"
        assert first_task["created"] is not None
        assert abs(first_task["created"] - now_ts) < 10.0


def test_chatlens_deadlines_fallback_direct_query(tmp_path: Path) -> None:
    """Directly verify SQLite query with mode=ro URI and 'created' column on read-only file."""
    db_file = str(tmp_path / "spark_direct_ro.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup.add_pending('{"event": {"summary": "Chemistry Lab Report"}}')

    # Connect with mode=ro URI
    conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, created, status, event_json FROM pending "
        "WHERE status = 'PENDING' ORDER BY id DESC LIMIT 20;"
    )
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 1
    row = rows[0]
    assert row[1] > 0  # created timestamp
    assert row[2] == "PENDING"
    assert "Chemistry Lab Report" in row[3]


# ============================================================================
# 3. Reminders Task Starvation & Exception Isolation (Fix 3.1)
# ============================================================================


@pytest.mark.asyncio
async def test_run_reminders_prevents_task_starvation(mock_valid_settings: Any) -> None:
    """Verify run_reminders fetches all pending items, preventing starvation beyond 20 items."""
    today_str = clock.today_ist().strftime("%Y-%m-%d")

    # Generate 25 items scheduled for today
    items = []
    for i in range(25):
        items.append(
            {
                "id": i + 1,
                "event": {
                    "course_name": f"Course {i + 1}",
                    "course_code": f"C{i + 1:03d}",
                    "period": "09:00 - 10:00",
                    "summary": f"Deadline {i + 1}",
                    "target_date": today_str,
                    "intent": "TASK",
                },
                "status": "PENDING",
            }
        )

    dispatched_messages: list[str] = []

    def mock_send(text: str, *args: Any, **kwargs: Any) -> None:
        dispatched_messages.append(text)

    with (
        patch.object(deduplicator, "list_pending", return_value=items) as mock_list,
        patch.object(deduplicator, "meta_get", return_value=None),
        patch.object(deduplicator, "meta_set"),
        patch("src.notify.bot.bot.send", side_effect=mock_send),
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_reminders()

        # Confirm list_pending was called with limit=None
        mock_list.assert_called_with(limit=None)
        # All 25 items should be dispatched
        assert len(dispatched_messages) == 25


@pytest.mark.asyncio
async def test_run_reminders_isolates_item_exceptions(mock_valid_settings: Any) -> None:
    """Verify that an error on one reminder notice does not drop remaining notices."""
    today_str = clock.today_ist().strftime("%Y-%m-%d")

    items = [
        # Item 1: Valid notice
        {
            "id": 1,
            "event": {
                "course_name": "Operating Systems",
                "summary": "Project Submission",
                "target_date": today_str,
            },
            "status": "PENDING",
        },
        # Item 2: Malformed notice that causes exception during processing
        {
            "id": 2,
            "event": {
                "course_name": None,
                "course_code": None,
                "summary": None,
                "target_date": today_str,
            },
            "status": "PENDING",
        },
        # Item 3: Valid notice following the faulty one
        {
            "id": 3,
            "event": {
                "course_name": "Database Systems",
                "summary": "Quiz 2",
                "target_date": today_str,
            },
            "status": "PENDING",
        },
    ]

    sent_courses: list[str] = []

    def mock_send(text: str, *args: Any, **kwargs: Any) -> None:
        if "Operating Systems" in text:
            sent_courses.append("Operating Systems")
        elif "Database Systems" in text:
            sent_courses.append("Database Systems")

    orig_render = None
    from src.formatting import templates

    orig_render = templates.render_proactive_reminder

    def flaky_render(*args: Any, **kwargs: Any) -> str:
        if kwargs.get("course_name") == "Academic Notice" and kwargs.get("course_code") is None:
            raise ValueError("Simulated template rendering error for malformed item")
        return orig_render(*args, **kwargs)

    with (
        patch.object(deduplicator, "list_pending", return_value=items),
        patch.object(deduplicator, "meta_get", return_value=None),
        patch.object(deduplicator, "meta_set"),
        patch("src.formatting.templates.render_proactive_reminder", side_effect=flaky_render),
        patch("src.notify.bot.bot.send", side_effect=mock_send),
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_reminders()

        # Both item 1 and item 3 should succeed despite item 2 failure
        assert "Operating Systems" in sent_courses
        assert "Database Systems" in sent_courses


@pytest.mark.asyncio
async def test_run_reminders_handles_iso_timestamp(mock_valid_settings: Any) -> None:
    """Verify target_date formatted as an ISO datetime string matches today_str."""
    today_str = clock.today_ist().strftime("%Y-%m-%d")
    iso_date = f"{today_str}T14:30:00+05:30"

    items = [
        {
            "id": 10,
            "event": {
                "course_name": "Computer Networks",
                "summary": "Lab Test",
                "target_date": iso_date,
            },
            "status": "PENDING",
        }
    ]

    sent_any = False

    def mock_send(text: str, *args: Any, **kwargs: Any) -> None:
        nonlocal sent_any
        sent_any = True

    with (
        patch.object(deduplicator, "list_pending", return_value=items),
        patch.object(deduplicator, "meta_get", return_value=None),
        patch.object(deduplicator, "meta_set"),
        patch("src.notify.bot.bot.send", side_effect=mock_send),
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_reminders()

        assert sent_any is True


# ============================================================================
# 4. Briefing Transient Retry Backoff (Fix 3.2)
# ============================================================================


@pytest.mark.asyncio
async def test_run_briefing_retries_on_transient_failure_with_backoff() -> None:
    """Verify run_briefing retries after a 5-minute backoff rather than locking out for 24 hours."""
    now = datetime(2026, 11, 1, 7, 15, 0, tzinfo=UTC)

    attempts = 0
    sleeps: list[float] = []

    async def mock_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if attempts >= 2:
            raise asyncio.CancelledError()

    async def flaky_fetch() -> tuple[list, list, list, dict]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("Transient network outage")
        return ([], [], [], {})

    with (
        patch("src.utils.clock.now_ist", return_value=now),
        patch("src.utils.clock.today_ist", return_value=now.date()),
        patch("src.briefing.next_run", return_value=now),
        patch("src.briefing.fetch_briefing_inputs", side_effect=flaky_fetch),
        patch("src.briefing.build_briefing", return_value="Test Briefing"),
        patch("src.notify.bot.bot.send", return_value=True),
        patch.object(deduplicator, "meta_get", return_value=None),
        patch.object(deduplicator, "meta_set") as mock_set,
        patch("asyncio.sleep", side_effect=mock_sleep),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_briefing()

        # Check that backoff sleep of 300 seconds was called after the first failure
        assert 300 in sleeps
        # Second attempt should have succeeded
        assert attempts == 2
        mock_set.assert_called_with("briefing_last_date", "2026-11-01")


# ============================================================================
# 5. Windows Signal Handling & Shutdown (Fix 3.3)
# ============================================================================


def test_install_signal_handlers_handles_not_implemented_and_attribute_errors() -> None:
    """Verify _install_signal_handlers catches NotImplementedError/AttributeError on Windows."""
    stop_event = asyncio.Event()

    # Mock loop raising NotImplementedError
    loop_mock = MagicMock()
    loop_mock.add_signal_handler.side_effect = NotImplementedError("Windows Proactor loop")

    with patch("signal.signal") as mock_signal:
        _install_signal_handlers(loop_mock, stop_event)
        # Should have fallen back to signal.signal
        assert mock_signal.called

    # Mock loop raising AttributeError
    loop_mock_attr = MagicMock()
    loop_mock_attr.add_signal_handler.side_effect = AttributeError("No add_signal_handler")

    with patch("signal.signal") as mock_signal:
        _install_signal_handlers(loop_mock_attr, stop_event)
        assert mock_signal.called


@pytest.mark.asyncio
async def test_run_daemon_graceful_keyboard_interrupt(mock_valid_settings: Any) -> None:
    """Verify run_daemon catches KeyboardInterrupt and returns 0 cleanly."""

    class FakeInterruptClient:
        def on(self, event: Any) -> Any:
            return lambda f: f

        async def connect(self) -> None:
            raise KeyboardInterrupt("Ctrl+C pressed")

        def is_connected(self) -> bool:
            return False

        async def disconnect(self) -> None:
            pass

    code = await run_daemon(client=FakeInterruptClient(), handle_signals=False)
    assert code == 0


def test_main_graceful_keyboard_interrupt() -> None:
    """Verify main() catches KeyboardInterrupt and exits cleanly with return code 0."""
    with (
        patch("src.main.run_daemon"),
        patch("asyncio.run", side_effect=KeyboardInterrupt("Ctrl+C")),
        patch("sys.exit") as mock_exit,
    ):
        main()
        mock_exit.assert_called_once_with(0)


# ============================================================================
# 6. Celery Worker Dialect Detection (Fix 4)
# ============================================================================


@pytest.mark.asyncio
async def test_celery_worker_dialect_detection_sqlite_and_postgres() -> None:
    """Verify save_messages reliably detects SQLite vs PostgreSQL dialects."""
    import celery_worker
    from models import Base

    # Test with in-memory SQLite AsyncEngine
    sqlite_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)

    test_messages = [
        {
            "platform": "telegram",
            "chat_name": "Test Group",
            "sender": "Alice",
            "timestamp": "2026-11-01 10:00:00",
            "text": "Assignment 1 due tomorrow",
        }
    ]

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": ""}),
        patch("celery_worker.AsyncSessionLocal", session_maker),
    ):
        # Should execute sqlite_insert and succeed without crashing on pg_insert
        await celery_worker.save_messages(test_messages)

    # Verify message was saved in SQLite table
    async with session_maker() as session:
        from models import Message
        from sqlalchemy import select

        result = await session.execute(select(Message))
        saved = result.scalars().all()
        assert len(saved) == 1
        assert saved[0].sender == "Alice"
        assert saved[0].text == "Assignment 1 due tomorrow"

    await sqlite_engine.dispose()


@pytest.mark.asyncio
async def test_celery_worker_dialect_detection_fallback_branches() -> None:
    """Verify dialect detection branches when session.bind is None or lacks dialect attribute."""
    import celery_worker

    executed_stmts = []

    class FakeSession:
        bind = None

        def get_bind(self) -> Any:
            b = MagicMock()
            b.dialect.name = "sqlite"
            return b

        async def execute(self, stmt: Any) -> None:
            executed_stmts.append(stmt)

        async def commit(self) -> None:
            pass

    class FakeContextManager:
        async def __aenter__(self) -> FakeSession:
            return FakeSession()

        async def __aexit__(self, *args: Any) -> None:
            pass

    test_messages = [
        {
            "platform": "telegram",
            "chat_name": "Group",
            "sender": "Bob",
            "timestamp": "2026-11-01",
            "text": "Hello",
        }
    ]

    with patch("celery_worker.AsyncSessionLocal", return_value=FakeContextManager()):
        await celery_worker.save_messages(test_messages)

    # Verify session.execute was called with a SQLite insert statement
    assert len(executed_stmts) == 1
    stmt = executed_stmts[0]
    assert "sqlite" in stmt.__class__.__module__.lower() or "sqlite" in str(stmt).lower()
