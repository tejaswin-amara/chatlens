"""Regression tests for the SPARK_MODE decision state machine."""

import pytest

from src.ingestion.handlers import Decision, decide


@pytest.mark.parametrize(
    ("mode", "verdict", "expected"),
    [
        ("dry", True, Decision.DRY_RUN),
        ("dry", False, Decision.DRY_RUN),
        ("confirm", True, Decision.CONFIRM),
        ("confirm", False, Decision.REVIEW),
        ("live", True, Decision.AUTO),
        ("live", False, Decision.REVIEW),
    ],
)
def test_mode_and_validation_order(mode, verdict, expected):
    """Dry mode audits every event; confirm/live review failed validation first."""
    result = decide(
        mode=mode,
        source="regex",
        event_intent="TASK",
        verdict=verdict,
        timetable_ready=True,
    )
    assert result is expected


@pytest.mark.parametrize("intent", ["ROOM_OVERRIDE", "TASK", "EXAM_DEADLINE"])
def test_live_regex_allowlisted_intents_auto_apply_when_valid(intent):
    assert (
        decide(
            mode="live",
            source="regex",
            event_intent=intent,
            verdict=True,
            timetable_ready=True,
        )
        is Decision.AUTO
    )


@pytest.mark.parametrize(
    ("source", "intent", "timetable_ready", "expected"),
    [
        ("gemini", "TASK", True, Decision.CONFIRM),
        ("gemini", "ROOM_OVERRIDE", True, Decision.CONFIRM),
        ("regex", "HOLIDAY", True, Decision.CONFIRM),
        ("regex", "CLASS_CANCELLED", True, Decision.CONFIRM),
        ("regex", "ROOM_OVERRIDE", False, Decision.CONFIRM),
        ("regex", "UNSUPPORTED_MUTATION", True, Decision.CONFIRM),
    ],
)
def test_live_mode_never_auto_applies_non_allowlisted_events(
    source, intent, timetable_ready, expected
):
    assert (
        decide(
            mode="live",
            source=source,
            event_intent=intent,
            verdict=True,
            timetable_ready=timetable_ready,
        )
        is expected
    )


def test_validation_failure_takes_precedence_over_live_auto_write():
    """Even an otherwise allowlisted event must not auto-write after failed validation."""
    assert (
        decide(
            mode="live",
            source="regex",
            event_intent="ROOM_OVERRIDE",
            verdict=False,
            timetable_ready=True,
        )
        is Decision.REVIEW
    )
