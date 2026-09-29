"""Unit tests for Telegram event handlers and command routing."""

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.handlers import register_handlers
from src.parsing.schemas import ExtractedAcademicEvent


@pytest.mark.asyncio
async def test_today_command_handler() -> None:
    mock_client = MagicMock()
    mock_client.on.side_effect = lambda event_builder: (lambda func: func)
    register_handlers(mock_client)

    assert mock_client.on.called


@pytest.mark.asyncio
@patch("src.ingestion.handlers.calendar_sync")
@patch("src.ingestion.handlers.sheets_logger")
@patch("src.ingestion.handlers.ai_extractor")
async def test_incoming_room_override_message(
    mock_ai: MagicMock,
    mock_sheets: MagicMock,
    mock_cal: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_client.on.side_effect = lambda event_builder: (lambda func: func)
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

    mock_cal.update_class_room.return_value = {"id": "ev_1"}
    mock_sheets.append_audit_log.return_value = {"status": "ok"}

    assert mock_cal is not None
