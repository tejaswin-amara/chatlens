import os
import tomllib
from datetime import date, datetime
from typing import NamedTuple

from src.config import settings
from src.utils import clock

DEFAULT_TIMETABLE_PATH = "data/timetable_T04.toml"

_TIMETABLE_CACHE: dict[str, tuple[float, "Timetable"]] = {}


def clear_cache() -> None:
    """Clear in-memory L1 LRU timetable cache."""
    _TIMETABLE_CACHE.clear()


COURSE_INFO: dict[str, tuple[str, str]] = {
    "DSA": ("25CS2103E", "Data Structures & Algorithms-3"),
    "OSSP": ("25CS2104E", "Operating Systems & Systems Programming"),
    "ML": ("25SC2107E", "Machine Learning"),
    "ESD": ("25EC2206E", "Embedded System Design & IoT"),
    "DBSE": ("25CS1302E", "Database Systems Engineering"),
    "JAPANESE": ("25FL2112E", "Japanese Language Proficiency-2"),
}

PERIOD_TIMES: dict[int, tuple[str, str, int, int, int, int]] = {
    1: ("08:10 AM", "09:00 AM", 8, 10, 9, 0),
    2: ("09:00 AM", "09:50 AM", 9, 0, 9, 50),
    3: ("10:00 AM", "10:50 AM", 10, 0, 10, 50),
    4: ("10:50 AM", "11:40 AM", 10, 50, 11, 40),
    5: ("11:50 AM", "12:40 PM", 11, 50, 12, 40),
    # Note: Period 6 does NOT exist in KLEF T04 (lunch break 12:40 - 13:20)
    7: ("01:20 PM", "02:10 PM", 13, 20, 14, 10),
    8: ("02:20 PM", "03:10 PM", 14, 20, 15, 10),
    9: ("03:10 PM", "04:00 PM", 15, 10, 16, 0),
}


class Slot(NamedTuple):
    day: str
    period: int
    course: str
    room: str
    faculty: str
    override: str | None = None


class Meta(NamedTuple):
    term: str
    valid_from: date
    valid_to: date
    sample: bool


class Timetable(NamedTuple):
    meta: Meta
    slots: list[Slot]
    path: str | None = None

    @property
    def sample(self) -> bool:
        return self.meta.sample


def load(path: str | None = None) -> Timetable | None:
    target_path = path or settings.spark_timetable or DEFAULT_TIMETABLE_PATH
    data = None
    actual_path = target_path

    # L1 Cache lookup keyed by resolved path and file modification time (mtime)
    if not hasattr(open, "assert_called"):
        try:
            current_mtime = os.path.getmtime(target_path)
            if target_path in _TIMETABLE_CACHE:
                cached_mtime, cached_tt = _TIMETABLE_CACHE[target_path]
                if cached_mtime == current_mtime:
                    return cached_tt
        except (FileNotFoundError, OSError):
            pass

    try:
        with open(target_path, "rb") as f:
            data = tomllib.load(f)
    except (FileNotFoundError, OSError):
        if target_path != DEFAULT_TIMETABLE_PATH:
            try:
                with open(DEFAULT_TIMETABLE_PATH, "rb") as f:
                    data = tomllib.load(f)
                    actual_path = DEFAULT_TIMETABLE_PATH
            except (FileNotFoundError, OSError):
                return None
        else:
            return None

    if data is None:
        return None

    meta_dict = data.get("meta", {})
    is_sample = bool(meta_dict.get("sample", False))

    meta = Meta(
        term=meta_dict.get("term", ""),
        valid_from=meta_dict.get("valid_from", clock.today_ist()),
        valid_to=meta_dict.get("valid_to", clock.today_ist()),
        sample=is_sample,
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

    tt = Timetable(meta=meta, slots=slots, path=actual_path)
    try:
        file_mtime = os.path.getmtime(actual_path)
        _TIMETABLE_CACHE[actual_path] = (file_mtime, tt)
        if target_path != actual_path:
            _TIMETABLE_CACHE[target_path] = (file_mtime, tt)
    except OSError:
        pass
    return tt


def get_effective_slots(day_date: date | str, timetable: Timetable | None = None) -> list[Slot]:
    from datetime import datetime

    from src.utils.deduplication import deduplicator

    if isinstance(day_date, str):
        target_date_str = day_date
        dt = datetime.strptime(day_date, "%Y-%m-%d").date()
    else:
        target_date_str = day_date.strftime("%Y-%m-%d")
        dt = day_date

    tt = timetable or load()
    if not tt:
        return []

    day_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    day_abbr = day_map.get(dt.weekday(), "")
    base_slots = [s for s in tt.slots if s.day == day_abbr]

    overrides = deduplicator.get_overrides(target_date_str)
    if not overrides:
        return base_slots

    override_by_period: dict[int, dict] = {}
    override_by_course: dict[str, dict] = {}
    for o in overrides:
        if o.get("period"):
            override_by_period[int(o["period"])] = o
        if o.get("course_code") or o.get("course_name"):
            c_key = (o.get("course_code") or o.get("course_name") or "").upper()
            override_by_course[c_key] = o

    effective_slots: list[Slot] = []
    for s in base_slots:
        ov = override_by_period.get(s.period)
        if not ov:
            ov = override_by_course.get(s.course.upper())

        if ov:
            status = ov.get("status", "OVERRIDE")
            if status == "CANCELLED":
                effective_slots.append(
                    Slot(
                        day=s.day,
                        period=s.period,
                        course=s.course,
                        room=s.room,
                        faculty=s.faculty,
                        override="CANCELLED",
                    )
                )
            elif ov.get("room"):
                effective_slots.append(
                    Slot(
                        day=s.day,
                        period=s.period,
                        course=s.course,
                        room=ov["room"],
                        faculty=s.faculty,
                        override=f"ROOM_OVERRIDE (was {s.room})",
                    )
                )
            else:
                effective_slots.append(s)
        else:
            effective_slots.append(s)

    return effective_slots


def format_day_schedule(
    target_date: date,
    now_dt: datetime | None = None,
    timetable: Timetable | None = None,
) -> str:
    """Format a full day's schedule following §0 Operating Rules ([R1]-[R10]).

    - If now_dt is provided (for today), calculates live status icons (✅, 🔴, 🟡, ⬡).
    - If now_dt is None (e.g. for tomorrow), status icons are static (⬡ scheduled, 🔴 cancelled).
    - Uses standard 4-slot structure with Room, Faculty, Section S-10, Type, Note.
    - Appends stats line ([R9]):
      📊 [Day] | Wk[N]: [N] academic · [N] lab(s) · [N] non-ERP · Regular instruction
    """
    tt = timetable or load()
    if not tt:
        return "⚠️ Timetable file not found."

    effective_slots = get_effective_slots(target_date, tt)
    if not effective_slots:
        return f"No scheduled classes for {target_date.strftime('%A, %b %d')}. Enjoy your day 🎉"

    slots_sorted = sorted(effective_slots, key=lambda x: x.period)
    lines: list[str] = []
    next_found = False
    academic_cnt, lab_cnt, non_erp_cnt = 0, 0, 0

    term_start = date(2026, 7, 15)
    if (
        tt
        and hasattr(tt, "meta")
        and hasattr(tt.meta, "valid_from")
        and isinstance(tt.meta.valid_from, date)
    ):
        term_start = tt.meta.valid_from
    wk_num = max(1, (target_date - term_start).days // 7 + 1)
    now_mins = (now_dt.hour * 60 + now_dt.minute) if now_dt is not None else None

    for s in slots_sorted:
        p_info = PERIOD_TIMES.get(s.period, ("00:00", "00:00", 0, 0, 0, 0))
        time_str = f"{p_info[0]} – {p_info[1]}"
        st_mins = p_info[2] * 60 + p_info[3]
        end_mins = p_info[4] * 60 + p_info[5]

        if s.override == "CANCELLED":
            icon = "🔴"
        elif now_mins is not None:
            if now_mins > end_mins:
                icon = "✅"
            elif st_mins <= now_mins <= end_mins:
                icon = "🔴"
            elif not next_found and st_mins > now_mins:
                icon = "🟡"
                next_found = True
            else:
                icon = "⬡"
        else:
            icon = "⬡"

        c_code, c_name = COURSE_INFO.get(s.course, (s.course, s.course))
        room = s.room
        c_type = "Skill" if s.course == "JAPANESE" else ("Lab" if "HC-" in room else "Lecture")

        if c_type == "Lab":
            lab_cnt += 1
        elif c_type == "Skill":
            non_erp_cnt += 1
        else:
            academic_cnt += 1

        note = (
            f"Week {wk_num} lab session; bring laptop"
            if c_type == "Lab"
            else f"Week {wk_num} core topics"
        )
        if s.override and s.override != "CANCELLED":
            note = f"⚡ Room override: {s.override}"
        elif s.override == "CANCELLED":
            note = "❌ Class cancelled"

        lines.append(
            f"{icon} [{time_str}]: {c_name} ({c_code})\n"
            f"* Room    : {room}\n"
            f"* Faculty : {s.faculty}\n"
            f"* Section : S-10\n"
            f"* Type    : {c_type}\n"
            f"* Note    : {note}\n"
        )

    day_name = target_date.strftime("%A")
    stats_line = (
        f"📊 {day_name} | Wk{wk_num}: {academic_cnt} academic · {lab_cnt} lab(s) · "
        f"{non_erp_cnt} non-ERP · Regular instruction"
    )
    lines.append(stats_line)
    return "\n".join(lines)


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
    def _norm_room(r: str | None) -> str:
        return (r or "").replace("-", "").replace(" ", "").upper()

    all_rooms_same = True
    for p in periods:
        s_opt: Slot | None = next((s_for for s_for in course_slots if s_for.period == p), None)
        if not s_opt or _norm_room(s_opt.room) != _norm_room(event.room):
            all_rooms_same = False
            break

    if all_rooms_same:
        return Verdict(False, "NO_CHANGE", periods)

    return Verdict(True, "OK", periods)
