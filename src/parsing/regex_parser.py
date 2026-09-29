"""Tier-1 Fast-Path Regex Parser for deterministic academic announcements."""

import re
from datetime import datetime, timedelta

from src.parsing.schemas import ExtractedAcademicEvent

COURSES = {
    "DSA": ["DSA", "DATA STRUCTURES", "25CS2101"],
    "OSSP": ["OSSP", "OPEN SOURCE", "25CS2102"],
    "ML": ["ML", "MACHINE LEARNING", "25CS2103E"],
    "ESD": ["ESD", "EMBEDDED SYSTEM DESIGN", "EMBEDDED SYSTEMS", "25CS2104"],
    "DBSE": ["DBSE", "DATABASE SYSTEMS", "25CS2105"],
    "JAPANESE": ["JAPANESE", "JPN", "JAP", "25LN1101"],
}

COURSE_CODES = {
    "DSA": "25CS2101",
    "OSSP": "25CS2102",
    "ML": "25CS2103E",
    "ESD": "25CS2104",
    "DBSE": "25CS2105",
    "JAPANESE": "25LN1101",
}

ROOM_PATTERN = re.compile(r"\b(H[C]?[- ]?\d{2,3}[A-Z]?)\b", re.IGNORECASE)
PERIOD_PATTERN = re.compile(
    r"\b(PERIOD[- ]?[1-9]|P[1-9](?:[- ]?P[1-9])?|\d{1,2}:\d{2}\s*(?:AM|PM))\b", re.IGNORECASE
)
SECTION_PATTERN = re.compile(r"\b(S[- ]?10|S[- ]?11)\b", re.IGNORECASE)
HOLIDAY_PATTERN = re.compile(
    r"\b(HOLIDAY|NO CLASSES|CLASSES CANCELLED|UNIVERSITY CLOSED|DECLARED HOLIDAY)\b",
    re.IGNORECASE,
)
TASK_PATTERN = re.compile(
    r"\b(SUBMIT|SUBMISSION|DUE BY|DEADLINE|PAY FEE|ASSIGNMENT|RECORD|EXAM|MIDTERM)\b",
    re.IGNORECASE,
)
ROOM_OVERRIDE_VERBS = re.compile(
    r"\b(MOVED TO|SHIFTED TO|VENUE|CONDUCTED IN|CLASS IN|ROOM)\b", re.IGNORECASE
)


class RegexParser:
    @staticmethod
    def parse(text: str, message_date: datetime | None = None) -> ExtractedAcademicEvent | None:
        if not text or not text.strip():
            return None

        clean_text = text.strip()
        upper_text = clean_text.upper()
        ref_date = message_date or datetime.now()

        detected_course: str | None = None
        detected_code: str | None = None
        for course_key, aliases in COURSES.items():
            if any(re.search(rf"\b{re.escape(alias)}\b", upper_text) for alias in aliases):
                detected_course = course_key
                detected_code = COURSE_CODES.get(course_key)
                break

        room_match = ROOM_PATTERN.search(clean_text)
        detected_room = room_match.group(1).upper().replace(" ", "-") if room_match else None

        period_match = PERIOD_PATTERN.search(clean_text)
        detected_period = period_match.group(1).upper() if period_match else None

        target_date_str = ref_date.strftime("%Y-%m-%d")
        if "TOMORROW" in upper_text:
            target_date_str = (ref_date + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", clean_text)
            if date_match:
                target_date_str = date_match.group(1)

        # 1. Holiday check
        if HOLIDAY_PATTERN.search(clean_text):
            return ExtractedAcademicEvent(
                intent="HOLIDAY",
                course_name=detected_course,
                course_code=detected_code,
                room=None,
                target_date=target_date_str,
                period=None,
                summary=f"University Holiday Notice: {clean_text[:100]}",
                action_required=False,
            )

        # 2. Exam / Deadline Task check
        if TASK_PATTERN.search(clean_text):
            is_exam = "EXAM" in upper_text or "MIDTERM" in upper_text
            intent_type = "EXAM_DEADLINE" if is_exam else "TASK"
            return ExtractedAcademicEvent(
                intent=intent_type,
                course_name=detected_course,
                course_code=detected_code,
                room=detected_room,
                target_date=target_date_str,
                period=detected_period,
                summary=clean_text[:150],
                action_required=True,
            )

        # 3. Room Override check
        if detected_room and (
            ROOM_OVERRIDE_VERBS.search(clean_text) or detected_course or detected_period
        ):
            summary_parts = [f"Room for {detected_course or 'Class'} updated to {detected_room}"]
            if detected_period:
                summary_parts.append(f"during {detected_period}")
            return ExtractedAcademicEvent(
                intent="ROOM_OVERRIDE",
                course_name=detected_course,
                course_code=detected_code,
                room=detected_room,
                target_date=target_date_str,
                period=detected_period,
                summary=" ".join(summary_parts),
                action_required=False,
            )

        return None
