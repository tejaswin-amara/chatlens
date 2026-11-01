"""Unit tests for Academic Calendar 2026-2027 loading, parsing, and milestone guards."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from src.academic_calendar import (
    CalendarEvent,
    get_milestone_date,
    get_milestone_window,
    load_calendar,
)
from src.config import settings


def test_calendar_loads_all_four_terms():
    cal = load_calendar()
    assert cal is not None
    assert "T04" in cal.terms
    assert "T05" in cal.terms
    assert "T06" in cal.terms
    assert "Summer" in cal.terms
    assert cal.events is not None
    assert len(cal.events["T04"]) > 0
    assert len(cal.events["T05"]) > 0
    assert len(cal.events["T06"]) > 0
    assert len(cal.events["Summer"]) > 0


@pytest.mark.parametrize(
    "term, milestone, expected_date",
    [
        # Trimester-4
        ("T04", "mid-term", date(2026, 9, 4)),
        ("T04", "re-check", date(2026, 9, 12)),
        ("T04", "fee", date(2026, 9, 26)),
        ("T04", "lab exam", date(2026, 10, 12)),
        ("T04", "last instruction", date(2026, 10, 15)),
        ("T04", "detention", date(2026, 10, 16)),
        ("T04", "sem-end", date(2026, 10, 26)),
        # Trimester-5
        ("T05", "mid-term", date(2026, 12, 14)),
        ("T05", "re-check", date(2026, 12, 24)),
        ("T05", "fee", date(2027, 1, 9)),
        ("T05", "lab exam", date(2027, 1, 18)),
        ("T05", "last instruction", date(2027, 1, 28)),
        ("T05", "detention", date(2027, 1, 29)),
        ("T05", "sem-end", date(2027, 2, 1)),
        # Trimester-6
        ("T06", "mid-term", date(2027, 3, 22)),
        ("T06", "re-check", date(2027, 3, 31)),
        ("T06", "fee", date(2027, 4, 10)),
        ("T06", "lab exam", date(2027, 4, 19)),
        ("T06", "last instruction", date(2027, 4, 29)),
        ("T06", "detention", date(2027, 4, 30)),
        ("T06", "sem-end", date(2027, 5, 2)),
        # Summer Term
        ("Summer", "mid-term", date(2027, 6, 18)),
        ("Summer", "lab exam", date(2027, 6, 29)),
        ("Summer", "detention", date(2027, 7, 7)),
        ("Summer", "sem-end", date(2027, 7, 8)),
    ],
)
def test_official_milestone_dates(term, milestone, expected_date):
    cal = load_calendar()
    assert cal is not None
    assert milestone in cal.terms[term]
    assert cal.terms[term][milestone] == expected_date


def test_structured_calendar_events():
    cal = load_calendar()
    assert cal is not None
    assert cal.events is not None

    # T04 orientation
    t4_events = {e.milestone: e for e in cal.events["T04"]}
    assert "orientation" in t4_events
    ev_orient = t4_events["orientation"]
    assert isinstance(ev_orient, CalendarEvent)
    assert ev_orient.start_date == date(2026, 7, 13)
    assert ev_orient.end_date == date(2026, 7, 18)

    # T05 immersion
    t5_events = {e.milestone: e for e in cal.events["T05"]}
    assert "immersion" in t5_events
    ev_imm = t5_events["immersion"]
    assert ev_imm.start_date == date(2026, 10, 30)
    assert ev_imm.end_date == date(2026, 10, 31)

    # T06 cultural immersion
    t6_events = {e.milestone: e for e in cal.events["T06"]}
    assert "immersion" in t6_events
    ev_cult = t6_events["immersion"]
    assert ev_cult.start_date == date(2027, 3, 12)
    assert ev_cult.end_date == date(2027, 3, 13)

    # Summer internships
    summer_events = {e.milestone: e for e in cal.events["Summer"]}
    assert "technical internship" in summer_events
    assert summer_events["technical internship"].start_date == date(2027, 5, 10)
    assert summer_events["technical internship"].end_date == date(2027, 5, 29)

    assert "summer internship" in summer_events
    assert summer_events["summer internship"].start_date == date(2027, 5, 10)
    assert summer_events["summer internship"].end_date == date(2027, 7, 3)

    assert "commencement next year" in summer_events
    assert summer_events["commencement next year"].start_date == date(2027, 7, 12)


def test_milestone_resolution_by_reference_date():
    cal = load_calendar()
    assert cal is not None

    # Reference date in August 2026 resolves to T04
    d_fee_t4 = get_milestone_date("fee", date(2026, 8, 15), cal)
    assert d_fee_t4 == date(2026, 9, 26)

    # Reference date in December 2026 resolves to T05
    d_fee_t5 = get_milestone_date("fee", date(2026, 12, 1), cal)
    assert d_fee_t5 == date(2027, 1, 9)

    # Reference date in March 2027 resolves to T06
    d_fee_t6 = get_milestone_date("fee", date(2027, 3, 1), cal)
    assert d_fee_t6 == date(2027, 4, 10)

    # Reference date in June 2027 resolves to Summer
    d_mid_summer = get_milestone_date("mid-term", date(2027, 6, 1), cal)
    assert d_mid_summer == date(2027, 6, 18)


def test_term_hint_resolution():
    cal = load_calendar()
    assert cal is not None

    # T5 orientation occurs in Oct 2026 while T4 is active
    # With term_hint, correctly resolves to T5 orientation window
    orient_t5 = get_milestone_date("orientation", date(2026, 10, 6), cal, term_hint="T05")
    assert orient_t5 == date(2026, 10, 6)

    orient_t5_shorthand = get_milestone_date("orientation", date(2026, 10, 6), cal, term_hint="T5")
    assert orient_t5_shorthand == date(2026, 10, 6)

    # T6 query with term_hint
    fee_t6 = get_milestone_date("fee", date(2026, 8, 1), cal, term_hint="Trimester 6")
    assert fee_t6 == date(2027, 4, 10)

    # Summer query with term_hint
    det_summer = get_milestone_date("detention", date(2026, 8, 1), cal, term_hint="summer")
    assert det_summer == date(2027, 7, 7)


def test_milestone_window_checks():
    cal = load_calendar()
    assert cal is not None

    # T4 Mid-term is 4-Sep-26 to 8-Sep-26
    # Date inside window returns the queried date (no false-positive conflict)
    assert get_milestone_date("mid-term", date(2026, 9, 4), cal) == date(2026, 9, 4)
    assert get_milestone_date("mid-term", date(2026, 9, 6), cal) == date(2026, 9, 6)
    assert get_milestone_date("mid-term", date(2026, 9, 8), cal) == date(2026, 9, 8)

    # Date outside window returns official start date (triggers conflict detection)
    assert get_milestone_date("mid-term", date(2026, 9, 20), cal) == date(2026, 9, 4)

    # T5 Lab Exam is 18-Jan-27 to 23-Jan-27
    assert get_milestone_date("lab exam", date(2027, 1, 20), cal) == date(2027, 1, 20)
    assert get_milestone_date("lab exam", date(2027, 1, 10), cal) == date(2027, 1, 18)

    # get_milestone_window queries
    w_mid = get_milestone_window("mid-term", date(2026, 9, 6), cal)
    assert w_mid == (date(2026, 9, 4), date(2026, 9, 8))

    w_fee = get_milestone_window("fee", date(2026, 8, 15), cal)
    assert w_fee == (date(2026, 9, 26), date(2026, 9, 26))

    w_sem_end = get_milestone_window("sem-end", date(2027, 1, 15), cal)
    assert w_sem_end == (date(2027, 2, 1), date(2027, 2, 7))

    assert get_milestone_window("nonexistent", date(2026, 9, 1), cal) is None


def test_invariant_5_milestone_protection_across_all_terms():
    """Ensure routine messages cannot modify official academic milestones (Invariant 5).

    Tests conflict detection across all 4 terms.
    """
    cal = load_calendar()
    assert cal is not None

    test_cases = [
        # (term, milestone, routine_message_date, official_start_date)
        ("T04", "fee", date(2026, 9, 20), date(2026, 9, 26)),
        ("T04", "last instruction", date(2026, 10, 20), date(2026, 10, 15)),
        ("T05", "detention", date(2027, 1, 20), date(2027, 1, 29)),
        ("T05", "fee", date(2027, 1, 15), date(2027, 1, 9)),
        ("T06", "mid-term", date(2027, 3, 10), date(2027, 3, 22)),
        ("T06", "fee", date(2027, 4, 15), date(2027, 4, 10)),
        ("Summer", "mid-term", date(2027, 6, 10), date(2027, 6, 18)),
        ("Summer", "sem-end", date(2027, 7, 1), date(2027, 7, 8)),
    ]

    for term, milestone, routine_dt, official_dt in test_cases:
        cal_date = get_milestone_date(milestone, routine_dt, cal, term_hint=term)
        # Cal date returns official start, which differs from unauthorized routine message date
        assert cal_date == official_dt
        assert cal_date != routine_dt, f"Undetected Invariant 5 conflict: {term} {milestone}"

    # Confirm that legitimate notices matching official dates pass with zero conflict
    for term, milestone, _, official_dt in test_cases:
        cal_date = get_milestone_date(milestone, official_dt, cal, term_hint=term)
        assert cal_date == official_dt


def test_graceful_missing_and_malformed_calendar_handling():
    # Non-existent file
    assert load_calendar("non_existent_file_xyz.toml") is None

    # Safe handling with None calendar
    assert get_milestone_date("fee", date(2026, 9, 1), None) is None
    assert get_milestone_window("fee", date(2026, 9, 1), None) is None

    # Corrupt TOML file
    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as tf:
        tf.write("invalid [[[ toml syntax")
        tf_path = tf.name

    try:
        assert load_calendar(tf_path) is None
    finally:
        Path(tf_path).unlink(missing_ok=True)

    # Valid TOML but with unexpected structure (e.g. non-dict top levels)
    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as tf:
        tf.write(
            """
            version = 1
            author = "Unknown"
            [T04]
            name = "Trimester 4"
            fee = 2026-09-26
            events = [
                "invalid",
                123,
                { name = "Valid", start_date = 2026-09-01, milestone = "valid" },
            ]
            """
        )
        tf_path = tf.name

    try:
        corrupt_cal = load_calendar(tf_path)
        assert corrupt_cal is not None
        assert "T04" in corrupt_cal.terms
        assert corrupt_cal.terms["T04"]["fee"] == date(2026, 9, 26)
        assert corrupt_cal.events is not None
        assert len(corrupt_cal.events["T04"]) == 1
        assert corrupt_cal.events["T04"][0].milestone == "valid"
    finally:
        Path(tf_path).unlink(missing_ok=True)


def test_argument_order_polymorphism():
    cal = load_calendar()
    assert cal is not None

    # Style 1: (milestone, ref_date, cal)
    d1 = get_milestone_date("fee", date(2026, 8, 15), cal)
    assert d1 == date(2026, 9, 26)

    # Style 2: (cal, milestone, ref_date)
    d2 = get_milestone_date(cal, "fee", date(2026, 8, 15))
    assert d2 == date(2026, 9, 26)

    # String date input
    d3 = get_milestone_date("fee", "2026-08-15", cal)
    assert d3 == date(2026, 9, 26)

    # Window query style 2
    w1 = get_milestone_window(cal, "mid-term", date(2026, 9, 6))
    assert w1 == (date(2026, 9, 4), date(2026, 9, 8))


def test_config_setting_loads_default_calendar():
    assert settings.spark_calendar == "data/calendar_2026_27.toml"
    cal = load_calendar()
    assert cal is not None
    assert "T04" in cal.terms
