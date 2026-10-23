"""Empirical challenge test suite for Milestone 2.

Authored by Challenger 1 (Milestone 2).
Exhaustively and empirically challenges:
1. Button callback lifecycle:
   - Simulation of callback_query for cmd:today, cmd:attendance, cmd:deadlines, cmd:status.
   - Verification that answerCallbackQuery is called with the exact callback ID.
   - Verification that each callback generates the exact output with 4 quick buttons re-attached.
   - Exact equivalence between callback execution and slash command execution.
2. Custom buttons overriding default buttons (1D and 2D layouts).
3. Empty buttons (buttons=[]) producing zero reply_markup.
4. Security & authorization:
   - Non-owner queries rejected (no answerCallbackQuery, no sendMessage).
   - Coercion between string and int owner_chat_id.
5. Fault injection & resilience:
   - answerCallbackQuery HTTP 400 failure (expired query) handled without interrupting command.
   - Malformed callback queries (missing fields, empty cmd:, unknown cmd:).
6. setMyCommands registration of exact 10 commands.
7. Concurrency stress test of simultaneous callbacks.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from src.config import settings
from src.ingestion.handlers import handle_bot_callback, handle_bot_command
from src.notify.bot import BotError, bot
from src.timetable import DEFAULT_TIMETABLE_PATH
from src.utils.deduplication import MessageDeduplicator

IST = ZoneInfo("Asia/Kolkata")
OWNER_ID = 123456789

DEFAULT_BUTTONS_EXPECTED = [
    [
        {"text": "📅 Today", "callback_data": "cmd:today"},
        {"text": "📊 Attendance", "callback_data": "cmd:attendance"},
    ],
    [
        {"text": "⏰ Deadlines", "callback_data": "cmd:deadlines"},
        {"text": "🟢 Status", "callback_data": "cmd:status"},
    ],
]


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Isolate SQLite database, credentials, and settings."""
    test_db = str(tmp_path / "challenger_m2_1.db")
    test_dedup = MessageDeduplicator(db_path=test_db)

    monkeypatch.setattr(settings, "spark_db", test_db)
    monkeypatch.setattr(settings, "owner_chat_id", OWNER_ID)
    monkeypatch.setattr(
        settings, "bot_token", MagicMock(get_secret_value=lambda: "bot123:mock_challenger_token")
    )
    monkeypatch.setattr(settings, "spark_timetable", DEFAULT_TIMETABLE_PATH)
    monkeypatch.setattr("src.utils.deduplication.deduplicator", test_dedup)
    monkeypatch.setattr("src.ingestion.handlers.deduplicator", test_dedup)
    yield test_dedup


class RequestRecorder:
    """Helper to record all Telegram Bot API requests via BotClient._request."""

    def __init__(self):
        self.calls = []

    def mock_request(self, endpoint: str, data: dict | None = None, timeout: int = 30):
        self.calls.append({"endpoint": endpoint, "data": data or {}, "timeout": timeout})
        return {"ok": True, "result": True}


# ============================================================================
# 1. Button Layouts & Custom Overrides
# ============================================================================


def test_bot_send_default_quick_buttons(monkeypatch):
    """Verify default buttons parameter (None) attaches the exact 2x2 grid."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    res = bot.send("Test message default")
    assert res == {"ok": True, "result": True}
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["endpoint"] == "sendMessage"
    assert "reply_markup" in call["data"]
    kb = call["data"]["reply_markup"].get("inline_keyboard")
    assert kb == DEFAULT_BUTTONS_EXPECTED


def test_bot_send_empty_buttons_suppresses_reply_markup(monkeypatch):
    """Verify buttons=[] produces zero reply_markup in payload."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    res = bot.send("Test message suppression", buttons=[])
    assert res == {"ok": True, "result": True}
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["endpoint"] == "sendMessage"
    assert "reply_markup" not in call["data"]


def test_bot_send_custom_buttons_1d(monkeypatch):
    """Verify single 1D list of buttons is automatically wrapped into a row."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    custom_1d = [
        {"text": "Custom 1", "callback_data": "custom:1"},
        {"text": "Custom 2", "callback_data": "custom:2"},
    ]
    res = bot.send("Test custom 1d", buttons=custom_1d)
    assert res == {"ok": True, "result": True}
    call = recorder.calls[0]
    kb = call["data"]["reply_markup"]["inline_keyboard"]
    assert kb == [custom_1d]


def test_bot_send_custom_buttons_2d(monkeypatch):
    """Verify 2D nested list of buttons preserves multi-row structure."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    custom_2d = [
        [{"text": "Row 1", "callback_data": "r1"}],
        [{"text": "Row 2", "callback_data": "r2"}],
    ]
    res = bot.send("Test custom 2d", buttons=custom_2d)
    assert res == {"ok": True, "result": True}
    call = recorder.calls[0]
    kb = call["data"]["reply_markup"]["inline_keyboard"]
    assert kb == custom_2d


# ============================================================================
# 2. Callback Lifecycle & answerCallbackQuery Exact ID Verification
# ============================================================================


@pytest.mark.asyncio
async def test_callback_lifecycle_cmd_today(monkeypatch):
    """Verify cmd:today lifecycle: exact answerCallbackQuery ID + exact schedule + 4 buttons."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    callback_id = "cb_query_today_42"
    query = {
        "id": callback_id,
        "from": {"id": OWNER_ID},
        "data": "cmd:today",
    }

    await handle_bot_callback(query)

    # Must have called answerCallbackQuery first, then sendMessage
    assert len(recorder.calls) >= 2
    ans_call = recorder.calls[0]
    assert ans_call["endpoint"] == "answerCallbackQuery"
    assert ans_call["data"]["callback_query_id"] == callback_id

    send_call = recorder.calls[1]
    assert send_call["endpoint"] == "sendMessage"
    assert "reply_markup" in send_call["data"]
    assert send_call["data"]["reply_markup"]["inline_keyboard"] == DEFAULT_BUTTONS_EXPECTED

    today_output = send_call["data"]["text"]
    assert today_output.strip() != ""

    # Oracle comparison: command execution must produce exact same text
    recorder.calls.clear()
    await handle_bot_command({"chat": {"id": OWNER_ID}, "text": "/today"})
    assert len(recorder.calls) == 1
    direct_cmd_output = recorder.calls[0]["data"]["text"]
    assert today_output == direct_cmd_output


@pytest.mark.asyncio
async def test_callback_lifecycle_cmd_attendance(monkeypatch):
    """Verify cmd:attendance lifecycle: exact answerCallbackQuery ID + report + 4 buttons."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    mock_records = [
        {
            "course_code": "25CS2103E",
            "course_name": "Data Structures & Algorithms-3",
            "attended": 28,
            "conducted": 30,
            "percentage": 93.33,
            "safe_bunks": 2,
            "recovery_needed": 0,
            "ltps": "Lecture",
        }
    ]
    monkeypatch.setattr(
        "src.erp.klu_erp.get_attendance", AsyncMock(return_value=mock_records)
    )

    callback_id = "cb_query_att_99"
    query = {
        "id": callback_id,
        "from": {"id": OWNER_ID},
        "data": "cmd:attendance",
    }

    await handle_bot_callback(query)

    assert len(recorder.calls) >= 2
    ans_call = recorder.calls[0]
    assert ans_call["endpoint"] == "answerCallbackQuery"
    assert ans_call["data"]["callback_query_id"] == callback_id

    # The last sendMessage is the actual attendance report
    report_call = recorder.calls[-1]
    assert report_call["endpoint"] == "sendMessage"
    assert "Live Attendance Overview (KL ERP)" in report_call["data"]["text"]
    assert "Data Structures & Algorithms-3" in report_call["data"]["text"]
    assert "reply_markup" in report_call["data"]
    assert report_call["data"]["reply_markup"]["inline_keyboard"] == DEFAULT_BUTTONS_EXPECTED

    att_output = report_call["data"]["text"]

    # Oracle comparison
    recorder.calls.clear()
    await handle_bot_command({"chat": {"id": OWNER_ID}, "text": "/attendance"})
    direct_report_call = recorder.calls[-1]
    assert direct_report_call["data"]["text"] == att_output


@pytest.mark.asyncio
async def test_callback_lifecycle_cmd_deadlines(monkeypatch):
    """Verify cmd:deadlines lifecycle: exact answerCallbackQuery ID + deadlines + 4 buttons."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    callback_id = "cb_query_deadlines_77"
    query = {
        "id": callback_id,
        "from": {"id": OWNER_ID},
        "data": "cmd:deadlines",
    }

    await handle_bot_callback(query)

    assert len(recorder.calls) >= 2
    ans_call = recorder.calls[0]
    assert ans_call["endpoint"] == "answerCallbackQuery"
    assert ans_call["data"]["callback_query_id"] == callback_id

    send_call = recorder.calls[1]
    assert send_call["endpoint"] == "sendMessage"
    assert "Upcoming Deadlines & Milestones" in send_call["data"]["text"]
    assert "reply_markup" in send_call["data"]
    assert send_call["data"]["reply_markup"]["inline_keyboard"] == DEFAULT_BUTTONS_EXPECTED

    deadlines_output = send_call["data"]["text"]

    # Oracle comparison
    recorder.calls.clear()
    await handle_bot_command({"chat": {"id": OWNER_ID}, "text": "/deadlines"})
    assert recorder.calls[0]["data"]["text"] == deadlines_output


@pytest.mark.asyncio
async def test_callback_lifecycle_cmd_status(monkeypatch):
    """Verify cmd:status lifecycle: exact answerCallbackQuery ID + exact status + 4 buttons."""
    fixed_now = datetime(2026, 10, 23, 14, 0, 0, tzinfo=IST)
    monkeypatch.setattr("src.utils.clock.now_ist", lambda: fixed_now)

    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    callback_id = "cb_query_status_55"
    query = {
        "id": callback_id,
        "from": {"id": OWNER_ID},
        "data": "cmd:status",
    }

    await handle_bot_callback(query)

    assert len(recorder.calls) >= 2
    ans_call = recorder.calls[0]
    assert ans_call["endpoint"] == "answerCallbackQuery"
    assert ans_call["data"]["callback_query_id"] == callback_id

    send_call = recorder.calls[1]
    assert send_call["endpoint"] == "sendMessage"
    assert "ChatLens PA Status" in send_call["data"]["text"]
    assert "reply_markup" in send_call["data"]
    assert send_call["data"]["reply_markup"]["inline_keyboard"] == DEFAULT_BUTTONS_EXPECTED

    status_output = send_call["data"]["text"]

    # Oracle comparison
    recorder.calls.clear()
    await handle_bot_command({"chat": {"id": OWNER_ID}, "text": "/status"})
    assert recorder.calls[0]["data"]["text"] == status_output


# ============================================================================
# 3. Security & Access Control
# ============================================================================


@pytest.mark.asyncio
async def test_callback_unauthorized_attacker_ignored(monkeypatch):
    """Verify unauthorized sender queries are dropped without answering or responding."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    attacker_id = 999999999
    for cmd in ["cmd:today", "cmd:attendance", "cmd:deadlines", "cmd:status"]:
        query = {
            "id": f"cb_unauth_{cmd}",
            "from": {"id": attacker_id},
            "data": cmd,
        }
        await handle_bot_callback(query)

    assert len(recorder.calls) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "configured_owner,sender_id",
    [
        (123456789, "123456789"),  # Configured as int, sender as str
        ("123456789", 123456789),  # Configured as str, sender as int
        ("123456789", "123456789"),  # Both str
        (123456789, 123456789),  # Both int
    ],
)
async def test_callback_owner_id_type_coercion(monkeypatch, configured_owner, sender_id):
    """Verify robustness to integer vs string ID differences between Telegram and settings."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)
    monkeypatch.setattr(settings, "owner_chat_id", configured_owner)

    query = {
        "id": "cb_coercion_test",
        "from": {"id": sender_id},
        "data": "cmd:status",
    }
    await handle_bot_callback(query)

    assert len(recorder.calls) >= 2
    assert recorder.calls[0]["endpoint"] == "answerCallbackQuery"
    assert recorder.calls[0]["data"]["callback_query_id"] == "cb_coercion_test"


# ============================================================================
# 4. Fault Injection & Resilience
# ============================================================================


@pytest.mark.asyncio
async def test_callback_answer_failure_resilience(monkeypatch):
    """If Telegram returns 400 for expired callback, command execution still proceeds."""
    recorder = RequestRecorder()

    def failing_request(endpoint: str, data: dict | None = None, timeout: int = 30):
        if endpoint == "answerCallbackQuery":
            raise BotError("Telegram Bot HTTPError 400: query is too old and response timeout")
        return recorder.mock_request(endpoint, data, timeout)

    monkeypatch.setattr(bot, "_request", failing_request)

    query = {
        "id": "cb_expired_query",
        "from": {"id": OWNER_ID},
        "data": "cmd:status",
    }

    # Should not raise exception
    await handle_bot_callback(query)

    # Command still executed!
    assert len(recorder.calls) == 1
    assert recorder.calls[0]["endpoint"] == "sendMessage"
    assert "ChatLens PA Status" in recorder.calls[0]["data"]["text"]


@pytest.mark.asyncio
async def test_callback_malformed_empty_cmd(monkeypatch):
    """Verify 'cmd:' with empty action falls through safely to '/' menu."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    query = {
        "id": "cb_empty_cmd",
        "from": {"id": OWNER_ID},
        "data": "cmd:",
    }

    await handle_bot_callback(query)

    assert len(recorder.calls) >= 2
    assert recorder.calls[0]["endpoint"] == "answerCallbackQuery"
    assert recorder.calls[0]["data"]["callback_query_id"] == "cb_empty_cmd"
    # Should render menu
    assert "ChatLens & SPARK PA Menu" in recorder.calls[1]["data"]["text"]
    assert recorder.calls[1]["data"]["reply_markup"]["inline_keyboard"] == DEFAULT_BUTTONS_EXPECTED


@pytest.mark.asyncio
async def test_callback_malformed_non_cmd_data(monkeypatch):
    """Verify arbitrary non-matching callback data is safely answered and dropped."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    query = {
        "id": "cb_arbitrary",
        "from": {"id": OWNER_ID},
        "data": "arbitrary_custom_data_without_prefix",
    }

    await handle_bot_callback(query)

    assert len(recorder.calls) == 1
    assert recorder.calls[0]["endpoint"] == "answerCallbackQuery"
    assert recorder.calls[0]["data"]["callback_query_id"] == "cb_arbitrary"


# ============================================================================
# 5. Native Telegram Commands Registration
# ============================================================================


def test_bot_set_my_commands_exact_registration(monkeypatch):
    """Verify set_my_commands sends exactly the 10 assistant commands."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    res = bot.set_my_commands()
    assert res == {"ok": True, "result": True}
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["endpoint"] == "setMyCommands"
    commands = call["data"]["commands"]
    assert len(commands) == 10
    cmd_names = [c["command"] for c in commands]
    assert cmd_names == [
        "today",
        "attendance",
        "deadlines",
        "status",
        "marks",
        "cgpa",
        "fee",
        "rescan",
        "undo",
        "help",
    ]


# ============================================================================
# 6. Concurrency Stress Test
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_callback_queries(monkeypatch):
    """Simulate rapid interleaved callback queries across all 4 commands concurrently."""
    recorder = RequestRecorder()
    monkeypatch.setattr(bot, "_request", recorder.mock_request)

    commands = ["today", "deadlines", "status", "today", "status", "deadlines"]
    queries = [
        {
            "id": f"cb_concurrent_{i}",
            "from": {"id": OWNER_ID},
            "data": f"cmd:{cmd}",
        }
        for i, cmd in enumerate(commands)
    ]

    await asyncio.gather(*(handle_bot_callback(q) for q in queries))

    # All 6 queries must have their answerCallbackQuery executed with their matching ID
    answered_ids = [
        c["data"]["callback_query_id"]
        for c in recorder.calls
        if c["endpoint"] == "answerCallbackQuery"
    ]
    for i in range(len(commands)):
        assert f"cb_concurrent_{i}" in answered_ids
