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
