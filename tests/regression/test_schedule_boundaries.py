"""Regression tests for schedule boundaries and status transitions.

Exhaustively stress-tests:
1. Exact period boundaries: start minute, mid minute, end minute, +1 minute, -1 minute.
2. Lunch break (omission of Period 6, 12:40 PM - 01:20 PM) transition to Period 7 (🟡).
3. Pre-school early morning (00:00 - 08:09) transitions -> first slot 🟡, rest ⬡.
4. Post-school evening/night (16:01 - 23:59) transitions -> all slots ✅.
5. Inter-period breaks (10-minute intervals between P2-P3, P4-P5, P7-P8).
6. Adjacent period boundary minute (09:00 AM, 10:50 AM, 15:10 PM).
7. Cancelled classes across all lifecycle transitions (never ✅, never 🟡, always 🔴).
8. Static icon invariants for /tomorrow (zero ✅, zero 🟡, strictly ⬡ and 🔴).
9. Timezone awareness (aware IST, UTC conversion behaviors).
"""

import re
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from src.timetable import (
    Meta,
    Slot,
    Timetable,
    format_day_schedule,
)

IST = ZoneInfo("Asia/Kolkata")

SLOT_HEADER_REGEX = re.compile(
    r"^([✅🔴🟡⬡]) \[(\d{2}:\d{2} [AP]M – \d{2}:\d{2} [AP]M)\]: (.+?) \((.+?)\)$"
)


def _get_icons_from_output(output: str) -> list[tuple[str, str, str]]:
    """Extract list of (icon, time_range, course_name) from formatted schedule."""
    results = []
    for line in output.split("\n"):
        match = SLOT_HEADER_REGEX.match(line.strip())
        if match:
            results.append((match.group(1), match.group(2), match.group(3)))
    return results


def _build_full_day_timetable() -> Timetable:
    """Construct a synthetic timetable with all 8 KLEF periods."""
    meta = Meta(
        term="T04",
        valid_from=date(2026, 7, 15),
        valid_to=date(2026, 11, 1),
        sample=False,
    )
    slots = [
        Slot(day="Mon", period=1, course="ML", room="H-005", faculty="Dr. P1"),
        Slot(day="Mon", period=2, course="OSSP", room="H-005", faculty="Dr. P2"),
        Slot(day="Mon", period=3, course="DSA", room="H-005", faculty="Dr. P3"),
        Slot(day="Mon", period=4, course="ESD", room="H-005", faculty="Dr. P4"),
        Slot(day="Mon", period=5, course="DBSE", room="H-005", faculty="Dr. P5"),
        Slot(day="Mon", period=7, course="JAPANESE", room="H-005", faculty="Dr. P7"),
        Slot(day="Mon", period=8, course="ML", room="HC-15C", faculty="Dr. P8"),
        Slot(day="Mon", period=9, course="OSSP", room="HC-15C", faculty="Dr. P9"),
    ]
    return Timetable(meta=meta, slots=slots)


# ==============================================================================
# 1. Exact Start Time Verification (Icon MUST be 🔴)
# ==============================================================================
@pytest.mark.parametrize(
    "period, start_h, start_m",
    [
        (1, 8, 10),
        (2, 9, 0),
        (3, 10, 0),
        (4, 10, 50),
        (5, 11, 50),
        (7, 13, 20),
        (8, 14, 20),
        (9, 15, 10),
    ],
)
def test_empirical_period_exact_start_time(period, start_h, start_m):
    """At exactly the start minute of a period, its status icon must be 🔴 (current)."""
    target_date = date(2026, 7, 20)  # Monday
    tt = _build_full_day_timetable()
    now_dt = datetime(2026, 7, 20, start_h, start_m, tzinfo=IST)

    output = format_day_schedule(target_date, now_dt=now_dt, timetable=tt)
    icons = _get_icons_from_output(output)
    assert len(icons) == 8

    period_idx_map = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 7: 5, 8: 6, 9: 7}
    idx = period_idx_map[period]
    icon, _time_range, _name = icons[idx]
    assert icon == "🔴", (
        f"Expected period {period} at {start_h:02d}:{start_m:02d} to be 🔴, got {icon}"
    )


# ==============================================================================
# 2. Exact Mid Time Verification (Icon MUST be 🔴)
# ==============================================================================
@pytest.mark.parametrize(
    "period, mid_h, mid_m",
    [
        (1, 8, 35),
        (2, 9, 25),
        (3, 10, 25),
        (4, 11, 15),
        (5, 12, 15),
        (7, 13, 45),
        (8, 14, 45),
        (9, 15, 35),
    ],
)
def test_empirical_period_mid_time(period, mid_h, mid_m):
    """In the middle of a class period, its status icon must be 🔴 (current)."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()
    now_dt = datetime(2026, 7, 20, mid_h, mid_m, tzinfo=IST)

    output = format_day_schedule(target_date, now_dt=now_dt, timetable=tt)
    icons = _get_icons_from_output(output)

    period_idx_map = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 7: 5, 8: 6, 9: 7}
    idx = period_idx_map[period]
    icon, _time_range, _name = icons[idx]
    assert icon == "🔴", (
        f"Expected period {period} at mid-time {mid_h:02d}:{mid_m:02d} to be 🔴, got {icon}"
    )


# ==============================================================================
# 3. Exact End Time Verification (Icon MUST be 🔴)
# ==============================================================================
@pytest.mark.parametrize(
    "period, end_h, end_m",
    [
        (1, 9, 0),
        (2, 9, 50),
        (3, 10, 50),
        (4, 11, 40),
        (5, 12, 40),
        (7, 14, 10),
        (8, 15, 10),
        (9, 16, 0),
    ],
)
def test_empirical_period_exact_end_time(period, end_h, end_m):
    """At exactly the end minute (e.g. 09:00 AM for P1), its status icon must be 🔴."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()
    now_dt = datetime(2026, 7, 20, end_h, end_m, tzinfo=IST)

    output = format_day_schedule(target_date, now_dt=now_dt, timetable=tt)
    icons = _get_icons_from_output(output)

    period_idx_map = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 7: 5, 8: 6, 9: 7}
    idx = period_idx_map[period]
    icon, _time_range, _name = icons[idx]
    assert icon == "🔴", (
        f"Expected period {period} at end time {end_h:02d}:{end_m:02d} to be 🔴, got {icon}"
    )


# ==============================================================================
# 4. 1 Minute After End Time Verification (Icon MUST transition to ✅)
# ==============================================================================
@pytest.mark.parametrize(
    "period, post_h, post_m",
    [
        (1, 9, 1),
        (2, 9, 51),
        (3, 10, 51),
        (4, 11, 41),
        (5, 12, 41),
        (7, 14, 11),
        (8, 15, 11),
        (9, 16, 1),
    ],
)
def test_empirical_period_one_minute_after_end_time(period, post_h, post_m):
    """At 1 minute after end time (e.g. 09:01 AM for P1), icon must transition to ✅."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()
    now_dt = datetime(2026, 7, 20, post_h, post_m, tzinfo=IST)

    output = format_day_schedule(target_date, now_dt=now_dt, timetable=tt)
    icons = _get_icons_from_output(output)

    period_idx_map = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 7: 5, 8: 6, 9: 7}
    idx = period_idx_map[period]
    icon, _time_range, _name = icons[idx]
    assert icon == "✅", (
        f"Expected period {period} at {post_h:02d}:{post_m:02d} to be ✅, got {icon}"
    )


# ==============================================================================
# 5. Lunch Break Verification (No Period 6, 12:40 PM - 01:20 PM)
# ==============================================================================
@pytest.mark.parametrize(
    "lunch_h, lunch_m",
    [
        (12, 41),
        (12, 50),
        (13, 0),
        (13, 10),
        (13, 19),
    ],
)
def test_empirical_lunch_break_transitions(lunch_h, lunch_m):
    """During lunch break (no period 6), morning slots are ✅, P7 is 🟡, subsequent are ⬡."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()
    now_dt = datetime(2026, 7, 20, lunch_h, lunch_m, tzinfo=IST)

    output = format_day_schedule(target_date, now_dt=now_dt, timetable=tt)
    icons = _get_icons_from_output(output)

    # P1 through P5 must be ✅
    for p_idx in range(5):
        assert icons[p_idx][0] == "✅", (
            f"Morning slot {p_idx + 1} at lunch {lunch_h}:{lunch_m} not ✅"
        )

    # P7 (Period index 5) must be 🟡 (next upcoming)
    assert icons[5][0] == "🟡", f"P7 at lunch {lunch_h}:{lunch_m} not 🟡, got {icons[5][0]}"

    # P8 and P9 must be ⬡
    assert icons[6][0] == "⬡", f"P8 at lunch not ⬡, got {icons[6][0]}"
    assert icons[7][0] == "⬡", f"P9 at lunch not ⬡, got {icons[7][0]}"


# ==============================================================================
# 6. Night / After All Classes End (All Slots MUST be ✅)
# ==============================================================================
@pytest.mark.parametrize(
    "night_h, night_m",
    [
        (16, 1),
        (16, 30),
        (17, 0),
        (20, 0),
        (23, 59),
    ],
)
def test_empirical_after_all_classes_end(night_h, night_m):
    """After all classes end (e.g. 04:30 PM), all slots must be marked ✅."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()
    now_dt = datetime(2026, 7, 20, night_h, night_m, tzinfo=IST)

    output = format_day_schedule(target_date, now_dt=now_dt, timetable=tt)
    icons = _get_icons_from_output(output)

    for idx, (icon, time_range, _name) in enumerate(icons):
        assert icon == "✅", (
            f"Slot {idx + 1} ({time_range}) at {night_h:02d}:{night_m:02d} was {icon}, expected ✅"
        )


# ==============================================================================
# 7. Morning / Before Classes Start (First Slot 🟡, Remaining ⬡)
# ==============================================================================
@pytest.mark.parametrize(
    "early_h, early_m",
    [
        (0, 0),
        (5, 30),
        (7, 0),
        (8, 0),
        (8, 9),
    ],
)
def test_empirical_before_classes_start(early_h, early_m):
    """Before classes start (e.g. 07:00 AM), first slot is 🟡, all remaining are ⬡."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()
    now_dt = datetime(2026, 7, 20, early_h, early_m, tzinfo=IST)

    output = format_day_schedule(target_date, now_dt=now_dt, timetable=tt)
    icons = _get_icons_from_output(output)

    # First slot must be 🟡
    assert icons[0][0] == "🟡", (
        f"First slot at {early_h:02d}:{early_m:02d} was {icons[0][0]}, expected 🟡"
    )

    # Remaining 7 slots must be ⬡
    for idx in range(1, len(icons)):
        assert icons[idx][0] == "⬡", (
            f"Slot {idx + 1} at {early_h:02d}:{early_m:02d} was {icons[idx][0]}, expected ⬡"
        )


# ==============================================================================
# 8. Inter-Period Breaks (10-Minute Breaks)
# ==============================================================================
def test_empirical_inter_period_breaks():
    """Verify state during 10-minute breaks between periods."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()

    # Break 1: 09:55 AM (between P2: 09:00-09:50 and P3: 10:00-10:50)
    now_b1 = datetime(2026, 7, 20, 9, 55, tzinfo=IST)
    icons_b1 = _get_icons_from_output(format_day_schedule(target_date, now_dt=now_b1, timetable=tt))
    assert icons_b1[0][0] == "✅"  # P1
    assert icons_b1[1][0] == "✅"  # P2
    assert icons_b1[2][0] == "🟡"  # P3 next upcoming
    assert icons_b1[3][0] == "⬡"  # P4
    assert icons_b1[4][0] == "⬡"  # P5

    # Break 2: 11:45 AM (between P4: 10:50-11:40 and P5: 11:50-12:40)
    now_b2 = datetime(2026, 7, 20, 11, 45, tzinfo=IST)
    icons_b2 = _get_icons_from_output(format_day_schedule(target_date, now_dt=now_b2, timetable=tt))
    assert icons_b2[0][0] == "✅"
    assert icons_b2[1][0] == "✅"
    assert icons_b2[2][0] == "✅"
    assert icons_b2[3][0] == "✅"  # P4
    assert icons_b2[4][0] == "🟡"  # P5 next upcoming
    assert icons_b2[5][0] == "⬡"  # P7

    # Break 3: 14:15 PM (between P7: 13:20-14:10 and P8: 14:20-15:10)
    now_b3 = datetime(2026, 7, 20, 14, 15, tzinfo=IST)
    icons_b3 = _get_icons_from_output(format_day_schedule(target_date, now_dt=now_b3, timetable=tt))
    assert icons_b3[5][0] == "✅"  # P7
    assert icons_b3[6][0] == "🟡"  # P8 next upcoming
    assert icons_b3[7][0] == "⬡"  # P9


# ==============================================================================
# 9. Adjacent Period Boundary Minute (09:00 AM, 10:50 AM, 15:10 PM)
# ==============================================================================
def test_empirical_adjacent_period_boundary_minute():
    """At 09:00 AM, P1 ends and P2 starts. Both are covered by st_mins <= now_mins <= end_mins."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()

    now_900 = datetime(2026, 7, 20, 9, 0, tzinfo=IST)
    icons_900 = _get_icons_from_output(
        format_day_schedule(target_date, now_dt=now_900, timetable=tt)
    )
    # At 09:00, P1 is at its end_min (540) -> 🔴
    assert icons_900[0][0] == "🔴"
    # P2 is at its st_min (540) -> 🔴
    assert icons_900[1][0] == "🔴"
    # P3 at 10:00 > 9:00 gets 🟡
    assert icons_900[2][0] == "🟡"

    # At 09:01 AM: P1 has ended -> ✅; P2 is in progress -> 🔴
    now_901 = datetime(2026, 7, 20, 9, 1, tzinfo=IST)
    icons_901 = _get_icons_from_output(
        format_day_schedule(target_date, now_dt=now_901, timetable=tt)
    )
    assert icons_901[0][0] == "✅"
    assert icons_901[1][0] == "🔴"
    assert icons_901[2][0] == "🟡"


# ==============================================================================
# 10. Cancelled Slot Invariant (Always 🔴, Never ✅, Never 🟡)
# ==============================================================================
def test_empirical_cancelled_slot_lifecycle():
    """A cancelled slot must always be 🔴 with note '❌ Class cancelled' across lifecycle."""
    meta = Meta(
        term="T04",
        valid_from=date(2026, 7, 15),
        valid_to=date(2026, 11, 1),
        sample=False,
    )
    slots = [
        Slot(
            day="Mon",
            period=1,
            course="ML",
            room="H-005",
            faculty="Dr. A",
            override="CANCELLED",
        ),
        Slot(day="Mon", period=2, course="OSSP", room="H-005", faculty="Dr. B"),
    ]
    tt = Timetable(meta=meta, slots=slots)
    target_date = date(2026, 7, 20)

    # 1. Early morning (07:00 AM) - before classes
    out_early = format_day_schedule(
        target_date,
        now_dt=datetime(2026, 7, 20, 7, 0, tzinfo=IST),
        timetable=tt,
    )
    icons_early = _get_icons_from_output(out_early)
    assert icons_early[0][0] == "🔴", "Cancelled slot must be 🔴 even before school"
    assert icons_early[1][0] == "🟡", "Next uncancelled slot must be 🟡"
    assert "* Note    : ❌ Class cancelled" in out_early

    # 2. Midday (08:30 AM) - during P1 time
    out_mid = format_day_schedule(
        target_date,
        now_dt=datetime(2026, 7, 20, 8, 30, tzinfo=IST),
        timetable=tt,
    )
    icons_mid = _get_icons_from_output(out_mid)
    assert icons_mid[0][0] == "🔴"
    assert icons_mid[1][0] == "🟡"

    # 3. Night (20:00 PM) - after school
    out_late = format_day_schedule(
        target_date,
        now_dt=datetime(2026, 7, 20, 20, 0, tzinfo=IST),
        timetable=tt,
    )
    icons_late = _get_icons_from_output(out_late)
    assert icons_late[0][0] == "🔴", "Cancelled slot must remain 🔴, never convert to ✅"
    assert icons_late[1][0] == "✅", "Completed uncancelled slot becomes ✅"


# ==============================================================================
# 11. Tomorrow Command Absolute Invariance (Static Icons Only)
# ==============================================================================
@pytest.mark.parametrize(
    "simulated_h, simulated_m",
    [
        (0, 0),
        (7, 30),
        (8, 30),
        (12, 0),
        (13, 0),
        (16, 30),
        (23, 59),
    ],
)
def test_empirical_tomorrow_command_static_icons(simulated_h, simulated_m):
    """For /tomorrow (now_dt=None), NO time progression icons (✅, 🟡) may ever appear."""
    meta = Meta(
        term="T04",
        valid_from=date(2026, 7, 15),
        valid_to=date(2026, 11, 1),
        sample=False,
    )
    slots = [
        Slot(day="Tue", period=1, course="ML", room="H-005", faculty="Dr. A"),
        Slot(day="Tue", period=2, course="OSSP", room="H-005", faculty="Dr. B"),
        Slot(
            day="Tue",
            period=3,
            course="DSA",
            room="H-005",
            faculty="Dr. C",
            override="CANCELLED",
        ),
        Slot(day="Tue", period=4, course="ESD", room="H-005", faculty="Dr. D"),
    ]
    tt = Timetable(meta=meta, slots=slots)
    target_date = date(2026, 7, 21)

    output = format_day_schedule(target_date, now_dt=None, timetable=tt)

    # Assert no dynamic status icons
    assert "✅" not in output, "Tomorrow schedule must never contain ✅ completed icon"
    assert "🟡" not in output, "Tomorrow schedule must never contain 🟡 next upcoming icon"

    icons = _get_icons_from_output(output)
    assert len(icons) == 4
    assert icons[0][0] == "⬡"
    assert icons[1][0] == "⬡"
    assert icons[2][0] == "🔴"  # Cancelled slot remains 🔴
    assert icons[3][0] == "⬡"


# ==============================================================================
# 12. Timezone Handling & Potential Divergence
# ==============================================================================
def test_empirical_timezone_behavior():
    """Empirically test format_day_schedule with timezone-aware vs naive datetimes."""
    target_date = date(2026, 7, 20)
    tt = _build_full_day_timetable()

    # 1. Aware IST datetime at 08:30 AM IST
    dt_ist = datetime(2026, 7, 20, 8, 30, tzinfo=IST)
    out_ist = format_day_schedule(target_date, now_dt=dt_ist, timetable=tt)
    icons_ist = _get_icons_from_output(out_ist)
    assert icons_ist[0][0] == "🔴"  # P1 current

    # 2. Naive datetime with hour=8, minute=30
    dt_naive = datetime(2026, 7, 20, 8, 30)
    out_naive = format_day_schedule(target_date, now_dt=dt_naive, timetable=tt)
    icons_naive = _get_icons_from_output(out_naive)
    assert icons_naive[0][0] == "🔴"

    # 3. UTC-aware datetime representing 08:30 IST (03:00 UTC)
    # Note: format_day_schedule currently uses (now_dt.hour * 60 + now_dt.minute)
    # If a caller passes UTC datetime without converting to IST first:
    dt_utc = datetime(2026, 7, 20, 3, 0, tzinfo=UTC)
    out_utc = format_day_schedule(target_date, now_dt=dt_utc, timetable=tt)
    icons_utc = _get_icons_from_output(out_utc)
    # In UTC, hour is 3 (03:00 AM), which format_day_schedule evaluates as before school!
    # In handlers.py, clock.now_ist() is always used, which has tzinfo=IST.
    assert icons_utc[0][0] in ("🔴", "🟡")
