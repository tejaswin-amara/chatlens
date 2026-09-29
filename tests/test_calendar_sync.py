"""Unit tests for Google Calendar sync adapter."""

from unittest.mock import MagicMock

from src.workspace.calendar_sync import CalendarSync


def test_update_class_room_patch_existing() -> None:
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_calendar_service.return_value = mock_service

    mock_service.events().list().execute.return_value = {
        "items": [
            {
                "id": "event_123",
                "summary": "DSA Lecture",
                "location": "Room H-001",
            }
        ]
    }

    mock_service.events().patch().execute.return_value = {
        "id": "event_123",
        "location": "Room H-005",
    }

    adapter = CalendarSync(calendar_id="primary", auth_adapter=mock_auth)
    res = adapter.update_class_room(
        course_name="DSA",
        course_code="25CS2101",
        new_room="H-005",
        target_date="2026-03-30",
    )

    assert res["id"] == "event_123"
    assert res["location"] == "Room H-005"
    assert mock_service.events().patch.called


def test_create_holiday_event_suppress_reminders() -> None:
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_calendar_service.return_value = mock_service

    mock_service.events().insert().execute.return_value = {
        "id": "holiday_456",
        "summary": "University Holiday: Founder's Day",
    }

    adapter = CalendarSync(calendar_id="primary", auth_adapter=mock_auth)
    res = adapter.create_holiday_event(reason="Founder's Day", target_date="2026-04-01")

    assert res["id"] == "holiday_456"
    call_args = mock_service.events().insert.call_args
    body = call_args[1]["body"]
    assert body["reminders"]["useDefault"] is False
    assert body["reminders"]["overrides"] == []
