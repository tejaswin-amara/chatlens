"""Unit tests for Telegram event handlers and command routing."""

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.handlers import apply_event, register_handlers
from src.parsing.schemas import ExtractedAcademicEvent


@pytest.mark.asyncio
async def test_today_command_handler() -> None:
    mock_client = MagicMock()
    mock_client.on.side_effect = lambda event_builder: lambda func: func
    register_handlers(mock_client)

    assert mock_client.on.called


@pytest.mark.asyncio
@patch("src.ingestion.handlers.calendar_sync")
@patch("src.ingestion.handlers.ai_extractor")
async def test_incoming_room_override_message(
    mock_ai: MagicMock,
    mock_cal: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_client.on.side_effect = lambda event_builder: lambda func: func
    register_handlers(mock_client)

    mock_ai.extract_from_text.return_value = ExtractedAcademicEvent(
        intent="ROOM_OVERRIDE",
        course_name="DSA",
        course_code="25CS2101",
        room="H-005",
        target_date="2026-03-30",
        period="P2",
        summary="DSA shifted to H-005",
        action_required=False,
    )
    from src.config import settings

    settings.spark_mode = "live"
    settings.spark_media = True

    mock_cal.update_class_room.return_value = {"id": "ev_1"}

    assert mock_cal is not None


@pytest.mark.asyncio
async def test_apply_event_calendar_conflict():
    # CALENDAR_CONFLICT test in the handler decision path
    # Needs to mock academic_calendar.get_milestone_date
    with patch("src.academic_calendar.load_calendar") as mock_load:
        mock_cal = MagicMock()
        mock_load.return_value = mock_cal
        with patch("src.academic_calendar.get_milestone_date") as mock_get_milestone:
            import datetime

            mock_get_milestone.return_value = datetime.date(2026, 4, 15)
            with patch("src.notify.bot.bot.send") as mock_send:
                with patch("src.workspace.sheets_logger.sheets_logger.append_audit_log"):
                    event = ExtractedAcademicEvent(
                        intent="EXAM_DEADLINE",
                        summary="Mid-term exam on April 10",
                        target_date="2026-04-10",
                        action_required=True,
                    )

                    execution_status, details_list = await apply_event(event)

                    assert execution_status == "CALENDAR_CONFLICT"
                    assert "Conflict: Msg date 2026-04-10, Cal date 2026-04-15" in details_list[0]
                    mock_send.assert_called_once()
                    assert "Message date: 2026-04-10" in mock_send.call_args.args[0]


@pytest.mark.asyncio
async def test_handle_bot_command_today():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/today"}

    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = []
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "No scheduled classes for" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_strip_bot_username():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/today@ChatLensBot"}

    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = []
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "No scheduled classes for" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_today_with_slots():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command
    from src.timetable import Slot

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/today"}

    test_slots = [
        Slot(
            day="Fri",
            period=1,
            course="ML",
            room="H-005",
            faculty="Dr. Lakshmi",
            override=None,
        ),
        Slot(
            day="Fri",
            period=3,
            course="DSA",
            room="HC-15C",
            faculty="Dr. Chandusha",
            override=None,
        ),
    ]

    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = test_slots
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        output = mock_send.call_args[0][0]
        assert "Machine Learning (25SC2107E)" in output
        assert "* Room    : H-005" in output
        assert "* Section : S-10" in output
        assert "* Type    : Lecture" in output
        assert "Data Structures & Algorithms-3 (25CS2103E)" in output
        assert "* Type    : Lab" in output
        assert "📊" in output


@pytest.mark.asyncio
async def test_handle_bot_command_fuzzy_routing():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/todat"}

    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = []
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "No scheduled classes for" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_standalone_slash():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/"}

    with patch("src.notify.bot.bot.send") as mock_send:
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "ChatLens & SPARK PA Menu" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_status():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/status"}

    with patch("src.notify.bot.bot.send") as mock_send:
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "ChatLens PA Status" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_unauthorized_ignored():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 99999}, "text": "/today"}

    with patch("src.notify.bot.bot.send") as mock_send:
        await handle_bot_command(msg)
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_handle_bot_callback_cmd_today():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_callback

    settings.owner_chat_id = 12345
    query = {
        "id": "cb_today_1",
        "from": {"id": 12345},
        "data": "cmd:today",
    }

    with (
        patch("src.notify.bot.bot.answer_callback") as mock_answer,
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = []
        await handle_bot_callback(query)

        mock_answer.assert_called_once_with("cb_today_1")
        mock_send.assert_called_once()
        assert "No scheduled classes for" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_callback_cmd_attendance():
    from unittest.mock import AsyncMock

    from src.config import settings
    from src.ingestion.handlers import handle_bot_callback

    settings.owner_chat_id = 12345
    query = {
        "id": "cb_att_1",
        "from": {"id": 12345},
        "data": "cmd:attendance",
    }

    fake_records = [
        {
            "course_code": "25CS2103E",
            "course_name": "DSA-3",
            "attended": 28,
            "conducted": 30,
            "percentage": 93.33,
            "safe_bunks": 2,
            "recovery_needed": 0,
            "ltps": "Lecture",
        }
    ]

    with (
        patch("src.notify.bot.bot.answer_callback") as mock_answer,
        patch("src.erp.klu_erp.get_attendance", new_callable=AsyncMock, return_value=fake_records),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_callback(query)

        mock_answer.assert_called_once_with("cb_att_1")
        assert mock_send.call_count == 2
        report = mock_send.call_args_list[1][0][0]
        assert "Live Attendance Overview (KL ERP)" in report
        assert "DSA-3" in report
        assert "93.33%" in report


@pytest.mark.asyncio
async def test_handle_bot_callback_cmd_deadlines():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_callback

    settings.owner_chat_id = 12345
    query = {
        "id": "cb_deadlines_1",
        "from": {"id": 12345},
        "data": "cmd:deadlines",
    }

    with (
        patch("src.notify.bot.bot.answer_callback") as mock_answer,
        patch("src.academic_calendar.load_calendar", return_value=None),
        patch("src.utils.deduplication.deduplicator.list_pending", return_value=[]),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_callback(query)

        mock_answer.assert_called_once_with("cb_deadlines_1")
        mock_send.assert_called_once()
        assert "Upcoming Deadlines & Milestones" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_callback_cmd_status():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_callback

    settings.owner_chat_id = 12345
    query = {
        "id": "cb_status_1",
        "from": {"id": 12345},
        "data": "cmd:status",
    }

    with (
        patch("src.notify.bot.bot.answer_callback") as mock_answer,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_callback(query)

        mock_answer.assert_called_once_with("cb_status_1")
        mock_send.assert_called_once()
        assert "ChatLens PA Status" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_callback_unauthorized_ignored():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_callback

    settings.owner_chat_id = 12345
    query = {
        "id": "cb_unauth_1",
        "from": {"id": 99999},
        "data": "cmd:today",
    }

    with (
        patch("src.notify.bot.bot.answer_callback") as mock_answer,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_callback(query)

        mock_answer.assert_not_called()
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_handle_bot_command_fuzzy_routing_attandance():
    from unittest.mock import AsyncMock

    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/attandance"}

    with (
        patch("src.erp.klu_erp.get_attendance", new_callable=AsyncMock, return_value=[]),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_command(msg)
        assert mock_send.call_count == 2
        assert "Fetching live attendance" in mock_send.call_args_list[0][0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_fuzzy_routing_deadlin():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/deadlin"}

    with (
        patch("src.academic_calendar.load_calendar", return_value=None),
        patch("src.utils.deduplication.deduplicator.list_pending", return_value=[]),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "Upcoming Deadlines & Milestones" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_fuzzy_routing_tomorow():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/tomorow"}

    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = []
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "No scheduled classes for" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_fuzzy_routing_statuss():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/statuss"}

    with patch("src.notify.bot.bot.send") as mock_send:
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "ChatLens PA Status" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_unrecognized_slash_falls_through():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/completelyunknownxyz"}

    with (
        patch.object(settings.gemini_api_key, "get_secret_value", return_value=""),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        output = mock_send.call_args[0][0]
        assert 'Received: "/completelyunknownxyz"' in output
        assert "/help" in output


@pytest.mark.asyncio
async def test_handle_bot_command_fuzzy_routing_does_not_match_undo_or_slash():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    for test_cmd in ("/random", "/xyz", "/a", "/1", "/pizza"):
        msg = {"chat": {"id": 12345}, "text": test_cmd}
        with (
            patch.object(settings.gemini_api_key, "get_secret_value", return_value=""),
            patch("src.notify.bot.bot.send") as mock_send,
            patch("src.ingestion.handlers.handle_undo_command") as mock_undo,
        ):
            await handle_bot_command(msg)
            mock_undo.assert_not_called()
            mock_send.assert_called_once()
            output = mock_send.call_args[0][0]
            assert f'Received: "{test_cmd}"' in output
            assert "ChatLens & SPARK PA Menu" not in output
            assert "Nothing to undo" not in output


@pytest.mark.asyncio
async def test_handle_bot_command_fuzzy_routing_valid_typos():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345

    # /toda -> /today
    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = []
        await handle_bot_command({"chat": {"id": 12345}, "text": "/toda"})
        mock_send.assert_called_once()
        assert "No scheduled classes for" in mock_send.call_args[0][0]

    # /dedlines -> /deadlines
    with (
        patch("src.academic_calendar.load_calendar", return_value=None),
        patch("src.utils.deduplication.deduplicator.list_pending", return_value=[]),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_command({"chat": {"id": 12345}, "text": "/dedlines"})
        mock_send.assert_called_once()
        assert "Upcoming Deadlines & Milestones" in mock_send.call_args[0][0]



@pytest.mark.asyncio
async def test_handle_bot_command_standalone_slash_menu_content():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/"}

    with patch("src.notify.bot.bot.send") as mock_send:
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        menu = mock_send.call_args[0][0]
        assert "ChatLens & SPARK PA Menu" in menu
        assert "/today" in menu
        assert "/tomorrow" in menu
        assert "/attendance" in menu
        assert "/deadlines" in menu
        assert "/status" in menu
        assert "/marks" in menu
        assert "/cgpa" in menu
        assert "/fee" in menu
        assert "/rescan" in menu
        assert "/undo" in menu
        assert "/help" in menu


@pytest.mark.asyncio
async def test_handle_bot_command_tomorrow_empty():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/tomorrow"}

    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = []
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        assert "No scheduled classes for" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_bot_command_tomorrow_with_slots():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command
    from src.timetable import Slot

    settings.owner_chat_id = 12345
    msg = {"chat": {"id": 12345}, "text": "/tomorrow"}

    test_slots = [
        Slot(
            day="Sat",
            period=1,
            course="ML",
            room="H-005",
            faculty="Dr. Lakshmi",
            override=None,
        ),
        Slot(
            day="Sat",
            period=2,
            course="DSA",
            room="HC-15C",
            faculty="Dr. Chandusha",
            override=None,
        ),
        Slot(
            day="Sat",
            period=3,
            course="JAPANESE",
            room="H006",
            faculty="Sensei Tanaka",
            override=None,
        ),
        Slot(
            day="Sat",
            period=4,
            course="DBSE",
            room="H-005",
            faculty="Divya Priya Degala",
            override="CANCELLED",
        ),
    ]

    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots") as mock_slots,
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        mock_slots.return_value = test_slots
        await handle_bot_command(msg)
        mock_send.assert_called_once()
        output = mock_send.call_args[0][0]

        # F1.3 4-slot structure
        assert "Machine Learning (25SC2107E)" in output
        assert "* Room    : H-005" in output
        assert "* Faculty : Dr. Lakshmi" in output
        assert "* Section : S-10" in output
        assert "* Type    : Lecture" in output

        # Lab type detection
        assert "Data Structures & Algorithms-3 (25CS2103E)" in output
        assert "* Type    : Lab" in output

        # Skill type detection
        assert "Japanese Language Proficiency-2 (25FL2112E)" in output
        assert "* Type    : Skill" in output

        # [R4] Status icons for tomorrow: static ⬡ for uncancelled, 🔴 for cancelled
        assert "⬡ [08:10 AM – 09:00 AM]: Machine Learning" in output
        assert "⬡ [09:00 AM – 09:50 AM]: Data Structures & Algorithms-3" in output
        assert "⬡ [10:00 AM – 10:50 AM]: Japanese Language Proficiency-2" in output
        assert "🔴 [10:50 AM – 11:40 AM]: Database Systems Engineering" in output
        assert "* Note    : ❌ Class cancelled" in output

        # F1.5 [R9] Stats line
        assert "📊" in output
        assert "2 academic · 1 lab(s) · 1 non-ERP" in output
        assert "Regular instruction" in output


@pytest.mark.asyncio
async def test_handle_bot_command_tomorrow_fuzzy_routing():
    from src.config import settings
    from src.ingestion.handlers import handle_bot_command

    settings.owner_chat_id = 12345

    for typo in ("/tomorow", "/tommorow"):
        msg = {"chat": {"id": 12345}, "text": typo}
        with (
            patch("src.timetable.load") as mock_load,
            patch("src.timetable.get_effective_slots") as mock_slots,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_load.return_value = MagicMock()
            mock_slots.return_value = []
            await handle_bot_command(msg)
            mock_send.assert_called_once()
            assert "No scheduled classes for" in mock_send.call_args[0][0]


def test_format_day_schedule_live_status_progression_today():
    from datetime import date, datetime
    from zoneinfo import ZoneInfo

    from src.timetable import Meta, Slot, Timetable, format_day_schedule

    ist = ZoneInfo("Asia/Kolkata")
    # Simulate current time at 09:30 AM (during Period 2: 09:00 AM - 09:50 AM)
    now_dt = datetime(2026, 10, 23, 9, 30, tzinfo=ist)
    target_date = date(2026, 10, 23)

    tt = Timetable(
        meta=Meta(
            term="T04",
            valid_from=date(2026, 7, 15),
            valid_to=date(2026, 11, 1),
            sample=False,
        ),
        slots=[
            Slot(day="Fri", period=1, course="ML", room="H-005", faculty="Dr. A"),
            Slot(day="Fri", period=2, course="OSSP", room="H-005", faculty="Dr. B"),
            Slot(day="Fri", period=3, course="DSA", room="H-005", faculty="Dr. C"),
            Slot(day="Fri", period=4, course="ESD", room="H-005", faculty="Dr. D"),
            Slot(
                day="Fri",
                period=5,
                course="DBSE",
                room="H-005",
                faculty="Dr. E",
                override="CANCELLED",
            ),
        ],
    )

    output = format_day_schedule(target_date, now_dt=now_dt, timetable=tt)

    # Period 1 (08:10 - 09:00) ended -> ✅ completed
    assert "✅ [08:10 AM – 09:00 AM]: Machine Learning" in output
    # Period 2 (09:00 - 09:50) in progress -> 🔴 current
    assert "🔴 [09:00 AM – 09:50 AM]: Operating Systems & Systems Programming" in output
    # Period 3 (10:00 - 10:50) earliest upcoming -> 🟡 next upcoming
    assert "🟡 [10:00 AM – 10:50 AM]: Data Structures & Algorithms-3" in output
    # Period 4 (10:50 - 11:40) later today -> ⬡ scheduled
    assert "⬡ [10:50 AM – 11:40 AM]: Embedded System Design & IoT" in output
    # Period 5 cancelled -> 🔴 cancelled
    assert "🔴 [11:50 AM – 12:40 PM]: Database Systems Engineering" in output


def test_format_day_schedule_static_icons_when_now_dt_none():
    from datetime import date

    from src.timetable import Meta, Slot, Timetable, format_day_schedule

    target_date = date(2026, 10, 24)
    tt = Timetable(
        meta=Meta(
            term="T04",
            valid_from=date(2026, 7, 15),
            valid_to=date(2026, 11, 1),
            sample=False,
        ),
        slots=[
            Slot(day="Sat", period=1, course="ML", room="H-005", faculty="Dr. A"),
            Slot(day="Sat", period=2, course="OSSP", room="H-005", faculty="Dr. B"),
            Slot(
                day="Sat",
                period=3,
                course="DBSE",
                room="H-005",
                faculty="Dr. C",
                override="CANCELLED",
            ),
        ],
    )

    # now_dt=None for tomorrow
    output = format_day_schedule(target_date, now_dt=None, timetable=tt)

    # Uncancelled slots must be ⬡, not time-dependent ✅ or 🟡
    assert "⬡ [08:10 AM – 09:00 AM]: Machine Learning" in output
    assert "⬡ [09:00 AM – 09:50 AM]: Operating Systems & Systems Programming" in output
    # Cancelled slot must be 🔴
    assert "🔴 [10:00 AM – 10:50 AM]: Database Systems Engineering" in output
    assert "✅" not in output
    assert "🟡" not in output


def test_timetable_load_fallback_to_default():
    from src.timetable import load

    # 1. Nonexistent custom path falls back to default data/timetable_T04.toml
    tt = load("nonexistent_timetable_path_xyz.toml")
    assert tt is not None
    assert tt.path == "data/timetable_T04.toml"
    assert len(tt.slots) > 0
    assert tt.meta.term == "T04"

    # 2. Both paths failing returns None
    with patch("builtins.open", side_effect=FileNotFoundError):
        assert load("missing.toml") is None


def test_format_day_schedule_missing_timetable():
    from datetime import date

    from src.timetable import format_day_schedule

    with patch("src.timetable.load", return_value=None):
        res = format_day_schedule(date(2026, 10, 23))
        assert res == "⚠️ Timetable file not found."

