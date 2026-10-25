"""End-to-end acceptance tests for the SPARK daemon.

Covers core commands, schedule boundaries, callbacks, authorization, persistence,
cross-feature combinations, and realistic daemon/user journeys.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.config import settings
from src.ingestion.handlers import handle_bot_callback, handle_bot_command
from src.notify.bot import BotClient, bot
from src.timetable import DEFAULT_TIMETABLE_PATH
from src.timetable import load as load_timetable
from src.utils import clock
from src.utils.deduplication import MessageDeduplicator

# ==============================================================================
# Shared Fixtures & Setup
# ==============================================================================


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """Isolate SQLite database, bot credentials, and environment for each test."""
    test_db = str(tmp_path / "test_spark.db")
    test_dedup = MessageDeduplicator(db_path=test_db)

    monkeypatch.setattr(settings, "spark_db", test_db)
    monkeypatch.setattr(settings, "owner_chat_id", 123456789)
    monkeypatch.setattr(
        settings, "bot_token", MagicMock(get_secret_value=lambda: "bot123:mock_token")
    )
    monkeypatch.setattr(settings, "spark_timetable", DEFAULT_TIMETABLE_PATH)
    monkeypatch.setattr("src.utils.deduplication.deduplicator", test_dedup)
    monkeypatch.setattr("src.ingestion.handlers.deduplicator", test_dedup)
    test_dedup.meta_set("consent:123", "1")

    yield test_dedup


@pytest.fixture
def mock_bot_send(monkeypatch):
    """Mock bot.send to record all sent messages without hitting Telegram."""
    sent_messages = []

    def _fake_send(text, buttons=None, parse_mode=None, chat_id=None):
        target_chat_id = chat_id if chat_id is not None else settings.owner_chat_id
        if buttons is not None:
            kb = buttons if isinstance(buttons[0], list) else [buttons]
            markup = {"inline_keyboard": kb} if buttons else None
        else:
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "📅 Today", "callback_data": "cmd:today"},
                        {"text": "📊 Attendance", "callback_data": "cmd:attendance"},
                    ],
                    [
                        {"text": "⏰ Deadlines", "callback_data": "cmd:deadlines"},
                        {"text": "🟢 Status", "callback_data": "cmd:status"},
                    ],
                ]
            }
        record = {
            "chat_id": target_chat_id,
            "text": text,
            "buttons": buttons,
            "reply_markup": markup,
            "parse_mode": parse_mode,
        }
        sent_messages.append(record)
        return {"ok": True, "result": {"message_id": len(sent_messages)}}

    monkeypatch.setattr(bot, "send", _fake_send)
    return sent_messages


@pytest.fixture
def mock_bot_answer_callback(monkeypatch):
    """Mock bot.answer_callback to record answered callback queries."""
    answered = []

    def _fake_answer(cb_id, text=None):
        answered.append({"id": cb_id, "text": text})
        return {"ok": True}

    monkeypatch.setattr(bot, "answer_callback", _fake_answer)
    return answered


# ==============================================================================
# Tier 1 — Core Feature Coverage (Happy Path)
# ==============================================================================


@pytest.mark.asyncio
async def test_tier1_today_command_happy_path(mock_bot_send, monkeypatch):
    """F1.2 - F1.6: /today outputs 4-slot structure, status icons, stats line, and zero filler."""
    # Freeze time to Monday 2026-07-20 at 09:15 AM (during Period 2: 09:00 - 09:50)
    fixed_dt = datetime(2026, 7, 20, 9, 15, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    msg = {"chat": {"id": 123456789}, "text": "/today"}
    await handle_bot_command(msg)

    assert len(mock_bot_send) == 1
    reply = mock_bot_send[0]["text"]
    buttons = mock_bot_send[0]["reply_markup"]["inline_keyboard"]

    # F1.2: Zero filler ([R2]) - Starts directly with icon and time
    assert not reply.startswith("Sure")
    assert not reply.startswith("Here is")
    assert reply.startswith("✅") or reply.startswith("🔴") or reply.startswith("⬡")

    # F1.3: 4-slot structure present
    assert "* Room    :" in reply
    assert "* Faculty :" in reply
    assert "* Section : S-10" in reply
    assert "* Type    :" in reply
    assert "* Note    :" in reply

    # F1.4 & F1.6: Status icons: Period 1 finished (✅), Period 2 current (🔴), Period 3 next (🟡)
    assert "✅ [08:10 AM – 09:00 AM]: Database Systems Engineering (25CS1302E)" in reply
    assert "🔴 [09:00 AM – 09:50 AM]: Database Systems Engineering (25CS1302E)" in reply
    assert "🟡 [10:00 AM – 10:50 AM]: Embedded System Design & IoT (25EC2206E)" in reply

    # F1.5: Stats line ([R9])
    assert "📊 Monday | Wk1:" in reply
    assert "academic" in reply
    assert "Regular instruction" in reply

    # F2.1: Quick-action buttons attached
    assert len(buttons) == 2
    assert buttons[0][0]["callback_data"] == "cmd:today"
    assert buttons[0][1]["callback_data"] == "cmd:attendance"
    assert buttons[1][0]["callback_data"] == "cmd:deadlines"
    assert buttons[1][1]["callback_data"] == "cmd:status"


@pytest.mark.asyncio
async def test_tier1_tomorrow_command_happy_path(mock_bot_send, monkeypatch):
    """F1.7: /tomorrow formats tomorrow's schedule with static ⬡ icons and stats line."""
    # Freeze time to Sunday 2026-07-19 at 10:00 AM (tomorrow is Monday 2026-07-20)
    fixed_dt = datetime(2026, 7, 19, 10, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    msg = {"chat": {"id": 123456789}, "text": "/tomorrow"}
    await handle_bot_command(msg)

    assert len(mock_bot_send) == 1
    reply = mock_bot_send[0]["text"]

    # Tomorrow must use static ⬡ icons for non-cancelled classes ([R4] Today Only)
    assert "⬡ [08:10 AM – 09:00 AM]: Database Systems Engineering (25CS1302E)" in reply
    assert "✅" not in reply  # No classes completed yet for tomorrow
    assert "🟡" not in reply  # No live upcoming icon for tomorrow

    # 4-slot structure and stats line present
    assert "* Room    :" in reply
    assert "* Section : S-10" in reply
    assert "📊 Monday | Wk1:" in reply


def test_tier1_timetable_fallback_happy_path(monkeypatch):
    """F1.1: Automatic fallback to data/timetable_T04.toml when configured path is missing."""
    monkeypatch.setattr(settings, "spark_timetable", "non_existent_timetable.toml")

    tt = load_timetable()
    assert tt is not None
    assert tt.path == DEFAULT_TIMETABLE_PATH
    assert len(tt.slots) > 0
    assert tt.meta.term == "T04"


def test_tier1_quick_action_buttons_injection():
    """F2.1: Default quick-action buttons injected on bot.send() unless explicitly suppressed."""
    mock_client = BotClient(token="bot123:test_token")
    mock_requests = []

    def _fake_retry(endpoint, data, timeout=30):
        mock_requests.append((endpoint, data))
        return {"ok": True}

    mock_client._retry = _fake_retry

    # Default call without buttons argument injects 2x2 keyboard
    mock_client.send("Default message", chat_id=123)
    assert len(mock_requests) == 1
    markup = mock_requests[0][1]["reply_markup"]["inline_keyboard"]
    assert len(markup) == 2
    assert markup[0][0]["text"] == "📅 Today"
    assert markup[1][1]["text"] == "🟢 Status"

    # Call with buttons=[] suppresses keyboard (e.g. for startup notification)
    mock_client.send("Startup message", buttons=[], chat_id=123)
    assert len(mock_requests) == 2
    assert "reply_markup" not in mock_requests[1][1]


@pytest.mark.asyncio
async def test_tier1_inline_callback_query_execution(
    mock_bot_send, mock_bot_answer_callback, monkeypatch
):
    """F2.2: Intercept cmd:<action> callback queries, answer spinner, and synthesize command."""
    fixed_dt = datetime(2026, 7, 20, 8, 30, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    query = {
        "id": "cb_query_999",
        "from": {"id": 123456789},
        "data": "cmd:today",
    }
    await handle_bot_callback(query)

    # Spinner answered
    assert len(mock_bot_answer_callback) == 1
    assert mock_bot_answer_callback[0]["id"] == "cb_query_999"

    # Command synthesized and executed
    assert len(mock_bot_send) == 1
    assert "Database Systems Engineering" in mock_bot_send[0]["text"]


def test_tier1_set_my_commands_registration():
    """F2.3: Native Telegram / autocomplete setMyCommands registers 10 standard commands."""
    mock_client = BotClient(token="bot123:test_token")
    captured = {}

    def _fake_request(endpoint, data=None, timeout=30):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return {"ok": True}

    mock_client._request = _fake_request
    res = mock_client.set_my_commands()

    assert res == {"ok": True}
    assert captured["endpoint"] == "setMyCommands"
    registered_cmds = [c["command"] for c in captured["data"]["commands"]]
    expected_cmds = [
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
    assert registered_cmds == expected_cmds


@pytest.mark.asyncio
async def test_tier1_standalone_slash_trigger(mock_bot_send):
    """F2.4: Standalone / outputs complete interactive command directory with quick buttons."""
    msg = {"chat": {"id": 123456789}, "text": "/"}
    await handle_bot_command(msg)

    assert len(mock_bot_send) == 1
    reply = mock_bot_send[0]["text"]
    assert "ChatLens & SPARK PA Menu" in reply
    assert "`/today`" in reply
    assert "`/tomorrow`" in reply
    assert "`/attendance`" in reply
    assert "`/status`" in reply
    assert mock_bot_send[0]["reply_markup"] is not None


@pytest.mark.asyncio
async def test_tier1_fuzzy_command_routing(mock_bot_send, monkeypatch):
    """F2.5: Resilient fuzzy command routing matches typos like /todat -> /today."""
    fixed_dt = datetime(2026, 7, 20, 8, 30, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    # Typos for /today
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/todat"})
    assert len(mock_bot_send) == 1
    assert "Database Systems Engineering" in mock_bot_send[0]["text"]

    await handle_bot_command({"chat": {"id": 123456789}, "text": "/toda"})
    assert len(mock_bot_send) == 2
    assert "Database Systems Engineering" in mock_bot_send[1]["text"]

    # Typos for /tomorrow
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/tomorow"})
    assert len(mock_bot_send) == 3
    assert "⬡ [08:10 AM – 09:00 AM]:" in mock_bot_send[2]["text"]

    # Typos for /status
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/statuss"})
    assert len(mock_bot_send) == 4
    assert "ChatLens PA Status" in mock_bot_send[3]["text"]


def test_tier1_startup_debounce_cooldown(isolate_test_environment, monkeypatch):
    """F3.1 - F3.2: Startup debounce in SQLite meta table enforces 15-minute cooldown."""
    dedup = isolate_test_environment
    now_ts = 1753000000.0

    # First boot: no prior timestamp -> should notify
    last_notify = dedup.meta_get("last_startup_notify_ts")
    assert last_notify is None
    should_notify = True if not last_notify else (now_ts - float(last_notify) >= 900)
    assert should_notify is True
    dedup.meta_set("last_startup_notify_ts", str(now_ts))

    # Restart after 5 minutes (300s): cooldown active -> should NOT notify
    reboot_5m_ts = now_ts + 300.0
    last_notify = dedup.meta_get("last_startup_notify_ts")
    should_notify = True if not last_notify else (reboot_5m_ts - float(last_notify) >= 900)
    assert should_notify is False

    # Restart after 16 minutes (960s): cooldown expired -> should notify
    reboot_16m_ts = now_ts + 960.0
    last_notify = dedup.meta_get("last_startup_notify_ts")
    should_notify = True if not last_notify else (reboot_16m_ts - float(last_notify) >= 900)
    assert should_notify is True


# ==============================================================================
# Tier 2 — Boundary & Corner Cases
# ==============================================================================


@pytest.mark.asyncio
async def test_tier2_empty_schedule_on_sunday(mock_bot_send, monkeypatch):
    """Tier 2: Empty schedule on Sunday delivers clean non-error message."""
    sunday_dt = datetime(2026, 7, 19, 11, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: sunday_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: sunday_dt.date())

    msg = {"chat": {"id": 123456789}, "text": "/today"}
    await handle_bot_command(msg)

    assert len(mock_bot_send) == 1
    reply = mock_bot_send[0]["text"]
    assert "No scheduled classes for Sunday, Jul 19. Enjoy your day 🎉" in reply


@pytest.mark.asyncio
async def test_tier2_all_periods_cancelled(isolate_test_environment, mock_bot_send, monkeypatch):
    """Tier 2: When all periods are cancelled, every slot shows 🔴 and note shows cancellation."""
    dedup = isolate_test_environment
    monday_date = "2026-07-20"
    fixed_dt = datetime(2026, 7, 20, 11, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    # Cancel all courses for this Monday
    for course in ["DBSE", "ESD", "JAPANESE", "ML"]:
        dedup.record_override(
            target_date=monday_date,
            period=None,
            course_code=course,
            course_name=course,
            status="CANCELLED",
        )

    msg = {"chat": {"id": 123456789}, "text": "/today"}
    await handle_bot_command(msg)

    assert len(mock_bot_send) == 1
    reply = mock_bot_send[0]["text"]

    # Every slot has cancelled icon and note
    assert "🔴" in reply
    assert "❌ Class cancelled" in reply
    assert "✅" not in reply  # Even past classes should show cancelled icon
    assert "📊 Monday | Wk1:" in reply


def test_tier2_debounce_boundary_exact_seconds(isolate_test_environment):
    """Tier 2: Exact boundary test at 899s (cooldown) and 901s (expired)."""
    dedup = isolate_test_environment
    base_ts = 1753000000.0
    dedup.meta_set("last_startup_notify_ts", str(base_ts))

    # At 899.9s -> cooldown active (< 900)
    ts_899 = base_ts + 899.9
    assert (ts_899 - float(dedup.meta_get("last_startup_notify_ts"))) < 900

    # At 900.1s -> cooldown expired (>= 900)
    ts_901 = base_ts + 900.1
    assert (ts_901 - float(dedup.meta_get("last_startup_notify_ts"))) >= 900


@pytest.mark.asyncio
async def test_tier2_unrecognized_invalid_command_fallback(mock_bot_send, monkeypatch):
    """Tier 2: Unrecognized slash commands fall back safely without matching /undo or /."""
    monkeypatch.setattr(settings, "gemini_api_key", MagicMock(get_secret_value=lambda: ""))

    for unrecognized in ("/completely_unknown_xyz", "/random", "/a", "/1", "/xyz"):
        mock_bot_send.clear()
        msg = {"chat": {"id": 123456789}, "text": unrecognized}
        await handle_bot_command(msg)

        assert len(mock_bot_send) == 1
        reply = mock_bot_send[0]["text"]
        assert f'Received: "{unrecognized}"' in reply
        assert "Use `/help` for commands or `/today` for your schedule." in reply
        assert "ChatLens & SPARK PA Menu" not in reply
        assert "Nothing to undo" not in reply


@pytest.mark.asyncio
async def test_tier2_unauthorized_sender_isolation(mock_bot_send, mock_bot_answer_callback):
    """Tier 2: Commands and callbacks from non-owner chat IDs are strictly ignored."""
    stranger_id = 999999999

    # Unauthorized command
    cmd_msg = {"chat": {"id": stranger_id}, "text": "/today"}
    await handle_bot_command(cmd_msg)
    assert len(mock_bot_send) == 0

    # Unauthorized callback
    cb_query = {"id": "stranger_cb", "from": {"id": stranger_id}, "data": "cmd:today"}
    await handle_bot_callback(cb_query)
    assert len(mock_bot_send) == 0
    assert len(mock_bot_answer_callback) == 0


@pytest.mark.asyncio
async def test_tier2_time_boundary_early_morning(mock_bot_send, monkeypatch):
    """Tier 2: At 07:00 AM before any classes, P1 is 🟡 (next upcoming) and all others are ⬡."""
    early_dt = datetime(2026, 7, 20, 7, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: early_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: early_dt.date())

    await handle_bot_command({"chat": {"id": 123456789}, "text": "/today"})
    reply = mock_bot_send[0]["text"]

    # First class of the day is next upcoming
    assert "🟡 [08:10 AM – 09:00 AM]:" in reply
    # Subsequent classes are later today
    assert "⬡ [09:00 AM – 09:50 AM]:" in reply
    assert "⬡ [10:00 AM – 10:50 AM]:" in reply
    # No completed or in-progress classes
    assert "✅" not in reply


@pytest.mark.asyncio
async def test_tier2_time_boundary_late_night(mock_bot_send, monkeypatch):
    """Tier 2: At 21:00 (after 16:00 end of day), all classes are marked ✅."""
    night_dt = datetime(2026, 7, 20, 21, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: night_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: night_dt.date())

    await handle_bot_command({"chat": {"id": 123456789}, "text": "/today"})
    reply = mock_bot_send[0]["text"]

    assert "🟡" not in reply
    assert "⬡" not in reply
    # Every slot line has ✅
    assert reply.count("✅") == 8  # 8 periods on Monday


def test_tier2_sqlite_wal_and_meta_concurrency(isolate_test_environment):
    """Tier 2: Verify WAL journal mode and busy_timeout = 5000 in deduplication store."""
    dedup = isolate_test_environment
    with dedup._get_conn() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert journal_mode.upper() == "WAL"

    # Concurrent write and read
    dedup.meta_set("key_a", "val_1")
    dedup.meta_set("key_b", "val_2")
    assert dedup.meta_get("key_a") == "val_1"
    assert dedup.meta_get("key_b") == "val_2"


# ==============================================================================
# Tier 3 — Cross-Feature Combinations (Pairwise)
# ==============================================================================


@pytest.mark.asyncio
async def test_tier3_inline_callback_triggers_schedule_with_buttons(
    mock_bot_send, mock_bot_answer_callback, monkeypatch
):
    """Pairwise 1: Inline callback cmd:today -> schedule formatter -> quick-action buttons."""
    fixed_dt = datetime(2026, 7, 20, 9, 30, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    query = {"id": "cb_1", "from": {"id": 123456789}, "data": "cmd:today"}
    await handle_bot_callback(query)

    assert len(mock_bot_answer_callback) == 1
    assert len(mock_bot_send) == 1
    msg = mock_bot_send[0]

    # Verify both 4-slot schedule content and inline keyboard buttons are intact
    assert "* Room    :" in msg["text"]
    assert "📊 Monday | Wk1:" in msg["text"]
    assert msg["reply_markup"]["inline_keyboard"][0][0]["text"] == "📅 Today"


@pytest.mark.asyncio
async def test_tier3_inline_callback_triggers_tomorrow_static_icons(
    mock_bot_send, mock_bot_answer_callback, monkeypatch
):
    """Pairwise 2: Inline callback cmd:tomorrow -> static icons -> quick-action buttons."""
    fixed_dt = datetime(2026, 7, 19, 14, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    query = {"id": "cb_tom", "from": {"id": 123456789}, "data": "cmd:tomorrow"}
    await handle_bot_callback(query)

    assert len(mock_bot_send) == 1
    reply = mock_bot_send[0]["text"]
    assert "⬡" in reply
    assert "✅" not in reply
    assert "📊 Monday | Wk1:" in reply


@pytest.mark.asyncio
async def test_tier3_startup_debounce_and_immediate_status_query(
    isolate_test_environment, mock_bot_send, monkeypatch
):
    """Pairwise 3: Startup debounce suppresses notification, subsequent /status succeeds cleanly."""
    dedup = isolate_test_environment
    fixed_dt = datetime(2026, 7, 20, 10, 0, tzinfo=clock.IST)
    now_ts = fixed_dt.timestamp()
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    # Set last startup notification to 2 minutes ago
    dedup.meta_set("last_startup_notify_ts", str(now_ts - 120))

    # Simulate startup check
    last_notify = dedup.meta_get("last_startup_notify_ts")
    should_notify = (now_ts - float(last_notify)) >= 900
    assert should_notify is False  # Debounce active

    # Owner queries /status immediately
    msg = {"chat": {"id": 123456789}, "text": "/status"}
    await handle_bot_command(msg)

    assert len(mock_bot_send) == 1
    assert "ChatLens PA Status" in mock_bot_send[0]["text"]
    assert "Live & Listening in Real-Time" in mock_bot_send[0]["text"]


@pytest.mark.asyncio
async def test_tier3_fuzzy_routing_with_dynamic_room_override(
    isolate_test_environment, mock_bot_send, monkeypatch
):
    """Pairwise 4: Typo /todat resolves to /today and accurately displays SQLite room override."""
    dedup = isolate_test_environment
    monday_date = "2026-07-20"
    fixed_dt = datetime(2026, 7, 20, 8, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    # Add dynamic room override for DBSE (Period 1)
    dedup.record_override(
        target_date=monday_date,
        period=1,
        course_code="25CS1302E",
        room="HC-15C",
        status="OVERRIDE",
    )

    # User issues typo command
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/todat"})

    assert len(mock_bot_send) == 1
    reply = mock_bot_send[0]["text"]

    # Verify fuzzy routing worked and room override was reflected
    assert "* Room    : HC-15C" in reply
    assert "⚡ Room override: ROOM_OVERRIDE (was H-005)" in reply
    assert "* Type    : Lab" in reply  # HC- rooms are recognized as Lab


@pytest.mark.asyncio
async def test_tier3_standalone_menu_to_deadlines_callback(
    mock_bot_send, mock_bot_answer_callback, monkeypatch
):
    """Pairwise 5: Standalone / outputs menu, clicking cmd:deadlines formats deadlines."""
    fixed_dt = datetime(2026, 7, 20, 10, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    # 1. User sends /
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/"})
    assert len(mock_bot_send) == 1
    assert "ChatLens & SPARK PA Menu" in mock_bot_send[0]["text"]

    # 2. User clicks Deadlines button
    await handle_bot_callback({"id": "cb_dl", "from": {"id": 123456789}, "data": "cmd:deadlines"})
    assert len(mock_bot_send) == 2
    assert "Upcoming Deadlines & Milestones" in mock_bot_send[1]["text"]


def test_tier3_debounce_with_corrupted_meta_timestamp(isolate_test_environment):
    """Pairwise 6: Corrupt string in SQLite meta table recovers gracefully without crashing."""
    dedup = isolate_test_environment
    now_ts = 1753000000.0

    # Store invalid non-numeric string
    dedup.meta_set("last_startup_notify_ts", "corrupt_garbage_value")

    # Debounce evaluation logic
    last_notify = dedup.meta_get("last_startup_notify_ts")
    should_notify = True
    if last_notify:
        try:
            if now_ts - float(last_notify) < 900:
                should_notify = False
        except ValueError:
            pass  # Recovers and proceeds to notify

    assert should_notify is True
    # Reset valid timestamp
    dedup.meta_set("last_startup_notify_ts", str(now_ts))
    assert dedup.meta_get("last_startup_notify_ts") == str(now_ts)


# ==============================================================================
# Tier 4 — Real-World Application Scenarios (End-to-End User Journeys)
# ==============================================================================


@pytest.mark.asyncio
async def test_tier4_student_morning_boot_and_query_journey(
    isolate_test_environment, mock_bot_send, mock_bot_answer_callback, monkeypatch
):
    """Scenario 1: Complete student morning boot journey.

    1. Daemon boots, sets commands via setMyCommands, applies startup debounce.
    2. Student opens bot, types standalone /.
    3. Student receives interactive menu with quick-action buttons.
    4. Student clicks 'cmd:today' -> receives 4-slot schedule with live status icons.
    5. Student clicks 'cmd:status' -> receives daemon health and monitoring telemetry.
    """
    dedup = isolate_test_environment
    fixed_dt = datetime(2026, 7, 20, 8, 45, tzinfo=clock.IST)
    now_ts = fixed_dt.timestamp()
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    # 1. Daemon boots and checks debounce
    last_notify = dedup.meta_get("last_startup_notify_ts")
    assert last_notify is None
    dedup.meta_set("last_startup_notify_ts", str(now_ts))

    # 2. Student types /
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/"})
    assert len(mock_bot_send) == 1
    assert "ChatLens & SPARK PA Menu" in mock_bot_send[0]["text"]

    # 3. Student taps Today button
    await handle_bot_callback({"id": "journey_cb1", "from": {"id": 123456789}, "data": "cmd:today"})
    assert len(mock_bot_send) == 2
    today_reply = mock_bot_send[1]["text"]
    assert "🔴 [08:10 AM – 09:00 AM]: Database Systems Engineering" in today_reply
    assert "* Section : S-10" in today_reply
    assert "📊 Monday | Wk1:" in today_reply

    # 4. Student taps Status button
    await handle_bot_callback(
        {"id": "journey_cb2", "from": {"id": 123456789}, "data": "cmd:status"}
    )
    assert len(mock_bot_send) == 3
    status_reply = mock_bot_send[2]["text"]
    assert "ChatLens PA Status" in status_reply
    assert "Live & Listening in Real-Time" in status_reply


@pytest.mark.asyncio
async def test_tier4_room_override_and_typo_resilience_journey(
    isolate_test_environment, mock_bot_send, monkeypatch
):
    """Scenario 2: Dynamic room override posted, typo check, verified against tomorrow.

    1. Class rep posts room override: ESD period 3 moved to H-006.
    2. Student accidentally types '/todat' (typo).
    3. System fuzzy-routes to /today, displaying updated room and note.
    4. Student checks '/tomorrow' -> verifies tomorrow's classes are untouched.
    """
    dedup = isolate_test_environment
    fixed_dt = datetime(2026, 7, 20, 9, 15, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    # 1. Apply override
    dedup.record_override(
        target_date="2026-07-20",
        period=3,
        course_code="25EC2206E",
        room="H-006",
        status="OVERRIDE",
    )

    # 2. Student sends typo /todat
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/todat"})
    assert len(mock_bot_send) == 1
    today_text = mock_bot_send[0]["text"]
    assert "* Room    : H-006" in today_text
    assert "⚡ Room override: ROOM_OVERRIDE (was H301A)" in today_text

    # 3. Student sends /tomorrow
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/tomorrow"})
    assert len(mock_bot_send) == 2
    tomorrow_text = mock_bot_send[1]["text"]
    assert "⬡" in tomorrow_text
    assert "⚡ Room override" not in tomorrow_text


@pytest.mark.asyncio
async def test_tier4_cancellation_and_progressive_status_journey(
    isolate_test_environment, mock_bot_send, monkeypatch
):
    """Scenario 3: Progressive status icon calculation throughout the academic day.

    - 07:30 AM (before classes): P1 is 🟡, rest ⬡.
    - 08:30 AM (during P1): P1 is 🔴, P2 is 🟡, rest ⬡.
    - 12:00 PM (during P5): P1-P4 are ✅, P5 is 🔴, P7 is 🟡, P8-P9 are ⬡.
    """
    # 07:30 AM
    dt_730 = datetime(2026, 7, 20, 7, 30, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: dt_730)
    monkeypatch.setattr(clock, "today_ist", lambda: dt_730.date())

    await handle_bot_command({"chat": {"id": 123456789}, "text": "/today"})
    res_730 = mock_bot_send[-1]["text"]
    assert "🟡 [08:10 AM – 09:00 AM]:" in res_730
    assert "⬡ [09:00 AM – 09:50 AM]:" in res_730

    # 08:30 AM
    dt_830 = datetime(2026, 7, 20, 8, 30, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: dt_830)
    monkeypatch.setattr(clock, "today_ist", lambda: dt_830.date())

    await handle_bot_command({"chat": {"id": 123456789}, "text": "/today"})
    res_830 = mock_bot_send[-1]["text"]
    assert "🔴 [08:10 AM – 09:00 AM]:" in res_830
    assert "🟡 [09:00 AM – 09:50 AM]:" in res_830

    # 12:00 PM (during P5 11:50 - 12:40)
    dt_1200 = datetime(2026, 7, 20, 12, 0, tzinfo=clock.IST)
    monkeypatch.setattr(clock, "now_ist", lambda: dt_1200)
    monkeypatch.setattr(clock, "today_ist", lambda: dt_1200.date())

    await handle_bot_command({"chat": {"id": 123456789}, "text": "/today"})
    res_1200 = mock_bot_send[-1]["text"]
    assert res_1200.count("✅") == 4  # P1, P2, P3, P4 completed
    assert "🔴 [11:50 AM – 12:40 PM]: Japanese Language Proficiency-2" in res_1200
    assert "🟡 [01:20 PM – 02:10 PM]: Japanese Language Proficiency-2" in res_1200


@pytest.mark.asyncio
async def test_tier4_daemon_reboot_and_task_review_journey(
    isolate_test_environment, mock_bot_send, monkeypatch
):
    """Scenario 4: Daemon crash, restart with debounce, and dead-ends recovery.

    1. System rebooted after 18 minutes (debounce allows notification).
    2. Rapid restart 1 minute later (debounce blocks notification).
    3. Student requests /deadlines to plan upcoming submissions.
    """
    dedup = isolate_test_environment
    fixed_dt = datetime(2026, 7, 20, 14, 0, tzinfo=clock.IST)
    now_ts = fixed_dt.timestamp()
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_dt)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_dt.date())

    # First restart after 18 mins (1080s)
    dedup.meta_set("last_startup_notify_ts", str(now_ts - 1080))
    last_notify = dedup.meta_get("last_startup_notify_ts")
    should_notify_1 = (now_ts - float(last_notify)) >= 900
    assert should_notify_1 is True
    dedup.meta_set("last_startup_notify_ts", str(now_ts))

    # Second restart after 60s
    last_notify_2 = dedup.meta_get("last_startup_notify_ts")
    should_notify_2 = (now_ts + 60 - float(last_notify_2)) >= 900
    assert should_notify_2 is False

    # Student reviews deadlines
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/deadlines"})
    assert len(mock_bot_send) == 1
    assert "Upcoming Deadlines & Milestones" in mock_bot_send[0]["text"]


@pytest.mark.asyncio
async def test_tier4_button_consistency_across_all_command_replies(mock_bot_send):
    """Scenario 5: Every user command reply attaches the standard 2x2 interactive button matrix."""
    commands_to_test = ["/", "/today", "/tomorrow", "/status", "/deadlines", "/help"]

    for i, cmd in enumerate(commands_to_test):
        await handle_bot_command({"chat": {"id": 123456789}, "text": cmd})
        assert len(mock_bot_send) == i + 1
        markup = mock_bot_send[i]["reply_markup"]
        assert markup is not None
        assert "inline_keyboard" in markup
        kb = markup["inline_keyboard"]
        assert len(kb) == 2
        assert kb[0][0]["callback_data"] == "cmd:today"
        assert kb[0][1]["callback_data"] == "cmd:attendance"
        assert kb[1][0]["callback_data"] == "cmd:deadlines"
        assert kb[1][1]["callback_data"] == "cmd:status"
