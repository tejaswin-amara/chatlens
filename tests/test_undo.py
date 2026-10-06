import json
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.handlers import handle_undo_command


@pytest.fixture
def clean_db():
    from src.utils.db import get_connection

    # Ensure tables exist
    from src.utils.deduplication import deduplicator

    deduplicator._init_db()
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS writes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL,
                kind TEXT,
                event_id TEXT,
                prior_json TEXT,
                undone INTEGER DEFAULT 0
            )
            """
        )
        conn.execute("DELETE FROM writes")


@pytest.mark.asyncio
async def test_undo_nothing_to_undo(clean_db):
    with patch("src.notify.bot.bot.send") as mock_send:
        await handle_undo_command({})
        mock_send.assert_called_once_with("⚠️ Nothing to undo.")


@pytest.mark.asyncio
async def test_undo_patch_body_incl_marker_clear(clean_db):
    import time

    prior = {
        "location": "H-106",
        "reminders": {"useDefault": True},
        "extendedProperties": {"private": {"spark_override": "0"}},
        "summary": "Original Title",
    }
    with patch("src.utils.db.get_connection"):
        # We need to insert a real row
        pass

    from src.utils.db import get_connection

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
            (time.time(), "patch", "ev_1", json.dumps(prior)),
        )

    with patch("src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service") as mock_auth:
        mock_service = MagicMock()
        mock_auth.return_value = mock_service

        with patch("src.notify.bot.bot.send") as mock_send:
            await handle_undo_command({})

            mock_service.events().patch.assert_called_once()
            args, kwargs = mock_service.events().patch.call_args
            assert kwargs["eventId"] == "ev_1"
            assert kwargs["body"]["location"] == "H-106"
            assert kwargs["body"]["summary"] == "Original Title"

            mock_send.assert_called_once_with("✅ Undid patch on event `ev_1`.")

            with get_connection() as conn:
                row = conn.execute("SELECT undone FROM writes LIMIT 1").fetchone()
                assert row[0] == 1


@pytest.mark.asyncio
async def test_undo_delete_event(clean_db):
    import time

    from src.utils.db import get_connection

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
            (time.time(), "insert", "ev_2", json.dumps({"source": "calendar"})),
        )

    with patch("src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service") as mock_auth:
        mock_service = MagicMock()
        mock_auth.return_value = mock_service

        with patch("src.notify.bot.bot.send") as mock_send:
            await handle_undo_command({})

            mock_service.events().delete.assert_called_once_with(
                calendarId="primary", eventId="ev_2"
            )
            mock_send.assert_called_once_with("✅ Deleted created calendar event.")

            with get_connection() as conn:
                row = conn.execute("SELECT undone FROM writes LIMIT 1").fetchone()
                assert row[0] == 1


@pytest.mark.asyncio
async def test_undo_delete_task(clean_db):
    import time

    from src.utils.db import get_connection

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
            (time.time(), "insert", "task_1", json.dumps({"source": "tasks"})),
        )

    with patch("src.workspace.tasks_sync.tasks_sync.auth.get_tasks_service") as mock_auth:
        mock_service = MagicMock()
        mock_auth.return_value = mock_service

        with patch("src.notify.bot.bot.send") as mock_send:
            await handle_undo_command({})

            mock_service.tasks().delete.assert_called_once_with(tasklist="@default", task="task_1")
            mock_send.assert_called_once_with("✅ Deleted created task.")

            with get_connection() as conn:
                row = conn.execute("SELECT undone FROM writes LIMIT 1").fetchone()
                assert row[0] == 1


@pytest.mark.asyncio
async def test_undo_failure_keeps_undone_0(clean_db):
    import time

    from src.utils.db import get_connection

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
            (time.time(), "insert", "ev_err", json.dumps({"source": "calendar"})),
        )

    with patch("src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service") as mock_auth:
        mock_service = MagicMock()
        # Make delete raise an exception
        mock_service.events().delete.side_effect = Exception("API Error")
        mock_auth.return_value = mock_service

        with patch("src.notify.bot.bot.send") as mock_send:
            await handle_undo_command({})

            mock_send.assert_called_once_with("❌ Undo failed: API Error")

            with get_connection() as conn:
                row = conn.execute("SELECT undone FROM writes LIMIT 1").fetchone()
                # Should still be 0
                assert row[0] == 0


@pytest.mark.asyncio
async def test_undo_already_undone_ignored(clean_db):
    import time

    from src.utils.db import get_connection

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO writes (ts, kind, event_id, prior_json, undone) VALUES (?, ?, ?, ?, ?)",
            (time.time(), "insert", "ev_done", json.dumps({"source": "calendar"}), 1),
        )

    with patch("src.notify.bot.bot.send") as mock_send:
        await handle_undo_command({})
        mock_send.assert_called_once_with("⚠️ Nothing to undo.")


@pytest.mark.asyncio
async def test_undo_skips_unknown_source(clean_db):
    import time

    from src.utils.db import get_connection

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
            (time.time(), "insert", "ev_ukn", json.dumps({"source": "unknown"})),
        )

    with patch("src.notify.bot.bot.send"):
        await handle_undo_command({})
        # The code just updates the row and doesn't actually hit an exception if it doesn't match calendar or tasks
        with get_connection() as conn:
            row = conn.execute("SELECT undone FROM writes LIMIT 1").fetchone()
            assert row[0] == 1


@pytest.mark.asyncio
async def test_undo_missing_prior_keys(clean_db):
    import time

    from src.utils.db import get_connection

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
            (time.time(), "patch", "ev_patch2", json.dumps({})),
        )

    with patch("src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service") as mock_auth:
        mock_service = MagicMock()
        mock_auth.return_value = mock_service

        with patch("src.notify.bot.bot.send"):
            await handle_undo_command({})

            mock_service.events().patch.assert_called_once()
            args, kwargs = mock_service.events().patch.call_args
            assert kwargs["body"]["location"] is None
            assert "summary" not in kwargs["body"]

            with get_connection() as conn:
                row = conn.execute("SELECT undone FROM writes LIMIT 1").fetchone()
                assert row[0] == 1
