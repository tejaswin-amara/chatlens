import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from src.parsing.regex_parser import RegexParser

IST = ZoneInfo("Asia/Kolkata")


def test_spark_rules_parser():
    tue = datetime(2026, 9, 29, 8, 0, tzinfo=IST)
    thu = datetime(2026, 9, 24, 8, 0, tzinfo=IST)

    # "DSA3 class shifted to H106 today P3-P4" tue gives ROOM_OVERRIDE, DSA, 2026-09-29
    res1 = RegexParser.parse("DSA3 class shifted to H106 today P3-P4", tue)
    assert res1.intent == "ROOM_OVERRIDE"
    assert res1.course_name == "DSA"
    assert res1.course_code == "25CS2103E"
    assert res1.target_date == "2026-09-29"

    # "25CS2103E class moved to H-005" tue gives ROOM_OVERRIDE, DSA, 2026-09-29
    res2 = RegexParser.parse("25CS2103E class moved to H-005", tue)
    assert res2.intent == "ROOM_OVERRIDE"
    assert res2.course_name == "DSA"
    assert res2.course_code == "25CS2103E"
    assert res2.target_date == "2026-09-29"

    # "Tomorrow's ML class will be held in HC-15C" tue gives ROOM_OVERRIDE, ML, 2026-09-30
    res3 = RegexParser.parse("Tomorrow's ML class will be held in HC-15C", tue)
    assert res3.intent == "ROOM_OVERRIDE"
    assert res3.course_name == "ML"
    assert res3.target_date == "2026-09-30"

    # "OSSP lab record submission by 10 Oct" tue gives TASK, OSSP, 2026-10-10
    res4 = RegexParser.parse("OSSP lab record submission by 10 Oct", tue)
    assert res4.intent == "TASK"
    assert res4.course_name == "OSSP"
    assert res4.target_date == "2026-10-10"

    # "Classes suspended..." thu gives HOLIDAY, no course, 2026-09-25
    res5 = RegexParser.parse("Classes suspended on Friday 25th for Ganesh Shobha Yatra", thu)
    assert res5.intent == "HOLIDAY"
    assert res5.course_name is None
    assert res5.target_date == "2026-09-25"

    # "ESD & IoT class in H301A on Saturday" tue gives ROOM_OVERRIDE, ESD, 2026-10-03
    res6 = RegexParser.parse("ESD & IoT class in H301A on Saturday", tue)
    assert res6.intent == "ROOM_OVERRIDE"
    assert res6.course_name == "ESD"
    assert res6.target_date == "2026-10-03"

    # "Japanese-2 class tomorrow in H006" tue gives ROOM_OVERRIDE, JAPANESE, 2026-09-30
    res7 = RegexParser.parse("Japanese-2 class tomorrow in H006", tue)
    assert res7.intent == "ROOM_OVERRIDE"
    assert res7.course_name == "JAPANESE"
    assert res7.target_date == "2026-09-30"

    # "Last date to pay end exam fee is 26 Sep" tue gives EXAM_DEADLINE, no course, 2026-09-26
    res8 = RegexParser.parse("Last date to pay end exam fee is 26 Sep", tue)
    assert res8.intent == "EXAM_DEADLINE"
    assert res8.course_name is None
    assert res8.target_date == "2026-09-26"

    # Noise test
    assert RegexParser.parse("bro lunch at the ML canteen near H-005 gate?", tue) is None

    # IST Rollover test
    utc_msg_aware = datetime(2026, 9, 29, 20, 0, tzinfo=UTC)
    res_utc = RegexParser.parse("DSA class tomorrow in H-005", utc_msg_aware)
    assert res_utc.target_date == "2026-10-01"


def test_spark_rules_canonical():
    assert RegexParser.canonical_course("Machine Learning", None) == ("ML", "25SC2107E")
    assert RegexParser.canonical_course(None, "25EC2206E") == ("ESD", "25EC2206E")
    assert RegexParser.canonical_course(None, None) == (None, None)


def test_spark_rules_dedupe():
    db_path = "test_spark.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    from src.utils.deduplication import MessageDeduplicator

    dedup = MessageDeduplicator()
    dedup.db_path = db_path
    dedup._init_db()

    chat_id = 123
    msg_id = 456
    text1 = "hello"
    text2 = "hello changed"

    assert not dedup.is_duplicate(chat_id, msg_id, text1)
    dedup.mark_processed(chat_id, msg_id, text1)
    assert dedup.is_duplicate(chat_id, msg_id, text1)

    assert not dedup.is_duplicate(chat_id, msg_id, text2)
    dedup.mark_processed(chat_id, msg_id, text2)
    assert dedup.is_duplicate(chat_id, msg_id, text2)

    if os.path.exists(db_path):
        os.remove(db_path)


def test_spark_rules_calendar():
    from unittest.mock import MagicMock

    from src.workspace.calendar_sync import calendar_sync

    calendar_sync.auth = MagicMock()
    service_mock = MagicMock()
    calendar_sync.auth.get_calendar_service.return_value = service_mock

    # simulate two DSA events on 2026-09-29 (08:10 and 14:20 IST), P8-P9 patches only afternoon one
    items = [
        {
            "id": "ev_1",
            "summary": "DSA",
            "start": {"dateTime": "2026-09-29T02:40:00Z"},
        },  # 08:10 IST
        {
            "id": "ev_2",
            "summary": "DSA",
            "start": {"dateTime": "2026-09-29T08:50:00Z"},
        },  # 14:20 IST
    ]
    service_mock.events().list().execute.return_value = {"items": items}

    patch_mock = MagicMock()
    service_mock.events().patch.return_value = patch_mock

    calendar_sync.update_class_room("DSA", "25CS2103E", "H106", "2026-09-29", "P8-P9")

    service_mock.events().patch.assert_called_once()
    args, kwargs = service_mock.events().patch.call_args
    assert kwargs["eventId"] == "ev_2"

    # ambiguity test
    service_mock.events().patch.reset_mock()
    service_mock.events().list().execute.return_value = {"items": items}

    with pytest.raises(LookupError):
        calendar_sync.update_class_room("DSA", "25CS2103E", "H106", "2026-09-29", None)

    with pytest.raises(LookupError):
        service_mock.events().list().execute.return_value = {"items": []}
        calendar_sync.update_class_room("DSA", "25CS2103E", "H106", "2026-09-29", None)
