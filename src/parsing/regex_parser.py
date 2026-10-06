"""Tier-1 Fast-Path Regex Parser for deterministic academic announcements."""

import re
from datetime import datetime, timedelta

from src.parsing.schemas import ExtractedAcademicEvent
from src.utils import clock

IST = clock.IST


COURSES = {
    "DSA": ["DSA", "DATA STRUCTURES", "DSA3", "DSA-3"],
    "OSSP": ["OSSP", "OPERATING SYSTEMS"],
    "ML": ["ML", "MLNG", "MACHINE LEARNING"],
    "ESD": ["ESD", "EBSD", "IOT", "EMBEDDED SYSTEM"],
    "DBSE": ["DBSE", "DATABASE SYSTEMS"],
    "JAPANESE": ["JAPANESE", "JPN", "FLP-2"],
}

COURSE_CODES = {
    "DSA": "25CS2103E",
    "OSSP": "25CS2104E",
    "ML": "25SC2107E",
    "ESD": "25EC2206E",
    "DBSE": "25CS1302E",
    "JAPANESE": "25FL2112E",
}

ROOM_PATTERN = re.compile(r"\b(H[C]?[- ]?\d{2,3}[A-Z]?)\b", re.IGNORECASE)
PERIOD_PATTERN = re.compile(
    r"\b(PERIOD[- ]?[1-9]|P[1-9](?:[- ]?P[1-9])?|\d{1,2}:\d{2}\s*(?:AM|PM))\b", re.IGNORECASE
)
SECTION_PATTERN = re.compile(r"\b(S[- ]?10|S[- ]?11)\b", re.IGNORECASE)
HOLIDAY_PATTERN = re.compile(
    r"\b(HOLIDAY|NO CLASSES|CLASSES(?: ARE| WILL BE)? (?:CANCELLED|CANCELED|SUSPENDED)|"
    r"UNIVERSITY CLOSED|NON-INSTRUCTIONAL)\b",
    re.IGNORECASE,
)
TASK_ACTION_CUES = re.compile(
    r"\b(SUBMIT|SUBMISSION|DUE|DEADLINE|LAST DATE|PAY|UPLOAD|REGISTER|REGISTRATION CLOSES|BRING)\b",
    re.IGNORECASE,
)
EXAM_CUES = re.compile(r"\b(EXAM|MIDTERM|MID-TERM|HALL TICKET)\b", re.IGNORECASE)

ROOM_OVERRIDE_VERBS = re.compile(
    r"\b(MOVED TO|SHIFTED TO|VENUE|CONDUCTED IN|CLASS IN|ROOM)\b", re.IGNORECASE
)


class RegexParser:
    @staticmethod
    def _resolve_date(clean_text: str, upper_text: str, ref_date: datetime) -> str | None:
        # ISO
        match = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", clean_text)
        if match:
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                return datetime(y, m, d).strftime("%Y-%m-%d")
            except ValueError:
                pass

        # D/M/Y or D/M
        match = re.search(r"\b(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?\b", clean_text)
        if match:
            d, m = int(match.group(1)), int(match.group(2))
            y_str = match.group(3)
            y = ref_date.year
            if y_str:
                y = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
            else:
                try:
                    dt = datetime(y, m, d)
                    if (ref_date.replace(tzinfo=None) - dt).days > 60:
                        y += 1
                except ValueError:
                    pass
            try:
                return datetime(y, m, d).strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Word dates: 12 Oct, 12th of October 2026, Oct 12
        months = [
            "JAN",
            "FEB",
            "MAR",
            "APR",
            "MAY",
            "JUN",
            "JUL",
            "AUG",
            "SEP",
            "OCT",
            "NOV",
            "DEC",
        ]

        # 12 Oct / 12th of October
        match = re.search(
            r"\b(\d{1,2})(?:ST|ND|RD|TH)?\s*(?:OF\s*)?([A-Z]{3,})\s*(\d{4})?\b", upper_text
        )
        if not match:
            # Oct 12
            match = re.search(r"\b([A-Z]{3,})\s+(\d{1,2})(?:ST|ND|RD|TH)?\s*(\d{4})?\b", upper_text)
            if match:
                m_str, d_str, y_str = match.groups()
            else:
                m_str, d_str, y_str = None, None, None
        else:
            d_str, m_str, y_str = match.groups()

        if d_str and m_str:
            m_idx = None
            for i, m_name in enumerate(months):
                if m_str.startswith(m_name):
                    m_idx = i + 1
                    break
            if m_idx:
                d = int(d_str)
                y = int(y_str) if y_str else ref_date.year
                if not y_str:
                    try:
                        dt = datetime(y, m_idx, d)
                        if (ref_date.replace(tzinfo=None) - dt).days > 60:
                            y += 1
                    except ValueError:
                        pass
                try:
                    return datetime(y, m_idx, d).strftime("%Y-%m-%d")
                except ValueError:
                    pass

        # Relatives
        if "DAY AFTER TOMORROW" in upper_text:
            return (ref_date + timedelta(days=2)).strftime("%Y-%m-%d")
        if "TOMORROW" in upper_text:
            return (ref_date + timedelta(days=1)).strftime("%Y-%m-%d")
        if "TODAY" in upper_text:
            return ref_date.strftime("%Y-%m-%d")

        # Weekdays
        weekdays = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        for i, wd in enumerate(weekdays):
            if re.search(rf"\b{wd}\b", upper_text) or re.search(rf"\b{wd[:3]}\b", upper_text):
                days_ahead = i - ref_date.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                if days_ahead == 0 and re.search(rf"\bNEXT {wd}\b", upper_text):
                    days_ahead += 7
                return (ref_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        return None

    @staticmethod
    def detect_course(upper_text: str) -> tuple[str | None, str | None]:
        for course_key, code in COURSE_CODES.items():
            if code and code in upper_text:
                return course_key, code

        for course_key, aliases in COURSES.items():
            for alias in aliases:
                # (?<![A-Z0-9])alias(?![A-Z])
                pattern = rf"(?<![A-Z0-9]){re.escape(alias)}(?![A-Z])"
                if re.search(pattern, upper_text):
                    return course_key, COURSE_CODES.get(course_key)
        return None, None

    @staticmethod
    def canonical_course(name: str | None, code: str | None) -> tuple[str | None, str | None]:
        if code:
            for course_key, course_code in COURSE_CODES.items():
                if code.upper() == course_code:
                    return course_key, course_code
        if name:
            upper_name = name.upper()
            for course_key, course_code in COURSE_CODES.items():
                if course_key == upper_name:
                    return course_key, course_code
            for course_key, aliases in COURSES.items():
                if any(upper_name == alias for alias in aliases):
                    return course_key, COURSE_CODES.get(course_key)
        return name, code

    @staticmethod
    def parse(text: str, message_date: datetime | None = None) -> ExtractedAcademicEvent | None:
        if not text or not text.strip():
            return None

        clean_text = text.strip().replace("–", "-").replace("—", "-")
        upper_text = clean_text.upper()

        detected_course, detected_code = RegexParser.detect_course(upper_text)

        room_matches = list(ROOM_PATTERN.finditer(clean_text))
        detected_room = None
        if room_matches:
            if len(room_matches) == 1:
                detected_room = room_matches[0].group(1).upper().replace(" ", "-")
            else:
                dest_keywords = re.compile(
                    r"\b(TO|IN|AT|NOW IN|CHANGED TO|MOVED TO)\b", re.IGNORECASE
                )
                source_keywords = re.compile(
                    r"\b(FROM|EARLIER|INSTEAD OF|PREVIOUSLY|WAS)\b", re.IGNORECASE
                )

                rooms_with_scores = []
                for m in room_matches:
                    score = 0
                    prefix = clean_text[max(0, m.start() - 20) : m.start()]
                    dest_match = list(dest_keywords.finditer(prefix))
                    src_match = list(source_keywords.finditer(prefix))

                    last_dest_idx = dest_match[-1].start() if dest_match else -1
                    last_src_idx = src_match[-1].start() if src_match else -1

                    if last_dest_idx > last_src_idx:
                        score = 1
                    elif last_src_idx > last_dest_idx:
                        score = -1

                    rooms_with_scores.append((score, m.group(1).upper().replace(" ", "-")))

                best_rooms = [r for s, r in rooms_with_scores if s > 0]
                if len(best_rooms) == 1:
                    detected_room = best_rooms[0]
                elif len(best_rooms) > 1:
                    detected_room = None
                else:
                    # no clear destination
                    detected_room = None

        period_match = PERIOD_PATTERN.search(clean_text)
        detected_period = period_match.group(1).upper() if period_match else None

        # Check for clock time range if detected_period is None or just a clock time
        time_range_match = re.search(
            r"\b(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)\b",
            clean_text,
            re.IGNORECASE,
        )
        if time_range_match:
            try:

                def parse_time(t_str):
                    t_str = t_str.strip().upper()
                    if "AM" in t_str or "PM" in t_str:
                        return datetime.strptime(t_str, "%I:%M %p").time()
                    return datetime.strptime(t_str, "%H:%M").time()

                t_start = parse_time(time_range_match.group(1))
                t_end = parse_time(time_range_match.group(2))

                # Period map
                period_map = {
                    1: (8, 10, 9, 0),
                    2: (9, 0, 9, 50),
                    3: (10, 0, 10, 50),
                    4: (10, 50, 11, 40),
                    5: (11, 50, 12, 40),
                    7: (13, 20, 14, 10),
                    8: (14, 20, 15, 10),
                    9: (15, 10, 16, 0),
                }

                start_p = None
                end_p = None

                start_mins = t_start.hour * 60 + t_start.minute
                end_mins = t_end.hour * 60 + t_end.minute

                for p, (sh, sm, eh, em) in period_map.items():
                    p_start_mins = sh * 60 + sm
                    p_end_mins = eh * 60 + em

                    if abs(start_mins - p_start_mins) <= 10:
                        start_p = p
                    if abs(end_mins - p_end_mins) <= 10:
                        end_p = p

                if start_p and end_p:
                    if start_p == end_p:
                        detected_period = f"P{start_p}"
                    else:
                        detected_period = f"P{start_p}-P{end_p}"
                else:
                    detected_period = time_range_match.group(0).upper()
            except ValueError:
                detected_period = time_range_match.group(0).upper()

        if message_date and message_date.tzinfo:
            ref_date = message_date.astimezone(IST)
        elif message_date:
            ref_date = message_date.replace(tzinfo=IST)
        else:
            ref_date = datetime.now(IST)

        resolved_date = RegexParser._resolve_date(clean_text, upper_text, ref_date)

        # a) HOLIDAY / CLASS_CANCELLED
        # "no class(es)", "not be held", "will not be conducted"
        # "cancelled", "canceled", "suspended"

        if re.search(
            r"\b(CANCELLED|CANCELED|SUSPENDED|NO CLASS|NO CLASSES|"
            r"NOT BE HELD|WILL NOT BE CONDUCTED)\b",
            clean_text,
            re.IGNORECASE,
        ):
            if detected_course:
                return ExtractedAcademicEvent(
                    intent="CLASS_CANCELLED",
                    course_name=detected_course,
                    course_code=detected_code,
                    room=None,
                    target_date=resolved_date or ref_date.strftime("%Y-%m-%d"),
                    period=detected_period,
                    summary=f"CANCELLED: {detected_course} class",
                    action_required=False,
                )

        if HOLIDAY_PATTERN.search(clean_text):
            return ExtractedAcademicEvent(
                intent="HOLIDAY",
                course_name=detected_course,
                course_code=detected_code,
                room=None,
                target_date=resolved_date or ref_date.strftime("%Y-%m-%d"),
                period=None,
                summary=f"University Holiday Notice: {clean_text[:100]}",
                action_required=False,
            )

        # b) ROOM_OVERRIDE strong
        strong_room_override_verbs = re.compile(
            r"\b(MOVED|SHIFTED|RELOCATED|CHANGED TO|CONDUCTED IN|HELD IN|HELD AT)\b", re.IGNORECASE
        )
        weak_room_override_verbs = re.compile(
            r"\b(VENUE|ROOM|WILL BE IN|CLASS IN)\b", re.IGNORECASE
        )
        class_words = re.compile(r"\b(CLASS|LECTURE|LAB|SESSION|PERIOD)\b", re.IGNORECASE)

        if detected_room and detected_course and strong_room_override_verbs.search(clean_text):
            summary_parts = [f"Room for {detected_course or 'Class'} updated to {detected_room}"]
            if detected_period:
                summary_parts.append(f"during {detected_period}")
            return ExtractedAcademicEvent(
                intent="ROOM_OVERRIDE",
                course_name=detected_course,
                course_code=detected_code,
                room=detected_room,
                target_date=resolved_date or ref_date.strftime("%Y-%m-%d"),
                period=detected_period,
                summary=" ".join(summary_parts),
                action_required=False,
            )

        # c) TASK or EXAM_DEADLINE
        from typing import Literal

        is_task = bool(TASK_ACTION_CUES.search(clean_text))
        is_exam = bool(EXAM_CUES.search(clean_text))
        if is_task or (is_exam and resolved_date):
            target_dt = resolved_date
            # EXAM_DEADLINE needs EXAM, MIDTERM or HALL TICKET plus a resolved date
            intent_type: Literal["EXAM_DEADLINE", "TASK"] = (
                "EXAM_DEADLINE" if (is_exam and resolved_date) else "TASK"
            )
            # Wait, "Last date to pay end exam fee is 26 Sep" is EXAM_DEADLINE.
            # Because it has EXAM and a resolved date.
            # If it has action cue and exam, it should be EXAM_DEADLINE? Yes.
            return ExtractedAcademicEvent(
                intent=intent_type,
                course_name=detected_course,
                course_code=detected_code,
                room=detected_room,
                target_date=target_dt,
                period=detected_period,
                summary=clean_text[:150],
                action_required=True,
            )

        # d) ROOM_OVERRIDE weak
        if (
            detected_room
            and detected_course
            and (
                weak_room_override_verbs.search(clean_text)
                or class_words.search(clean_text)
                or detected_period
            )
        ):
            summary_parts = [f"Room for {detected_course or 'Class'} updated to {detected_room}"]
            if detected_period:
                summary_parts.append(f"during {detected_period}")
            return ExtractedAcademicEvent(
                intent="ROOM_OVERRIDE",
                course_name=detected_course,
                course_code=detected_code,
                room=detected_room,
                target_date=resolved_date or ref_date.strftime("%Y-%m-%d"),
                period=detected_period,
                summary=" ".join(summary_parts),
                action_required=False,
            )

        return None
