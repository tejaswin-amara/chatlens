import json
from unittest.mock import AsyncMock, patch

import pytest

from src.ingestion.handlers import handle_bot_callback


@pytest.fixture
def clean_db():
    from src.utils.db import get_connection
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
        conn.execute("DELETE FROM pending")


@pytest.fixture
def mock_bot():
    with patch("src.notify.bot.bot.answer_callback") as answer:
        with patch("src.notify.bot.bot.edit") as edit:
            yield answer, edit


@pytest.mark.asyncio
async def test_confirm_flow_approve(clean_db, mock_bot):
    import time

    from src.utils.db import get_connection

    wrapper = {
        "event": {
            "intent": "ROOM_OVERRIDE",
            "room": "H-101",
            "summary": "Test",
            "course_name": "DSA",
        },
        "source": "regex",
    }
    with get_connection() as conn:
        pid = conn.execute(
            "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
            (json.dumps(wrapper), time.time()),
        ).lastrowid

    with patch("src.ingestion.handlers.settings.owner_chat_id", 123):
        with patch("src.ingestion.handlers.apply_event", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = ("SUCCESS", ["Calendar Patched"])
            await handle_bot_callback(
                {
                    "from": {"id": 123},
                    "id": "cb_1",
                    "message": {"message_id": 456},
                    "data": f"ok:{pid}",
                }
            )

            mock_apply.assert_called_once()
            ans, edit = mock_bot
            edit.assert_called_once()
            assert "✅ Action applied: ROOM_OVERRIDE" in edit.call_args.args[1]

            # test double tap
            await handle_bot_callback(
                {
                    "from": {"id": 123},
                    "id": "cb_2",
                    "message": {"message_id": 456},
                    "data": f"ok:{pid}",
                }
            )
            # should tell it was already handled
            assert edit.call_count == 2
            assert "already handled" in edit.call_args.args[1]


@pytest.mark.asyncio
async def test_confirm_flow_ignore(clean_db, mock_bot):
    import time

    from src.utils.db import get_connection

    wrapper = {
        "event": {
            "intent": "ROOM_OVERRIDE",
            "room": "H-101",
            "summary": "Test",
            "course_name": "DSA",
        },
        "source": "regex",
    }
    with get_connection() as conn:
        pid = conn.execute(
            "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
            (json.dumps(wrapper), time.time()),
        ).lastrowid

    with patch("src.ingestion.handlers.settings.owner_chat_id", 123):
        with patch("src.ingestion.handlers.apply_event", new_callable=AsyncMock) as mock_apply:
            await handle_bot_callback(
                {
                    "from": {"id": 123},
                    "id": "cb_1",
                    "message": {"message_id": 456},
                    "data": f"no:{pid}",
                }
            )

            mock_apply.assert_not_called()
            ans, edit = mock_bot
            edit.assert_called_once()
            assert "❌ Action ignored." in edit.call_args.args[1]


@pytest.mark.asyncio
async def test_confirm_flow_expired(clean_db, mock_bot):
    import time

    from src.utils.db import get_connection

    wrapper = {
        "event": {
            "intent": "ROOM_OVERRIDE",
            "room": "H-101",
            "summary": "Test",
            "course_name": "DSA",
        },
        "source": "regex",
    }
    with get_connection() as conn:
        pid = conn.execute(
            "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
            (json.dumps(wrapper), time.time() - 87000),
        ).lastrowid

    with patch("src.ingestion.handlers.settings.owner_chat_id", 123):
        await handle_bot_callback(
            {"from": {"id": 123}, "id": "cb_1", "message": {"message_id": 456}, "data": f"ok:{pid}"}
        )

        ans, edit = mock_bot
        edit.assert_called_once()
        assert "has expired" in edit.call_args.args[1]


@pytest.mark.asyncio
async def test_confirm_flow_non_owner(clean_db, mock_bot):
    import time

    from src.utils.db import get_connection

    wrapper = {
        "event": {
            "intent": "ROOM_OVERRIDE",
            "room": "H-101",
            "summary": "Test",
            "course_name": "DSA",
        },
        "source": "regex",
    }
    with get_connection() as conn:
        pid = conn.execute(
            "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
            (json.dumps(wrapper), time.time()),
        ).lastrowid

    with patch("src.ingestion.handlers.settings.owner_chat_id", 123):
        with patch("src.ingestion.handlers.apply_event", new_callable=AsyncMock) as mock_apply:
            await handle_bot_callback(
                {
                    "from": {"id": 999},  # Non-owner
                    "id": "cb_1",
                    "message": {"message_id": 456},
                    "data": f"ok:{pid}",
                }
            )

            mock_apply.assert_not_called()
            ans, edit = mock_bot
            edit.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_flow_failed_write(clean_db, mock_bot):
    import time

    from src.utils.db import get_connection

    wrapper = {
        "event": {
            "intent": "ROOM_OVERRIDE",
            "room": "H-101",
            "summary": "Test",
            "course_name": "DSA",
        },
        "source": "regex",
    }
    with get_connection() as conn:
        pid = conn.execute(
            "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
            (json.dumps(wrapper), time.time()),
        ).lastrowid

    with patch("src.ingestion.handlers.settings.owner_chat_id", 123):
        with patch("src.ingestion.handlers.apply_event", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = ("FAILED: Network error", [])
            await handle_bot_callback(
                {
                    "from": {"id": 123},
                    "id": "cb_1",
                    "message": {"message_id": 456},
                    "data": f"ok:{pid}",
                }
            )

            ans, edit = mock_bot
            edit.assert_called_once()
            assert "Status: FAILED: Network error" in edit.call_args.args[1]


@pytest.mark.asyncio
async def test_confirm_flow_missing_pending_row(clean_db, mock_bot):
    with patch("src.ingestion.handlers.settings.owner_chat_id", 123):
        await handle_bot_callback(
            {
                "from": {"id": 123},
                "id": "cb_1",
                "message": {"message_id": 456},
                "data": "ok:999",  # doesn't exist
            }
        )
        ans, edit = mock_bot
        edit.assert_called_once()
        assert "not found" in edit.call_args.args[1]


@pytest.mark.asyncio
async def test_confirm_flow_unsupported_data(clean_db, mock_bot):
    with patch("src.ingestion.handlers.settings.owner_chat_id", 123):
        await handle_bot_callback(
            {
                "from": {"id": 123},
                "id": "cb_1",
                "message": {"message_id": 456},
                "data": "unknown:123",
            }
        )
        ans, edit = mock_bot
        edit.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_flow_bot_edit_without_msg_id(clean_db, mock_bot):
    import time

    from src.utils.db import get_connection

    wrapper = {
        "event": {
            "intent": "ROOM_OVERRIDE",
            "room": "H-101",
            "summary": "Test",
            "course_name": "DSA",
        },
        "source": "regex",
    }
    with get_connection() as conn:
        pid = conn.execute(
            "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
            (json.dumps(wrapper), time.time()),
        ).lastrowid

    with patch("src.ingestion.handlers.settings.owner_chat_id", 123):
        with patch("src.ingestion.handlers.apply_event", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = ("SUCCESS", [])
            await handle_bot_callback(
                {
                    "from": {"id": 123},
                    "id": "cb_1",
                    # no message object
                    "data": f"ok:{pid}",
                }
            )

            mock_apply.assert_called_once()
            ans, edit = mock_bot
            edit.assert_not_called()


@pytest.mark.asyncio
async def test_apply_event_writes_audit():
    # Directly test apply_event writes audit
    with patch("src.workspace.sheets_logger.sheets_logger.append_audit_log") as mock_audit:
        with patch("src.workspace.tasks_sync.tasks_sync.create_task"):
            from src.ingestion.handlers import apply_event
            from src.parsing.schemas import ExtractedAcademicEvent

            event = ExtractedAcademicEvent(intent="TASK", summary="Test Task")
            await apply_event(event)
            mock_audit.assert_called_once()
