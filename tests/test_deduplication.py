"""Unit tests for SQLite schema enhancements, composite indexes, and Outbox/Inbox bridge."""

import sqlite3

import pytest

from src.utils.deduplication import MessageDeduplicator


def test_schema_indexes_and_tables(tmp_path):
    """Verify composite indexes and chatlens_outbox / chatlens_inbox tables are created."""
    db_path = str(tmp_path / "test_schema.db")
    dedup = MessageDeduplicator(db_path=db_path)
    dedup._ensure_db()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Verify tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "chatlens_outbox" in tables
    assert "chatlens_inbox" in tables
    assert "timetable_overrides" in tables
    assert "pending" in tables
    assert "writes" in tables

    # Verify composite indexes exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}
    assert "idx_pending_status_created" in indexes
    assert "idx_writes_undone_ts" in indexes
    assert "idx_overrides_date_period" in indexes
    assert "idx_outbox_processed_ts" in indexes
    assert "idx_inbox_status_ts" in indexes

    conn.close()


def test_outbox_event_lifecycle(tmp_path):
    """Verify adding, listing, and marking processed on outbox events."""
    db_path = str(tmp_path / "test_outbox.db")
    dedup = MessageDeduplicator(db_path=db_path)

    # Initially empty
    assert dedup.list_outbox_events() == []

    # Add outbox event
    payload = {
        "chat_id": -100123456,
        "course_name": "DLAC",
        "room": "H-005",
        "intent": "ROOM_OVERRIDE",
    }
    event_id = dedup.add_outbox_event("academic.room_override", payload)
    assert event_id > 0

    # Retrieve unprocessed
    events = dedup.list_outbox_events(unprocessed_only=True)
    assert len(events) == 1
    assert events[0]["id"] == event_id
    assert events[0]["event_type"] == "academic.room_override"
    assert events[0]["payload"] == payload
    assert events[0]["processed"] == 0

    # Mark processed
    dedup.mark_outbox_processed(event_id)
    assert dedup.list_outbox_events(unprocessed_only=True) == []

    # All events list still retains it
    all_events = dedup.list_outbox_events(unprocessed_only=False)
    assert len(all_events) == 1
    assert all_events[0]["processed"] == 1


def test_inbox_command_lifecycle(tmp_path):
    """Verify polling and updating inbox commands."""
    db_path = str(tmp_path / "test_inbox.db")
    dedup = MessageDeduplicator(db_path=db_path)
    dedup._ensure_db()

    conn = sqlite3.connect(db_path)
    # Simulate web platform inserting an inbox command
    conn.execute(
        """
        INSERT INTO chatlens_inbox (ts, command, payload_json, status)
        VALUES (?, ?, ?, 'PENDING')
        """,
        (1700000000.0, "OVERRIDE_ROOM", '{"course": "DLAC", "room": "HC-15C"}'),
    )
    conn.commit()
    conn.close()

    # Poll inbox commands
    commands = dedup.poll_inbox_commands(limit=10)
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd["command"] == "OVERRIDE_ROOM"
    assert cmd["payload"] == {"course": "DLAC", "room": "HC-15C"}
    assert cmd["status"] == "PENDING"

    # Mark command processed
    dedup.mark_inbox_processed(cmd["id"], "COMPLETED")
    assert dedup.poll_inbox_commands() == []


@pytest.mark.asyncio
async def test_process_message_emits_outbox_event(tmp_path, monkeypatch):
    """Verify that process_message emits an outbox event for parsed academic messages."""
    from datetime import datetime
    from unittest.mock import AsyncMock, MagicMock

    from src.config import settings
    from src.ingestion.handlers import process_message
    from src.utils import clock

    test_db = str(tmp_path / "test_proc_outbox.db")
    dedup = MessageDeduplicator(db_path=test_db)
    monkeypatch.setattr("src.ingestion.handlers.deduplicator", dedup)
    monkeypatch.setattr("src.utils.deduplication.deduplicator", dedup)
    monkeypatch.setattr(settings, "spark_db", test_db)
    monkeypatch.setattr(settings, "spark_mode", "dry")

    mock_client = AsyncMock()
    mock_msg = MagicMock()
    mock_msg.id = 1001
    mock_msg.text = "Tomorrow DLAC class moved to H-005 period 1"
    mock_msg.date = datetime(2026, 10, 23, 10, 0, 0, tzinfo=clock.IST)
    mock_msg.voice = None
    mock_msg.document = None
    mock_msg.photo = None
    mock_msg.sender_id = 999
    mock_msg.get_chat = AsyncMock(return_value=MagicMock(title="CS Dept", username=None))
    mock_msg.get_sender = AsyncMock(return_value=MagicMock(first_name="Prof", last_name="Sharma"))

    await process_message(mock_client, -100999888, mock_msg)

    # Check that outbox has recorded the event
    outbox_events = dedup.list_outbox_events()
    assert len(outbox_events) == 1
    ev = outbox_events[0]
    assert "room_override" in ev["event_type"].lower()
    assert ev["payload"]["room"] == "H-005"
    assert ev["payload"]["chat_name"] == "CS Dept"
    assert ev["payload"]["decision"] == "DRY_RUN"


def test_prune_expired_cleans_seen_and_processed_events(tmp_path):
    import time

    from src.utils.deduplication import MessageDeduplicator

    db_file = str(tmp_path / "prune_test.db")
    dedup = MessageDeduplicator(ttl_seconds=3600, db_path=db_file)

    now = time.time()
    # Insert old seen row (2 hours ago) and fresh seen row (10 seconds ago)
    with dedup._get_conn() as conn:
        conn.execute("INSERT INTO seen (key, ts) VALUES (?, ?)", ("old_hash", now - 7200))
        conn.execute("INSERT INTO seen (key, ts) VALUES (?, ?)", ("fresh_hash", now - 10))

        # Insert old processed outbox event (40 days ago) and unprocessed outbox event
        insert_outbox = (
            "INSERT INTO chatlens_outbox (ts, event_type, payload_json, processed) "
            "VALUES (?, ?, ?, ?)"
        )
        conn.execute(insert_outbox, (now - (86400 * 40), "test_old", "{}", 1))
        conn.execute(insert_outbox, (now - 10, "test_fresh", "{}", 0))

    # Prune
    pruned = dedup.prune_expired()
    assert pruned == 1  # 1 old seen hash deleted

    with dedup._get_conn() as conn:
        keys = [r[0] for r in conn.execute("SELECT key FROM seen").fetchall()]
        assert "old_hash" not in keys
        assert "fresh_hash" in keys

        outbox_rows = conn.execute("SELECT event_type FROM chatlens_outbox").fetchall()
        outbox_types = [r[0] for r in outbox_rows]
        assert "test_old" not in outbox_types
        assert "test_fresh" in outbox_types
