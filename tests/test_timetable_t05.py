"""Tests for Trimester 5 (T05) timetable, course mappings, and formatting."""

from datetime import date

from src.parsing.regex_parser import RegexParser
from src.timetable import COURSE_INFO, PERIOD_TIMES, format_day_schedule, load, parse_periods


def test_t05_timetable_loads_successfully():
    tt = load("data/timetable_T05.toml")
    assert tt is not None
    assert tt.meta.term == "T05"
    assert tt.meta.valid_from == date(2026, 11, 2)
    assert tt.meta.valid_to == date(2027, 2, 7)
    assert tt.meta.sample is False
    assert len(tt.slots) == 38


def test_t05_all_courses_in_course_info():
    t05_keys = ["DLAC", "CIS", "CNNP", "GENAI", "ISDG", "KABBADI"]
    for k in t05_keys:
        assert k in COURSE_INFO
        code, name = COURSE_INFO[k]
        assert code.startswith("25")
        assert len(name) > 3


def test_t05_period_times_extended():
    for p in (10, 11, 12, 13):
        assert p in PERIOD_TIMES
        assert len(PERIOD_TIMES[p]) == 6


def test_t05_wednesday_schedule():
    # 2026-11-04 is Wednesday (commencement of T05 classwork)
    sched = format_day_schedule(date(2026, 11, 4))
    assert "Deep Learning With Accelerated Computing" in sched
    assert "Cloud Infrastructure And Services" in sched
    assert "Insights to Sustainable Development Goals" in sched
    assert "25UC0032E" in sched
    assert "HC-15C" in sched
    assert "H-107" in sched
    assert "H-005" in sched
    assert "S-10" in sched
    assert "S-11" in sched


def test_t05_friday_extended_periods():
    # 2026-11-06 is Friday
    sched = format_day_schedule(date(2026, 11, 6))
    assert "Computer Networks And Network Programming" in sched
    assert "Generative Ai And Ai Platform Engineering" in sched
    assert "Kabbadi" in sched
    assert "25SP2108E" in sched
    assert "06:00 PM – 06:50 PM" in sched
    assert "06:50 PM – 07:40 PM" in sched
    assert "S-1" in sched


def test_t05_regex_course_detection():
    from datetime import datetime

    cases = [
        ("Deep learning class in room HC-15C tomorrow", "DLAC"),
        ("GenAI lab in HC-15C P3-P4", "GENAI"),
        ("Cloud infrastructure moved to H006", "CIS"),
        ("Computer networks exam on Friday", "CNNP"),
        ("Sustainable development goals class in room H-005 tomorrow", "ISDG"),
        ("Kabbadi practice in HC-15C Period 12", "KABBADI"),
    ]
    ref_dt = datetime(2026, 11, 4, 10, 0)
    for text, expected_course in cases:
        course, code = RegexParser.detect_course(text.upper())
        assert course == expected_course, f"detect_course failed for {text}"
        ev = RegexParser.parse(text, message_date=ref_dt)
        assert ev is not None, f"Failed parsing: {text}"
        assert ev.course_name == expected_course, (
            f"Expected {expected_course}, got {ev.course_name} for '{text}'"
        )


def test_parse_periods_extended():
    assert parse_periods("Period 12") == [12]
    assert parse_periods("P12-P13") == [12, 13]
    assert parse_periods("06:00 PM - 06:50 PM") == [12]
    assert parse_periods("06:50 PM - 07:40 PM") == [13]
