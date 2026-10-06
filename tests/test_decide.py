import pytest

from src.ingestion.handlers import Decision, decide


@pytest.mark.parametrize(
    "mode, source, intent, timetable_ready, expected",
    [
        # DRY_RUN tests
        ("dry", "text", "TASK", True, Decision.DRY_RUN),
        ("dry", "regex", "CLASS_CANCELLED", True, Decision.DRY_RUN),
        ("dry", "gemini", "ROOM_OVERRIDE", True, Decision.DRY_RUN),
        ("dry", "photo", "HOLIDAY", True, Decision.DRY_RUN),
        # LIVE mode tests
        # Auto-writes
        ("live", "regex", "ROOM_OVERRIDE", True, Decision.AUTO),
        ("live", "regex", "TASK", True, Decision.AUTO),
        ("live", "regex", "EXAM_DEADLINE", True, Decision.AUTO),
        # Requires confirm in LIVE
        ("live", "regex", "ROOM_OVERRIDE", False, Decision.CONFIRM),  # Timetable missing/sample
        ("live", "gemini", "TASK", True, Decision.CONFIRM),
        ("live", "voice", "TASK", True, Decision.CONFIRM),
        ("live", "photo", "ROOM_OVERRIDE", True, Decision.CONFIRM),
        ("live", "pdf", "EXAM_DEADLINE", True, Decision.CONFIRM),
        ("live", "text", "HOLIDAY", True, Decision.CONFIRM),
        ("live", "regex", "HOLIDAY", True, Decision.CONFIRM),
        ("live", "regex", "CLASS_CANCELLED", True, Decision.CONFIRM),
        ("live", "gemini", "CLASS_CANCELLED", True, Decision.CONFIRM),
        # CONFIRM mode tests
        ("confirm", "regex", "ROOM_OVERRIDE", True, Decision.CONFIRM),
        ("confirm", "regex", "TASK", True, Decision.CONFIRM),
        ("confirm", "gemini", "EXAM_DEADLINE", True, Decision.CONFIRM),
        ("confirm", "photo", "HOLIDAY", True, Decision.CONFIRM),
    ],
)
def test_decide_valid(mode, source, intent, timetable_ready, expected):
    # Simulating a passed validation (verdict=True)
    assert decide(mode, source, intent, True, timetable_ready) == expected


@pytest.mark.parametrize(
    "mode, source, intent, timetable_ready",
    [
        ("live", "regex", "ROOM_OVERRIDE", True),
        ("live", "gemini", "TASK", True),
        ("confirm", "regex", "ROOM_OVERRIDE", True),
        ("dry", "text", "TASK", True),
    ],
)
def test_decide_invalid(mode, source, intent, timetable_ready):
    # Simulating a failed validation always triggers REVIEW
    assert decide(mode, source, intent, False, timetable_ready) == (
        Decision.DRY_RUN if mode == "dry" else Decision.REVIEW
    )
