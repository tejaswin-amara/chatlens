"""Unit tests for Tier-1 Fast-Path Regex Parser."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.parsing.regex_parser import RegexParser


def test_regex_parser_sample_circulars() -> None:
    fixtures_path = Path(__file__).parent / "fixtures" / "sample_circulars.json"
    with open(fixtures_path, encoding="utf-8") as f:
        samples = json.load(f)

    ref_date = datetime(2026, 3, 30, 9, 0, 0)

    for sample in samples:
        result = RegexParser.parse(sample["text"], message_date=ref_date)
        assert result is not None, f"Failed to parse text: {sample['text']}"
        assert result.intent == sample["expected_intent"]
        if sample["expected_course"]:
            assert result.course_name == sample["expected_course"]
        if sample["expected_room"]:
            assert result.room == sample["expected_room"]
        assert result.action_required == sample["expected_action_required"]


def test_regex_parser_room_formats() -> None:
    ref_date = datetime(2026, 3, 30, 9, 0, 0)
    test_cases = [
        ("DSA shifted to H006", "H006"),
        ("ML lecture moved to HC-15C", "HC-15C"),
        ("DBSE class in H107A", "H107A"),
        ("Japanese language venue is H-005", "H-005"),
    ]

    for text, expected_room in test_cases:
        res = RegexParser.parse(text, message_date=ref_date)
        assert res is not None
        assert res.room == expected_room
        assert res.intent == "ROOM_OVERRIDE"


def test_regex_parser_none_on_unstructured() -> None:
    unstructured_texts = [
        "Hey, anyone free for lunch today?",
        "Did you guys watch the match yesterday?",
        "Please check your email for more details.",
    ]
    for text in unstructured_texts:
        res = RegexParser.parse(text)
        assert res is None


def test_regex_parser_real_circulars() -> None:
    # Optional loader for real circulars
    fixtures_path = Path(__file__).parent / "fixtures" / "real_circulars.json"
    if not fixtures_path.exists():
        pytest.skip("real_circulars.json not found")

    with open(fixtures_path, encoding="utf-8") as f:
        samples = json.load(f)
        if not samples:
            pytest.skip("real_circulars.json is empty")

    for sample in samples:
        # The owner will drop anonymized S-10/S-11 messages there.
        try:
            ref_date = datetime.fromisoformat(sample["date"])
        except Exception:
            ref_date = datetime.now()

        result = RegexParser.parse(sample["text"], message_date=ref_date)
        if sample["expected_intent"] is None:
            assert result is None
        else:
            assert result is not None
            assert result.intent == sample["expected_intent"]
            if sample["expected_course"]:
                assert result.course_name == sample["expected_course"]
            if sample["expected_room"]:
                assert result.room == sample["expected_room"]
            if sample["expected_date"]:
                assert result.target_date == sample["expected_date"]


def test_regex_parser_holiday_summary_truncation() -> None:
    long_notice = "Holiday announced by university: " + "A" * 150
    res = RegexParser.parse(long_notice)
    assert res is not None
    assert res.intent == "HOLIDAY"
    assert len(res.summary) <= 100
    assert res.summary == long_notice[:100]


def test_regex_parser_course_mapping_table() -> None:
    expected_mappings = {
        "DSA": ("25CS2103E", ["DSA", "DATA STRUCTURES", "DSA3", "DSA-3"]),
        "OSSP": ("25CS2104E", ["OSSP", "OPERATING SYSTEMS"]),
        "ML": ("25SC2107E", ["ML", "MLNG", "MACHINE LEARNING"]),
        "ESD": ("25EC2206E", ["ESD", "EBSD", "IOT", "EMBEDDED SYSTEM"]),
        "DBSE": ("25CS1302E", ["DBSE", "DATABASE SYSTEMS"]),
        "JAPANESE": ("25FL2112E", ["JAPANESE", "JPN", "FLP-2"]),
    }
    for canonical_name, (expected_code, aliases) in expected_mappings.items():
        c_name, c_code = RegexParser.canonical_course(canonical_name, None)
        assert c_name == canonical_name
        assert c_code == expected_code

        c_name2, c_code2 = RegexParser.canonical_course(None, expected_code)
        assert c_name2 == canonical_name
        assert c_code2 == expected_code

        for alias in aliases:
            text = f"Notice: {alias} class is moved to H-005"
            detected_name, detected_code = RegexParser.detect_course(text.upper())
            assert (
                detected_name == canonical_name
            ), f"Alias '{alias}' did not resolve to {canonical_name}"
            assert detected_code == expected_code
