import datetime

import pytest

from src.parsing.schemas import ExtractedAcademicEvent as ParsedEvent
from src.timetable import Meta, Slot, Timetable, validate


@pytest.fixture
def timetable():
    return Timetable(
        meta=Meta(
            term="Even 2026",
            sample=False,
            valid_from=datetime.date(2026, 1, 1),
            valid_to=datetime.date(2026, 6, 30),
        ),
        slots=[
            Slot(day="Mon", period=3, course="DSA", room="H-001", faculty="Dr. A"),
            Slot(day="Mon", period=4, course="DSA", room="H-001", faculty="Dr. A"),
            Slot(day="Tue", period=6, course="DSA", room="H-001", faculty="Dr. A"),
            Slot(day="Wed", period=3, course="DSA", room="H-001", faculty="Dr. A"),
            Slot(
                day="Thu", period=3, course="DSA", room="H-002", faculty="Dr. A"
            ),  # different room
            Slot(day="Fri", period=3, course="DSA", room="H-001", faculty="Dr. B"),
            Slot(day="Fri", period=5, course="DSA", room="H-001", faculty="Dr. C"),
        ],
    )


@pytest.fixture
def sample_timetable():
    return Timetable(
        meta=Meta(
            term="Even 2026",
            sample=True,
            valid_from=datetime.date(2026, 1, 1),
            valid_to=datetime.date(2026, 6, 30),
        ),
        slots=[],
    )


@pytest.mark.parametrize(
    "intent, expected_ok, expected_reason",
    [
        ("HOLIDAY", True, "NOT_APPLICABLE"),
        ("TASK", True, "NOT_APPLICABLE"),
        ("EXAM_DEADLINE", True, "NOT_APPLICABLE"),
    ],
)
def test_validate_non_applicable_intents(timetable, intent, expected_ok, expected_reason):
    event = ParsedEvent(intent=intent, summary="Test summary")
    verdict = validate(event, timetable)
    assert verdict.ok == expected_ok
    assert verdict.reason == expected_reason


@pytest.mark.parametrize(
    "intent, is_sample, has_timetable",
    [
        ("ROOM_OVERRIDE", False, False),
        ("ROOM_OVERRIDE", True, True),
        ("CLASS_CANCELLED", False, False),  # Add 14th case
    ],
)
def test_validate_missing_or_sample_timetable(sample_timetable, intent, is_sample, has_timetable):
    event = ParsedEvent(intent=intent, summary="Test summary")
    tt = sample_timetable if has_timetable and is_sample else None
    verdict = validate(event, tt)
    assert verdict.ok
    assert verdict.reason == "NO_TIMETABLE"


@pytest.mark.parametrize(
    "scenario, target_date, period, room, expected_ok, expected_reason",
    [
        ("Saturday NO_SLOT (if period empty)", "2026-03-21", "", "H-002", False, "NO_SLOT"),
        (
            "Saturday (period passed -> PERIOD_MISMATCH)",
            "2026-03-21",
            "P3",
            "H-002",
            False,
            "PERIOD_MISMATCH",
        ),
        ("multi-block", "2026-03-23", "P3-P4", "H-002", True, "OK"),
        ("P6 range", "2026-03-24", "P6", "H-002", True, "OK"),
        ("clock time", "2026-03-24", "13:30 - 14:20", "H-002", False, "PERIOD_MISMATCH"),
        ("OUTSIDE_TERM", "2026-07-01", "P3", "H-002", False, "OUTSIDE_TERM"),
        ("NO_CHANGE", "2026-03-26", "P3", "H-002", False, "NO_CHANGE"),  # Thu P3 is already H-002
        (
            "AMBIGUOUS_PERIOD",
            "2026-03-27",
            "",
            "H-002",
            False,
            "AMBIGUOUS_PERIOD",
        ),  # Fri P4 and P5 are two blocks
    ],
)
def test_timetable_scenarios(
    timetable, scenario, target_date, period, room, expected_ok, expected_reason
):
    event = ParsedEvent(
        intent="ROOM_OVERRIDE",
        summary="Test",
        target_date=target_date,
        period=period,
        course_name="DSA",
        room=room,
    )
    verdict = validate(event, timetable)
    assert verdict.ok == expected_ok
    assert verdict.reason == expected_reason
