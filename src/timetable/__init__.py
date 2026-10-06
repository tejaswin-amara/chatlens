import tomllib
from datetime import date
from typing import NamedTuple

from src.config import settings
from src.utils import clock


class Slot(NamedTuple):
    day: str
    period: int
    course: str
    room: str
    faculty: str


class Meta(NamedTuple):
    term: str
    valid_from: date
    valid_to: date
    sample: bool


class Timetable(NamedTuple):
    meta: Meta
    slots: list[Slot]


def load(path: str | None = None) -> Timetable | None:
    path = path or settings.spark_timetable
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return None

    meta_dict = data.get("meta", {})
    if meta_dict.get("sample", False):
        return None

    meta = Meta(
        term=meta_dict.get("term", ""),
        valid_from=meta_dict.get("valid_from", clock.today_ist()),
        valid_to=meta_dict.get("valid_to", clock.today_ist()),
        sample=meta_dict.get("sample", False),
    )

    slots = []
    for slot in data.get("slot", []):
        slots.append(
            Slot(
                day=slot.get("day", ""),
                period=slot.get("period", 0),
                course=slot.get("course", ""),
                room=slot.get("room", ""),
                faculty=slot.get("faculty", ""),
            )
        )

    return Timetable(meta=meta, slots=slots)


def parse_periods(text: str) -> list[int]:
    import re

    if not text:
        return []

    # Check for clock time range
    time_range_match = re.search(
        r"\b(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)\b", text, re.IGNORECASE
    )
    if time_range_match:
        try:
            from datetime import datetime

            t_str = time_range_match.group(1).strip().upper()
            if "AM" in t_str or "PM" in t_str:
                t_start = datetime.strptime(t_str, "%I:%M %p").time()
            else:
                t_start = datetime.strptime(t_str, "%H:%M").time()

            start_mins = t_start.hour * 60 + t_start.minute
            period_map = {
                1: 8 * 60 + 10,
                2: 9 * 60 + 0,
                3: 10 * 60 + 0,
                4: 10 * 60 + 50,
                5: 11 * 60 + 50,
                7: 13 * 60 + 20,
                8: 14 * 60 + 20,
                9: 15 * 60 + 10,
            }

            for p, p_mins in period_map.items():
                if abs(start_mins - p_mins) <= 10:
                    return [p]
        except ValueError:
            pass

    periods = set()
    m = re.search(r"P(\d+)", text, re.IGNORECASE)
    m_end = re.search(r"-P(\d+)", text, re.IGNORECASE)
    if m:
        p_start = int(m.group(1))
        p_end = int(m_end.group(1)) if m_end else p_start
        for p in range(p_start, p_end + 1):
            if p != 6:  # No P6
                periods.add(p)
    elif "PERIOD" in text.upper():
        m = re.search(r"PERIOD\s*[-]?\s*(\d+)", text, re.IGNORECASE)
        if m:
            p = int(m.group(1))
            if p != 6:
                periods.add(p)

    return sorted(list(periods))


class Verdict(NamedTuple):
    ok: bool
    reason: str
    period: list[int]


def validate(event, timetable: Timetable | None) -> Verdict:
    if event.intent not in ("ROOM_OVERRIDE", "CLASS_CANCELLED"):
        return Verdict(True, "NOT_APPLICABLE", [])

    if not timetable or timetable.meta.sample:
        return Verdict(True, "NO_TIMETABLE", parse_periods(event.period or ""))

    if not event.target_date:
        return Verdict(False, "INVALID_DATE", parse_periods(event.period or ""))

    from datetime import datetime

    try:
        dt = datetime.strptime(event.target_date, "%Y-%m-%d").date()
    except Exception:
        return Verdict(False, "INVALID_DATE", parse_periods(event.period or ""))

    if dt < timetable.meta.valid_from or dt > timetable.meta.valid_to:
        return Verdict(False, "OUTSIDE_TERM", parse_periods(event.period or ""))

    day_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    event_day = day_map.get(dt.weekday())

    course_slots = [
        s for s in timetable.slots if s.day == event_day and s.course == event.course_name
    ]

    periods = parse_periods(event.period or "")
    if not periods:
        if not course_slots:
            return Verdict(False, "NO_SLOT", [])
        # Find contiguous blocks
        course_slots.sort(key=lambda s: s.period)
        blocks = []
        current_block: list[int] = []
        for s in course_slots:
            if (
                not current_block
                or s.period == current_block[-1] + 1
                or (current_block[-1] == 5 and s.period == 7)
            ):
                current_block.append(s.period)
            else:
                blocks.append(current_block)
                current_block = [s.period]
        if current_block:
            blocks.append(current_block)

        if len(blocks) > 1:
            return Verdict(False, "AMBIGUOUS_PERIOD", [])

        # Exactly one block
        periods = blocks[0]
        return Verdict(True, "OK", periods)

    # Event provides period(s)
    # Check if all provided periods exist for this course on this day
    slot_periods = {s.period for s in course_slots}
    for p in periods:
        if p not in slot_periods:
            return Verdict(False, "PERIOD_MISMATCH", periods)

    # Check if the room is already the same
    # But wait, validate only returns Verdict, it doesn't know the intended room unless we \
    # check it here
    # P3 says: "NO_CHANGE"
    # "validate(event, timetable) -> Verdict(ok, reason, period) for ROOM_OVERRIDE: "
    # "OUTSIDE_TERM, NO_SLOT, PERIOD_MISMATCH, AMBIGUOUS_PERIOD, NO_CHANGE, OK"
    all_rooms_same = True
    for p in periods:
        s_opt: Slot | None = next((s_for for s_for in course_slots if s_for.period == p), None)
        if not s_opt or s_opt.room.upper().replace(" ", "-") != (event.room or "").upper().replace(
            " ", "-"
        ):
            all_rooms_same = False
            break

    if all_rooms_same:
        return Verdict(False, "NO_CHANGE", periods)

    return Verdict(True, "OK", periods)
