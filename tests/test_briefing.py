from datetime import date, datetime

from src.briefing import build_briefing


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
        {"course": "DSA", "attended": "18", "held": "20"}, # 90%, skip 1
        {"course": "ML", "attended": "16", "held": "20"},  # 80%, need 7
        {"course": "OSSP", "attended": "14", "held": "20"} # 70%, need 10
    ]
    res = build_briefing(now, [], [], attendance, {})
    assert "DSA" not in res
    assert "🟡 <85% ML: 16/20 (Need 7 more)" in res
    assert "🔴 <75% OSSP: 14/20 (Need 20 more)" in res

def test_build_briefing_tasks_events_milestones():
    now = datetime(2026, 10, 5, 8, 0)
    tasks = [
        {"title": "Task 1", "due": "2026-10-06T00:00:00Z"},
        {"title": "Task 2", "due": "2026-10-10T00:00:00Z"}
    ]
    events = [
        {"summary": "DSA", "location": "H-005", "start": {"dateTime": "2026-10-05T08:10:00Z"},
         "extendedProperties": {"private": {"spark_override": "1"}}},
        {"summary": "ML", "location": "H-106"}
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
