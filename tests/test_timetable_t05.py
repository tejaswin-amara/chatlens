"""Tests for Trimester 5 (T05) timetable, course mappings, and formatting."""

from datetime import date

from src.parsing.regex_parser import RegexParser
from src.timetable import (
    COURSE_INFO,
    COURSE_METADATA,
    PERIOD_TIMES,
    T05_COURSE_METADATA,
    clear_cache,
    format_day_schedule,
    load,
    parse_periods,
)


def test_t05_timetable_loads_successfully():
    clear_cache()
    tt = load("data/timetable_T05.toml")
    assert tt is not None
    assert tt.meta.term == "T05"
    assert tt.meta.cluster == 4
    assert tt.meta.credits == 15
    assert tt.meta.contact_hours == 48
    assert tt.meta.valid_from == date(2026, 11, 2)
    assert tt.meta.valid_to == date(2027, 2, 7)
    assert tt.meta.sample is False
    assert len(tt.slots) == 48

    # Verify slot types
    slot_types = {s.slot_type for s in tt.slots}
    assert slot_types.issubset({"Skill", "Lecture", "Practical"})
    skill_slots = [s for s in tt.slots if s.slot_type == "Skill"]
    lecture_slots = [s for s in tt.slots if s.slot_type == "Lecture"]
    practical_slots = [s for s in tt.slots if s.slot_type == "Practical"]
    assert len(practical_slots) == 2  # Tue P5,7 CIS
    assert len(lecture_slots) == 10
    assert len(skill_slots) == 36
    assert len(skill_slots) + len(lecture_slots) + len(practical_slots) == 48


def test_t05_course_metadata_and_credits():
    assert len(COURSE_METADATA) == 7
    assert len(T05_COURSE_METADATA) == 7
    total_credits = sum(c.credits for c in COURSE_METADATA.values())
    assert total_credits == 15
    assert COURSE_METADATA["DLAC"].credits == 4
    assert COURSE_METADATA["CIS"].credits == 4
    assert COURSE_METADATA["GENAI"].credits == 4
    assert COURSE_METADATA["CNNP"].credits == 3
    assert COURSE_METADATA["GLBC"].credits == 0
    assert COURSE_METADATA["SDG"].credits == 0
    assert COURSE_METADATA["ISDG"].credits == 0
    assert COURSE_METADATA["KABADDI"].credits == 0
    assert COURSE_METADATA["KABBADI"].credits == 0
    assert COURSE_METADATA["DLAC"].section == "S-10"
    assert COURSE_METADATA["CIS"].section == "S-11"
    assert COURSE_METADATA["GENAI"].section == "S-10"
    assert COURSE_METADATA["CNNP"].section == "S-11"
    assert COURSE_METADATA["GLBC"].section == "S-10"
    assert COURSE_METADATA["SDG"].section == "S-10"
    assert COURSE_METADATA["KABADDI"].section == "S-1"


def test_t05_all_courses_in_course_info():
    t05_keys = ["DLAC", "CIS", "CNNP", "GENAI", "GLBC", "SDG", "ISDG", "KABADDI", "KABBADI"]
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
    clear_cache()
    # 2026-11-04 is Wednesday (commencement of T05 classwork)
    sched = format_day_schedule(date(2026, 11, 4))
    assert "Global Logic Building Contest Practicum" in sched
    assert "Deep Learning With Accelerated Computing" in sched
    assert "Cloud Infrastructure And Services" in sched
    assert "Insights to Sustainable Development Goals" in sched
    assert "25UC0037" in sched
    assert "25UC0032E" in sched
    assert "HC-15C" in sched
    assert "H-107" in sched
    assert "H-005" in sched
    assert "S-10" in sched
    assert "S-11" in sched
    assert "Anitha Chekuri" in sched
    assert "Divya Priya Degala" in sched
    assert "Sama Mineesha" in sched


def test_t05_friday_schedule():
    clear_cache()
    # 2026-11-06 is Friday
    sched = format_day_schedule(date(2026, 11, 6))
    assert "Computer Networks And Network Programming" in sched
    assert "Generative Ai And Ai Platform Engineering" in sched
    assert "Deep Learning With Accelerated Computing" in sched
    assert "Kabaddi" in sched
    assert "25SP2108E" in sched
    assert "HC-15D" in sched
    assert "H-005" in sched
    assert "HC-15C" in sched
    assert "Dasari Alekhya" in sched
    assert "LakshmiPrasanna Yeluri" in sched
    assert "Anitha Chekuri" in sched
    assert "Ediga Raja Gopal" in sched
    assert "S-1" in sched


def test_t05_regex_course_detection():
    from datetime import datetime

    cases = [
        ("Deep learning class in room HC-15C tomorrow", "DLAC"),
        ("GenAI lab in HC-15C P3-P4", "GENAI"),
        ("Cloud infrastructure moved to H006", "CIS"),
        ("Computer networks exam on Friday", "CNNP"),
        ("Global logic building practicum in HC-15C tomorrow", "GLBC"),
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
    assert parse_periods("P5 & P7") == [5, 7]
    assert parse_periods("P5 & P7 [P6 Lunch]") == [5, 7]
    assert parse_periods("P1 & P2") == [1, 2]
    assert parse_periods("P8 & P9") == [8, 9]
    assert parse_periods("09:00 - 10:40") == [1, 2]
    assert parse_periods("10:50 - 12:30") == [3, 4]
    assert parse_periods("12:40 - 13:30") == [5]
    assert parse_periods("14:20 - 15:10") == [7]
    assert parse_periods("15:20 - 17:00") == [8, 9]


def test_t05_slot_types():
    clear_cache()
    tt = load("data/timetable_T05.toml")
    assert tt is not None
    assert len(tt.slots) == 48

    # Assert specific day slot types
    slots_by_day = {}
    for s in tt.slots:
        slots_by_day.setdefault(s.day, []).append(s)

    for _day, slots in slots_by_day.items():
        slots.sort(key=lambda x: x.period)

    # Check Wednesday (Skill, Skill, Skill, Skill, Skill, Skill, Lecture, Lecture)
    wed_slots = sorted(slots_by_day["Wed"], key=lambda x: x.period)
    assert wed_slots[0].period == 1 and wed_slots[0].slot_type == "Skill"
    assert wed_slots[1].period == 2 and wed_slots[1].slot_type == "Skill"
    assert wed_slots[2].period == 3 and wed_slots[2].slot_type == "Skill"
    assert wed_slots[3].period == 4 and wed_slots[3].slot_type == "Skill"
    assert wed_slots[4].period == 5 and wed_slots[4].slot_type == "Skill"
    assert wed_slots[5].period == 7 and wed_slots[5].slot_type == "Skill"
    assert wed_slots[6].period == 8 and wed_slots[6].slot_type == "Lecture"
    assert wed_slots[7].period == 9 and wed_slots[7].slot_type == "Lecture"

    # Check Friday
    fri_slots = sorted(slots_by_day["Fri"], key=lambda x: x.period)
    assert fri_slots[0].period == 1 and fri_slots[0].slot_type == "Skill"
    assert fri_slots[1].period == 2 and fri_slots[1].slot_type == "Skill"
    assert fri_slots[2].period == 3 and fri_slots[2].slot_type == "Lecture"
    assert fri_slots[3].period == 4 and fri_slots[3].slot_type == "Lecture"
    assert fri_slots[4].period == 5 and fri_slots[4].slot_type == "Skill"
    assert fri_slots[5].period == 7 and fri_slots[5].slot_type == "Skill"
    assert fri_slots[6].period == 8 and fri_slots[6].slot_type == "Skill"
    assert fri_slots[7].period == 9 and fri_slots[7].slot_type == "Skill"


def test_t05_weekly_contact_hours_and_credits():
    clear_cache()
    tt = load("data/timetable_T05.toml")
    assert tt is not None

    # Total weekly contact hours is number of slots
    assert len(tt.slots) == 48

    # Total registered credits is defined in metadata
    assert tt.meta.credits == 15
    assert tt.meta.cluster == 4
    assert tt.meta.contact_hours == 48


def test_t05_period_6_is_unassigned_lunch_separator_across_all_days():
    clear_cache()
    tt = load("data/timetable_T05.toml")
    assert tt is not None
    p6_slots = [s for s in tt.slots if s.period == 6]
    assert len(p6_slots) == 0, (
        f"Period 6 must be unassigned lunch separator, found {len(p6_slots)} slots"
    )
    # Verify operational days (Mon-Sat) all exist in slots
    operational_days = {s.day for s in tt.slots}
    assert operational_days == {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat"}

    # Verify each day has exactly 8 periods: 1, 2, 3, 4, 5, 7, 8, 9
    expected_periods = [1, 2, 3, 4, 5, 7, 8, 9]
    for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat"):
        day_periods = [s.period for s in tt.slots if s.day == day]
        assert day_periods == expected_periods, f"{day} periods mismatch: {day_periods}"


def test_t05_exact_rooms_and_faculty_assignments():
    clear_cache()
    tt = load("data/timetable_T05.toml")
    assert tt is not None

    expected_schedule = {
        "Mon": [
            (1, "GENAI", "H-005", "LakshmiPrasanna Yeluri", "S-10", "Skill"),
            (2, "GENAI", "H-005", "LakshmiPrasanna Yeluri", "S-10", "Skill"),
            (3, "CIS", "H006", "Divya Priya Degala", "S-11", "Lecture"),
            (4, "CIS", "H006", "Divya Priya Degala", "S-11", "Lecture"),
            (5, "DLAC", "H-005", "Anitha Chekuri", "S-10", "Skill"),
            (7, "DLAC", "H-005", "Anitha Chekuri", "S-10", "Skill"),
            (8, "GLBC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
            (9, "GLBC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
        ],
        "Tue": [
            (1, "DLAC", "H107A", "Anitha Chekuri", "S-10", "Skill"),
            (2, "DLAC", "H107A", "Anitha Chekuri", "S-10", "Skill"),
            (3, "GENAI", "HC-15C", "LakshmiPrasanna Yeluri", "S-10", "Skill"),
            (4, "GENAI", "HC-15C", "LakshmiPrasanna Yeluri", "S-10", "Skill"),
            (5, "CIS", "HC-15D", "Divya Priya Degala", "S-11", "Practical"),
            (7, "CIS", "HC-15D", "Divya Priya Degala", "S-11", "Practical"),
            (8, "GLBC", "HC-15D", "Anitha Chekuri", "S-10", "Skill"),
            (9, "GLBC", "HC-15D", "Anitha Chekuri", "S-10", "Skill"),
        ],
        "Wed": [
            (1, "GLBC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
            (2, "GLBC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
            (3, "DLAC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
            (4, "DLAC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
            (5, "CIS", "H-107", "Divya Priya Degala", "S-11", "Skill"),
            (7, "CIS", "H-107", "Divya Priya Degala", "S-11", "Skill"),
            (8, "SDG", "H-005", "Sama Mineesha", "S-10", "Lecture"),
            (9, "SDG", "H-005", "Sama Mineesha", "S-10", "Lecture"),
        ],
        "Thu": [
            (1, "DLAC", "H005C", "Anitha Chekuri", "S-10", "Lecture"),
            (2, "DLAC", "H005C", "Anitha Chekuri", "S-10", "Lecture"),
            (3, "GENAI", "HC-15C", "LakshmiPrasanna Yeluri", "S-10", "Skill"),
            (4, "GENAI", "HC-15C", "LakshmiPrasanna Yeluri", "S-10", "Skill"),
            (5, "CNNP", "H107B", "Dasari Alekhya", "S-11", "Skill"),
            (7, "CNNP", "H107B", "Dasari Alekhya", "S-11", "Skill"),
            (8, "GLBC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
            (9, "GLBC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
        ],
        "Fri": [
            (1, "CNNP", "HC-15D", "Dasari Alekhya", "S-11", "Skill"),
            (2, "CNNP", "HC-15D", "Dasari Alekhya", "S-11", "Skill"),
            (3, "GENAI", "H-005", "LakshmiPrasanna Yeluri", "S-10", "Lecture"),
            (4, "GENAI", "H-005", "LakshmiPrasanna Yeluri", "S-10", "Lecture"),
            (5, "DLAC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
            (7, "DLAC", "HC-15C", "Anitha Chekuri", "S-10", "Skill"),
            (8, "KABADDI", "HC-15C", "Ediga Raja Gopal", "S-1", "Skill"),
            (9, "KABADDI", "HC-15C", "Ediga Raja Gopal", "S-1", "Skill"),
        ],
        "Sat": [
            (1, "CIS", "H-005", "Divya Priya Degala", "S-11", "Skill"),
            (2, "CIS", "H-005", "Divya Priya Degala", "S-11", "Skill"),
            (3, "CNNP", "H006", "Dasari Alekhya", "S-11", "Lecture"),
            (4, "CNNP", "H006", "Dasari Alekhya", "S-11", "Lecture"),
            (5, "GENAI", "H-005", "LakshmiPrasanna Yeluri", "S-10", "Skill"),
            (7, "GENAI", "H-005", "LakshmiPrasanna Yeluri", "S-10", "Skill"),
            (8, "GLBC", "H-005", "Anitha Chekuri", "S-10", "Skill"),
            (9, "GLBC", "H-005", "Anitha Chekuri", "S-10", "Skill"),
        ],
    }

    for day, slots in expected_schedule.items():
        actual_slots = [s for s in tt.slots if s.day == day]
        assert len(actual_slots) == 8, f"{day} should have 8 slots, got {len(actual_slots)}"
        for actual, expected in zip(actual_slots, slots, strict=True):
            exp_p, exp_course, exp_room, exp_faculty, exp_sec, exp_type = expected
            assert actual.period == exp_p, f"{day} period mismatch: {actual.period} vs {exp_p}"
            assert actual.course == exp_course, (
                f"{day} course mismatch: {actual.course} vs {exp_course}"
            )
            assert actual.room == exp_room, f"{day} room mismatch: {actual.room} vs {exp_room}"
            assert actual.faculty == exp_faculty, (
                f"{day} faculty mismatch: {actual.faculty} vs {exp_faculty}"
            )
            assert actual.section == exp_sec, (
                f"{day} section mismatch: {actual.section} vs {exp_sec}"
            )
            assert actual.slot_type == exp_type, (
                f"{day} type mismatch: {actual.slot_type} vs {exp_type}"
            )
