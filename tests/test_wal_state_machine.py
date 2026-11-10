"""Comprehensive tests for Milestone M3: SQLite WAL State Machine and /undo Idempotency.

Verifies:
1. Persistence and connection closing across all 6 tables:
   seen, chat_state, llm_budget, pending, writes, meta.
2. WAL mode (PRAGMA journal_mode=WAL) and schema migration idempotency.
3. Idempotent /undo: double-undo, 404/already-deleted target tolerance, and LIFO ordering.
4. SPARK mode state transitions: dry, confirm, live.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.handlers import Decision, decide, handle_undo_command
from src.utils.deduplication import MessageDeduplicator


def test_wal_mode_and_all_six_tables_created(tmp_path):
    """Verify that _init_db enables WAL journal mode and creates all 6 canonical tables."""
    db_file = str(tmp_path / "test_wal_state.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    conn = sqlite3.connect(db_file)
    try:
        # 1. Verify WAL mode
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert journal_mode.lower() == "wal", f"Expected WAL mode, got {journal_mode}"

        # 2. Verify all 6 tables exist (+ timetable_overrides)
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        canonical_tables = {"seen", "chat_state", "llm_budget", "pending", "writes", "meta"}
        for tbl in canonical_tables:
            assert tbl in tables, f"Missing expected canonical table: {tbl}"
        assert "timetable_overrides" in tables
    finally:
        conn.close()


def test_schema_migration_idempotency(tmp_path):
    """Re-running _init_db on populated database must be idempotent and non-destructive."""
    db_file = str(tmp_path / "migration_test.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    # Insert data across all 6 tables
    dedup.mark_processed(chat_id=100, message_id=1, content="hello")
    dedup.update_chat_state(chat_id=100, last_id=42)
    dedup.increment_llm_calls("2026-11-10")
    pid = dedup.add_pending(json.dumps({"intent": "TASK", "summary": "Study"}))
    dedup.record_write("insert", "ev_100", json.dumps({"source": "calendar"}))
    dedup.meta_set("key_1", "val_1")

    # Re-run _init_db multiple times
    dedup._initialized = False
    dedup._init_db()
    dedup._initialized = False
    dedup._init_db()

    # Verify all records survived intact
    assert dedup.is_duplicate(chat_id=100, message_id=1, content="hello") is True
    assert dedup.get_chat_state(100) == 42
    assert dedup.get_llm_calls("2026-11-10") == 1
    assert dedup.get_pending(pid) is not None
    last = dedup.last_write()
    assert last is not None and last[2] == "ev_100"
    assert dedup.meta_get("key_1") == "val_1"


def test_chat_state_monotonic_progression(tmp_path):
    """chat_state updates must use MAX(last_id, excluded.last_id) and preserve maximum ID."""
    db_file = str(tmp_path / "chat_state.db")
    dedup = MessageDeduplicator(db_path=db_file)

    dedup.update_chat_state(chat_id=500, last_id=10)
    assert dedup.get_chat_state(500) == 10

    # Updating with smaller ID must not regress
    dedup.update_chat_state(chat_id=500, last_id=5)
    assert dedup.get_chat_state(500) == 10

    # Updating with larger ID advances last_id
    dedup.update_chat_state(chat_id=500, last_id=25)
    assert dedup.get_chat_state(500) == 25


def test_seen_table_deduplication_and_ttl(tmp_path):
    """seen table must hash chat_id + message_id + content and respect TTL eviction."""
    db_file = str(tmp_path / "seen.db")
    dedup = MessageDeduplicator(ttl_seconds=2, db_path=db_file)

    assert dedup.is_duplicate(chat_id=1, message_id=100, content="assignment due") is False
    dedup.mark_processed(chat_id=1, message_id=100, content="assignment due")
    assert dedup.is_duplicate(chat_id=1, message_id=100, content="assignment due") is True

    # Different content is not duplicate
    assert dedup.is_duplicate(chat_id=1, message_id=100, content="different text") is False

    # After TTL expiry, entry is evicted and is_duplicate returns False
    time.sleep(2.1)
    assert dedup.is_duplicate(chat_id=1, message_id=100, content="assignment due") is False


def test_pending_state_machine_lifecycle(tmp_path):
    """pending table lifecycle: PENDING -> CLAIMED -> PROCESSED/DISCARDED."""
    db_file = str(tmp_path / "pending.db")
    dedup = MessageDeduplicator(db_path=db_file)

    event_payload = json.dumps({"intent": "ROOM_OVERRIDE", "room": "B-201"})
    pid = dedup.add_pending(event_payload)

    # Initial state
    pending_list = dedup.list_pending()
    assert any(item["id"] == pid for item in pending_list)
    record = dedup.get_pending(pid)
    assert record is not None and record[1] == "PENDING"

    # Atomic claim
    claimed = dedup.claim_pending(pid)
    assert claimed is True
    # Double claim fails
    assert dedup.claim_pending(pid) is False

    # No longer in pending list
    assert not any(item["id"] == pid for item in dedup.list_pending())

    # Finish pending
    dedup.finish_pending(pid, "APPLIED")
    record_after = dedup.get_pending(pid)
    assert record_after is not None and record_after[1] == "APPLIED"


def test_llm_budget_persistence_and_rollover(tmp_path):
    """llm_budget table must persist daily calls and allow incrementing."""
    db_file = str(tmp_path / "llm_budget.db")
    dedup = MessageDeduplicator(db_path=db_file)

    day1 = "2026-11-10"
    day2 = "2026-11-11"

    assert dedup.get_llm_calls(day1) == 0
    assert dedup.increment_llm_calls(day1) == 1
    assert dedup.increment_llm_calls(day1) == 2
    assert dedup.increment_llm_calls(day1) == 3
    assert dedup.get_llm_calls(day1) == 3

    # Day 2 starts at 0
    assert dedup.get_llm_calls(day2) == 0
    assert dedup.increment_llm_calls(day2) == 1
    assert dedup.get_llm_calls(day1) == 3


def test_meta_table_key_value_store(tmp_path):
    """meta table stores key-value pairs and supports updates."""
    db_file = str(tmp_path / "meta.db")
    dedup = MessageDeduplicator(db_path=db_file)

    assert dedup.meta_get("last_heartbeat") is None
    dedup.meta_set("last_heartbeat", "1794318000.0")
    assert dedup.meta_get("last_heartbeat") == "1794318000.0"

    dedup.meta_set("last_heartbeat", "1794319000.0")
    assert dedup.meta_get("last_heartbeat") == "1794319000.0"


def test_timetable_overrides_table(tmp_path):
    """timetable_overrides table CRUD operations."""
    db_file = str(tmp_path / "overrides.db")
    dedup = MessageDeduplicator(db_path=db_file)

    ov_id = dedup.record_override(
        target_date="2026-11-10",
        period=1,
        course_code="25CS3112E",
        course_name="Enterprise Programming",
        room="H-202",
        status="OVERRIDE",
        summary="Shifted to H-202",
    )
    assert ov_id > 0

    overrides = dedup.get_overrides("2026-11-10")
    assert len(overrides) == 1
    assert overrides[0]["room"] == "H-202"
    assert overrides[0]["period"] == 1

    dedup.delete_override(ov_id)
    assert len(dedup.get_overrides("2026-11-10")) == 0


@pytest.mark.asyncio
async def test_undo_idempotent_on_already_undone_write(tmp_path):
    """Calling /undo when last write has already been undone must not crash or re-execute."""
    db_file = str(tmp_path / "undo_idempotent.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        dedup.record_write("insert", "ev_test_1", json.dumps({"source": "calendar"}))
        last = dedup.last_write()
        assert last is not None
        write_id = last[0]

        # First undo
        cal_auth_path = "src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service"
        with (
            patch(cal_auth_path) as mock_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_service = MagicMock()
            mock_auth.return_value = mock_service
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created calendar event.")

        # Invariant: write must now have undone = 1
        with dedup._get_conn() as conn:
            row = conn.execute("SELECT undone FROM writes WHERE id = ?", (write_id,)).fetchone()
            assert row[0] == 1

        # Second undo (no more undone=0 writes)
        with patch("src.notify.bot.bot.send") as mock_send:
            await handle_undo_command({})
            mock_send.assert_called_once_with("⚠️ Nothing to undo.")


@pytest.mark.asyncio
async def test_undo_tolerates_404_already_deleted_calendar_event(tmp_path):
    """If calendar event is already deleted (404), /undo must mark undone=1 cleanly."""
    db_file = str(tmp_path / "undo_404.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        dedup.record_write("insert", "ev_deleted", json.dumps({"source": "calendar"}))
        last = dedup.last_write()
        assert last is not None
        write_id = last[0]

        cal_auth_path = "src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service"
        with (
            patch(cal_auth_path) as mock_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_service = MagicMock()
            mock_service.events().delete.side_effect = Exception(
                "HttpError 404: Resource Not Found"
            )
            mock_auth.return_value = mock_service

            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created calendar event.")

        # Must mark undone=1 despite 404
        with dedup._get_conn() as conn:
            row = conn.execute("SELECT undone FROM writes WHERE id = ?", (write_id,)).fetchone()
            assert row[0] == 1


@pytest.mark.asyncio
async def test_undo_tolerates_404_already_deleted_task(tmp_path):
    """If task is already deleted (404), /undo must mark undone=1 cleanly."""
    db_file = str(tmp_path / "undo_task_404.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        dedup.record_write("insert", "task_deleted", json.dumps({"source": "tasks"}))
        last = dedup.last_write()
        assert last is not None
        write_id = last[0]

        tasks_auth_path = "src.workspace.tasks_sync.tasks_sync.auth.get_tasks_service"
        with (
            patch(tasks_auth_path) as mock_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_service = MagicMock()
            mock_service.tasks().delete.side_effect = Exception("HttpError 404: Task not found")
            mock_auth.return_value = mock_service

            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created task.")

        with dedup._get_conn() as conn:
            row = conn.execute("SELECT undone FROM writes WHERE id = ?", (write_id,)).fetchone()
            assert row[0] == 1


@pytest.mark.asyncio
async def test_undo_lifo_sequence(tmp_path):
    """Multiple writes must be undone in LIFO order (last in, first out)."""
    db_file = str(tmp_path / "undo_lifo.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        # Insert write 1 then write 2
        dedup.record_write("insert", "ev_first", json.dumps({"source": "calendar"}))
        await asyncio.sleep(0.01)
        dedup.record_write("insert", "task_second", json.dumps({"source": "tasks"}))

        # First undo must revert task_second
        tasks_auth_path = "src.workspace.tasks_sync.tasks_sync.auth.get_tasks_service"
        with (
            patch(tasks_auth_path) as mock_tasks_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_ts = MagicMock()
            mock_tasks_auth.return_value = mock_ts
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created task.")
            mock_ts.tasks().delete.assert_called_once_with(tasklist="@default", task="task_second")

        # Second undo must revert ev_first
        cal_auth_path = "src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service"
        with (
            patch(cal_auth_path) as mock_cal_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_cs = MagicMock()
            mock_cal_auth.return_value = mock_cs
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created calendar event.")

        # Third undo -> nothing to undo
        with patch("src.notify.bot.bot.send") as mock_send:
            await handle_undo_command({})
            mock_send.assert_called_once_with("⚠️ Nothing to undo.")


@pytest.mark.parametrize(
    ("mode", "source", "intent", "verdict", "tt_ready", "expected"),
    [
        # Dry mode: ALWAYS Decision.DRY_RUN
        ("dry", "regex", "ROOM_OVERRIDE", True, True, Decision.DRY_RUN),
        ("dry", "regex", "TASK", True, True, Decision.DRY_RUN),
        ("dry", "gemini", "HOLIDAY", True, True, Decision.DRY_RUN),
        ("dry", "regex", "ROOM_OVERRIDE", False, True, Decision.DRY_RUN),
        # Confirm mode: Valid -> CONFIRM, Invalid -> REVIEW
        ("confirm", "regex", "ROOM_OVERRIDE", True, True, Decision.CONFIRM),
        ("confirm", "regex", "TASK", True, True, Decision.CONFIRM),
        ("confirm", "regex", "ROOM_OVERRIDE", False, True, Decision.REVIEW),
        ("confirm", "gemini", "TASK", False, True, Decision.REVIEW),
        # Live mode: Only regex ROOM_OVERRIDE (with tt_ready), TASK, EXAM_DEADLINE auto-apply
        ("live", "regex", "ROOM_OVERRIDE", True, True, Decision.AUTO),
        ("live", "regex", "TASK", True, True, Decision.AUTO),
        ("live", "regex", "EXAM_DEADLINE", True, True, Decision.AUTO),
        # Live mode: Non-ready timetable -> CONFIRM
        ("live", "regex", "ROOM_OVERRIDE", True, False, Decision.CONFIRM),
        # Live mode: Gemini sources -> CONFIRM
        ("live", "gemini", "ROOM_OVERRIDE", True, True, Decision.CONFIRM),
        ("live", "gemini", "TASK", True, True, Decision.CONFIRM),
        # Live mode: Sensitive intents -> CONFIRM
        ("live", "regex", "HOLIDAY", True, True, Decision.CONFIRM),
        ("live", "regex", "CLASS_CANCELLED", True, True, Decision.CONFIRM),
        # Live mode: Validation failure -> REVIEW (precedence over AUTO)
        ("live", "regex", "ROOM_OVERRIDE", False, True, Decision.REVIEW),
        ("live", "regex", "TASK", False, True, Decision.REVIEW),
    ],
)
def test_spark_mode_exhaustive_state_transitions(mode, source, intent, verdict, tt_ready, expected):
    """Exhaustively verify SPARK mode transitions across all operational matrix entries."""
    decision = decide(
        mode=mode,
        source=source,
        event_intent=intent,
        verdict=verdict,
        timetable_ready=tt_ready,
    )
    assert decision is expected
