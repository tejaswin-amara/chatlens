from datetime import date, datetime

import pytest

from src.briefing import build_briefing, classes_can_skip, classes_needed


def test_build_briefing_empty():
    now = datetime(2026, 10, 5, 8, 0)
    res = build_briefing(now, [], [], [], {})
    assert "No classes today" in res
    assert "Upcoming Tasks" not in res
    assert "Attendance Alerts" not in res
    assert "Academic Milestones" not in res


def test_build_briefing_attendance():
    now = datetime(2026, 10, 5, 8, 0)
    attendance = [
        {"course": "DSA", "attended": "18", "held": "20"},  # 90%, skip 1
        {"course": "ML", "attended": "16", "held": "20"},  # 80%, need 7
        {"course": "OSSP", "attended": "14", "held": "20"},  # 70%, need 10
    ]
    res = build_briefing(now, [], [], attendance, {})
    assert "DSA" not in res
    assert "🟡 <85% ML: 16/20 (Need 7 more)" in res
    assert "🔴 <75% OSSP: 14/20 (Need 20 more)" in res


def test_build_briefing_tasks_events_milestones():
    now = datetime(2026, 10, 5, 8, 0)
    tasks = [
        {"title": "Task 1", "due": "2026-10-06T00:00:00Z"},
        {"title": "Task 2", "due": "2026-10-10T00:00:00Z"},
    ]
    events = [
        {
            "summary": "DSA",
            "location": "H-005",
            "start": {"dateTime": "2026-10-05T08:10:00Z"},
            "extendedProperties": {"private": {"spark_override": "1"}},
        },
        {"summary": "ML", "location": "H-106"},
    ]
    milestones = {"T04 Midterm": date(2026, 10, 8)}

    res = build_briefing(now, events, tasks, [], milestones)
    assert "[URGENT]" in res
    assert "Task 1 [URGENT]" in res
    assert "Task 2 [URGENT]" not in res
    assert "Task 2" in res
    assert "DSA [H-005] 🔁" in res
    assert "All day: ML" in res
    assert "T04 Midterm" in res


def test_classes_can_skip_exhaustive():
    assert classes_can_skip(10, 10, 85) == 1
    assert classes_can_skip(85, 100, 85) == 0


def test_classes_needed_exhaustive():
    # Exhaustive test for h=1..199
    for h in range(1, 200):
        # 70% attendance
        a = int(h * 0.7)
        needed = classes_needed(a, h, 85)
        # Verify the new ratio
        new_a = a + needed
        new_h = h + needed
        assert new_a / new_h >= 0.85
        if needed > 0:
            assert (new_a - 1) / (new_h - 1) < 0.85


async def guard(coro, seconds: float = 5.0):
    import asyncio

    return await asyncio.wait_for(coro, timeout=seconds)


@pytest.mark.asyncio
async def test_fetch_briefing_inputs_empty_attendance():
    from unittest.mock import MagicMock, patch

    from src.briefing import fetch_briefing_inputs

    with (
        patch("src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service") as mock_cal,
        patch("src.workspace.tasks_sync.tasks_sync.list_open_tasks", return_value=[]) as mock_tasks,
        patch(
            "src.workspace.sheets_logger.sheets_logger.get_attendance", return_value=[]
        ) as mock_att,
        patch("src.academic_calendar.load_calendar", return_value=None),
    ):
        mock_events = MagicMock()
        mock_events.list.return_value.execute.return_value = {"items": []}
        mock_cal.return_value.events.return_value = mock_events

        events, tasks, att, milestones = await guard(fetch_briefing_inputs())
        assert events == []
        assert tasks == []
        assert att == []
        assert milestones == {}
        mock_tasks.assert_called_once()
        mock_att.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_briefing_inputs_calendar_timezone():
    from unittest.mock import MagicMock, patch

    from src.briefing import fetch_briefing_inputs

    with (
        patch("src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service") as mock_cal,
        patch("src.workspace.tasks_sync.tasks_sync.list_open_tasks", return_value=[]),
        patch("src.workspace.sheets_logger.sheets_logger.get_attendance", return_value=[]),
        patch("src.academic_calendar.load_calendar", return_value=None),
    ):
        mock_events = MagicMock()
        mock_events.list.return_value.execute.return_value = {"items": [{"summary": "Test Class"}]}
        mock_cal.return_value.events.return_value = mock_events

        events, _, _, _ = await guard(fetch_briefing_inputs())
        assert len(events) == 1
        call_kwargs = mock_events.list.call_args[1]
        assert call_kwargs.get("timeZone") == "Asia/Kolkata"


@pytest.mark.asyncio
async def test_fetch_briefing_inputs_uses_list_open_tasks():
    from unittest.mock import MagicMock, patch

    from src.briefing import fetch_briefing_inputs

    with (
        patch("src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service") as mock_cal,
        patch("src.workspace.tasks_sync.tasks_sync.list_open_tasks") as mock_tasks,
        patch("src.workspace.sheets_logger.sheets_logger.get_attendance", return_value=[]),
        patch("src.academic_calendar.load_calendar", return_value=None),
    ):
        mock_events = MagicMock()
        mock_events.list.return_value.execute.return_value = {"items": []}
        mock_cal.return_value.events.return_value = mock_events
        mock_tasks.return_value = [{"title": "Submit assignment", "id": "t1"}]

        _, tasks, _, _ = await guard(fetch_briefing_inputs())
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Submit assignment"
        mock_tasks.assert_called_once()


def test_format_bunk_calculator():
    from src.briefing import format_bunk_calculator

    # 1. Empty rows
    assert "No attendance records" in format_bunk_calculator([])

    # 2. Populated rows
    rows = [
        {"course": "DSA", "code": "25CS2103E", "attended": "18", "held": "20"},  # 90%
        {"course": "ML", "code": "25SC2107E", "attended": "14", "held": "20"},  # 70%
    ]
    res = format_bunk_calculator(rows)
    assert "DSA (25CS2103E)" in res
    assert "90.0%" in res
    assert "Safe bunks (≥75%): **4**" in res
    assert "ML (25SC2107E)" in res
    assert "70.0%" in res
    assert "Attend next: **4** classes" in res
