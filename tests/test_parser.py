from datetime import datetime

from src.parsing.regex_parser import SECTION_PATTERN, RegexParser


def test_t05_parsing():
    ref_date = datetime(2026, 11, 4, 10, 0)

    # DLAC
    ev = RegexParser.parse(
        "Deep Learning With Accelerated Computing moved to H005C during P10",
        message_date=ref_date,
    )
    assert ev.course_name == "DLAC"
    assert ev.room == "H005C"
    assert ev.period == "P10"

    # CIS
    ev = RegexParser.parse(
        "Cloud Infrastructure And Services class in H-005 from 16:10-17:00",
        message_date=ref_date,
    )
    assert ev.course_name == "CIS"
    assert ev.room == "H-005"
    assert ev.period == "P10"

    # GENAI
    ev = RegexParser.parse("GenAI in HC-15D from 17:00-17:50", message_date=ref_date)
    assert ev.course_name == "GENAI"
    assert ev.room == "HC-15D"
    assert ev.period == "P11"

    # CNNP
    ev = RegexParser.parse("CNNP class in H107B from 18:00 - 18:50", message_date=ref_date)
    assert ev.course_name == "CNNP"
    assert ev.room == "H107B"
    assert ev.period == "P12"

    # KABBADI
    ev = RegexParser.parse("Kabaddi moved to H-107 from 18:50-19:40", message_date=ref_date)
    assert ev.course_name == "KABBADI"
    assert ev.room == "H-107"
    assert ev.period == "P13"

    # ISDG
    ev = RegexParser.parse("SDG class in Section 10 in H006", message_date=ref_date)
    assert ev.course_name == "ISDG"
    assert ev.room == "H006"

    # Section tests
    assert SECTION_PATTERN.search("Sec 11")
    assert SECTION_PATTERN.search("Section 10")
    assert SECTION_PATTERN.search("S-1")
    assert SECTION_PATTERN.search("S10")
