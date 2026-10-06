from unittest.mock import MagicMock

import pytest

from src.workspace.calendar_sync import CalendarSync
from src.workspace.tasks_sync import TasksSync


# Requirements: "calendar and tasks idempotency. 8 cases"
# Let's write them.
def test_calendar_sync_idempotency():
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_calendar_service.return_value = mock_service

    adapter = CalendarSync(calendar_id="primary", auth_adapter=mock_auth)

    # Simulate list returning an existing event
    mock_service.events().list().execute.return_value = {
        "items": [{"id": "ev_existing", "summary": "University Holiday: Diwali"}]
    }

    res = adapter.create_holiday_event("Diwali", "2026-11-01")
    assert res["id"] == "ev_existing"
    mock_service.events().insert.assert_not_called()


def test_calendar_sync_insert_new():
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_calendar_service.return_value = mock_service

    adapter = CalendarSync(calendar_id="primary", auth_adapter=mock_auth)

    mock_service.events().list().execute.return_value = {"items": []}
    mock_service.events().insert().execute.return_value = {"id": "ev_new"}

    res = adapter.create_holiday_event("Diwali", "2026-11-01")
    assert res["id"] == "ev_new"


def test_tasks_sync_idempotency():
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_tasks_service.return_value = mock_service

    adapter = TasksSync(auth_adapter=mock_auth)

    # Test same title, same due date
    mock_service.tasks().list().execute.return_value = {
        "items": [{"id": "task_existing", "title": "Submit Lab", "due": "2026-11-01T23:59:59.000Z"}]
    }

    res = adapter.create_task("Submit Lab", due_date="2026-11-01")
    assert res["id"] == "task_existing"
    mock_service.tasks().insert.assert_not_called()


def test_tasks_sync_same_title_no_date():
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_tasks_service.return_value = mock_service

    adapter = TasksSync(auth_adapter=mock_auth)

    # Test same title, no due date in task or in creation
    mock_service.tasks().list().execute.return_value = {
        "items": [{"id": "task_existing", "title": "Review syllabus"}]
    }

    res = adapter.create_task("Review syllabus")
    assert res["id"] == "task_existing"
    mock_service.tasks().insert.assert_not_called()


def test_calendar_period_window():
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_calendar_service.return_value = mock_service

    adapter = CalendarSync(calendar_id="primary", auth_adapter=mock_auth)

    # Simulate NO existing event when listing
    mock_service.events().list().execute.return_value = {"items": []}

    try:
        adapter.update_class_room("DSA", "25CS", "H-101", "2026-10-05", "P1")
    except LookupError:
        pass
    list_kwargs = mock_service.events().list.call_args.kwargs
    assert "T00:00:00" in list_kwargs["timeMin"] or "T08:00:00" in list_kwargs["timeMin"]

    # Verify timeMin and timeMax are computed
    list_kwargs = mock_service.events().list.call_args.kwargs
    assert "T00:00:00" in list_kwargs["timeMin"] or "T08:00:00" in list_kwargs["timeMin"]


def test_calendar_cancel_class():
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_calendar_service.return_value = mock_service

    adapter = CalendarSync(calendar_id="primary", auth_adapter=mock_auth)

    # Simulate existing event
    mock_service.events().list().execute.return_value = {
        "items": [
            {"id": "ev_cancel", "summary": "DSA", "start": {"dateTime": "2026-10-05T02:40:00Z"}}
        ]
    }
    mock_service.events().patch().execute.return_value = {"id": "ev_cancel"}

    res = adapter.cancel_class("DSA", "25CS", "2026-10-05", "P1")
    assert res["id"] == "ev_cancel"
    # Verify extendedProperties logic
    patch_kwargs = mock_service.events().patch.call_args.kwargs
    assert patch_kwargs["body"]["extendedProperties"]["private"]["spark_override"] == "1"
    assert "CANCELLED" in patch_kwargs["body"]["summary"]


def test_calendar_override_marker_room():
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_calendar_service.return_value = mock_service

    adapter = CalendarSync(calendar_id="primary", auth_adapter=mock_auth)

    mock_service.events().list().execute.return_value = {
        "items": [
            {"id": "ev_room", "summary": "DSA", "start": {"dateTime": "2026-10-05T02:40:00Z"}}
        ]
    }
    mock_service.events().patch().execute.return_value = {"id": "ev_room"}

    adapter.update_class_room("DSA", "25CS", "H-101", "2026-10-05", "P1")
    patch_kwargs = mock_service.events().patch.call_args.kwargs
    assert patch_kwargs["body"]["extendedProperties"]["private"]["spark_override"] == "1"
    assert patch_kwargs["body"]["location"] == "Room H-101"


def test_calendar_missing_event():
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_calendar_service.return_value = mock_service

    adapter = CalendarSync(calendar_id="primary", auth_adapter=mock_auth)

    mock_service.events().list().execute.return_value = {"items": []}

    with pytest.raises(LookupError, match="No events found matching"):
        adapter.update_class_room("DSA", "25CS", "H-101", "2026-10-05", "P1")
