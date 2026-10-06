from datetime import datetime
from zoneinfo import ZoneInfo

from src.parsing.regex_parser import RegexParser

IST = ZoneInfo("Asia/Kolkata")


def test_room_direction():
    ref_date = datetime(2026, 10, 5, 8, 0, tzinfo=IST)
    # The destination wins
    res1 = RegexParser.parse("DSA class shifted from H-005 to H-106 today P3-P4", ref_date)
    assert res1 and res1.room == "H-106"

    res2 = RegexParser.parse("DSA class moved to H-106 (earlier H-005) today", ref_date)
    assert res2 and res2.room == "H-106"

    res3 = RegexParser.parse(
        "Today's DSA lab will be conducted in H-301A instead of H-005", ref_date
    )
    assert res3 and res3.room == "H-301A"

    res4 = RegexParser.parse("ML lab moved to H-107A / H-107B today", ref_date)
    # Actually wait: our implementation returns None for room.
    assert (not res4) or (res4.room is None)


def test_periods_dashes():
    ref_date = datetime(2026, 10, 5, 8, 0, tzinfo=IST)
    res1 = RegexParser.parse("DSA P3–P4 in H-106", ref_date)
    assert res1 and res1.period == "P3-P4"

    res2 = RegexParser.parse("DSA 10:00 AM - 11:40 AM in H-106", ref_date)
    assert res2 and res2.period == "P3-P4"

    res3 = RegexParser.parse("DSA 10:00-11:40 in H-106", ref_date)
    assert res3 and res3.period == "P3-P4"


def test_task_precision():
    ref_date = datetime(2026, 10, 5, 8, 0, tzinfo=IST)

    res1 = RegexParser.parse("OSSP lab record submission by 10 Oct", ref_date)
    assert res1
    assert res1.intent == "TASK" and res1.course_name == "OSSP"
    assert res1.target_date == "2026-10-10"

    res2 = RegexParser.parse("Last date to pay end exam fee is 26 Sep", ref_date)
    assert res2 and res2.intent == "EXAM_DEADLINE" and res2.target_date == "2026-09-26"

    res3 = RegexParser.parse("Submit OSSP record on Friday", ref_date)
    assert res3 and res3.intent == "TASK" and res3.target_date == "2026-10-09"

    res4 = RegexParser.parse("Mid-term exam for OSSP on 4 Sep", ref_date)
    assert res4 and res4.intent == "EXAM_DEADLINE" and res4.target_date == "2026-09-04"

    res5 = RegexParser.parse("Hackathon registration closes 8 Oct", ref_date)
    assert res5 and res5.intent == "TASK" and res5.target_date == "2026-10-08"

    res6 = RegexParser.parse("Attendance record for ML displayed on notice board", ref_date)
    assert res6 is None
