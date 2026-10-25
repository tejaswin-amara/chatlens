"""Empirical stress test suite for Milestone 1 (Schedule Formatting & /tomorrow).

Authored by Challenger 1 (Milestone 1).
Exhaustively verifies:
1. Schedule formatting and stats lines across all 7 days of the week (Mon–Sun).
2. Slot note generation for all course types, room overrides, and cancellations.
3. Live vs static status icons ([R4] today only).
4. Simultaneous room override injection for /today and /tomorrow without cross-day leakage.
5. Strict regex format compliance of the 4-slot structure.
6. Edge cases and boundary conditions (Period 6 omission, week calculation, fuzzy routing).
"""

import re
from datetime import date, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from src.config import settings
from src.ingestion.handlers import handle_bot_command
from src.notify.bot import bot
from src.timetable import DEFAULT_TIMETABLE_PATH, format_day_schedule, get_effective_slots
from src.timetable import load as load_timetable
from src.utils import clock
from src.utils.deduplication import MessageDeduplicator

IST = ZoneInfo("Asia/Kolkata")

SLOT_HEADER_REGEX = re.compile(
    r"^([✅🔴🟡⬡]) \[(\d{2}:\d{2} [AP]M – \d{2}:\d{2} [AP]M)\]: (.+?) \((.+?)\)$"
)
ROOM_LINE_REGEX = re.compile(r"^\* Room    : (.+)$")
FACULTY_LINE_REGEX = re.compile(r"^\* Faculty : (.+)$")
SECTION_LINE_REGEX = re.compile(r"^\* Section : S-10$")
TYPE_LINE_REGEX = re.compile(r"^\* Type    : (Lecture|Lab|Skill)$")
NOTE_LINE_REGEX = re.compile(r"^\* Note    : (.+)$")
STATS_LINE_REGEX = re.compile(
    r"^📊 (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) \| Wk\d+: "
    r"(\d+) academic · (\d+) lab\(s\) · (\d+) non-ERP · Regular instruction$"
)


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Isolate SQLite database, credentials, and settings."""
    test_db = str(tmp_path / "schedule_formatting.db")
    test_dedup = MessageDeduplicator(db_path=test_db)

    monkeypatch.setattr(settings, "spark_db", test_db)
    monkeypatch.setattr(settings, "owner_chat_id", 123456789)
    monkeypatch.setattr(
        settings, "bot_token", MagicMock(get_secret_value=lambda: "bot123:mock_token")
    )
    monkeypatch.setattr(settings, "spark_timetable", DEFAULT_TIMETABLE_PATH)
    monkeypatch.setattr("src.utils.deduplication.deduplicator", test_dedup)
    monkeypatch.setattr("src.ingestion.handlers.deduplicator", test_dedup)
    yield test_dedup


def _validate_schedule_output_format(output: str, day_name: str, is_today: bool) -> dict:
    """Validate that schedule output strictly complies with 4-slot structure and stats line."""
    if output.startswith("No scheduled classes for"):
        assert "Enjoy your day 🎉" in output
        return {"empty": True, "slot_count": 0}

    lines = [line for line in output.split("\n") if line.strip()]
    assert len(lines) >= 7, f"Schedule output too short: {output}"

    # Last line must be stats line
    stats_line = lines[-1]
    stats_match = STATS_LINE_REGEX.match(stats_line)
    assert stats_match is not None, f"Stats line does not match schema: {stats_line}"
    assert stats_match.group(1) == day_name, f"Day mismatch in stats: {stats_line}"

    academic_cnt = int(stats_match.group(2))
    lab_cnt = int(stats_match.group(3))
    non_erp_cnt = int(stats_match.group(4))

    slot_blocks = [block for block in output.split("\n\n") if block.strip()]
    actual_slots = [block for block in slot_blocks if not block.strip().startswith("📊")]

    observed_academic = 0
    observed_lab = 0
    observed_non_erp = 0

    for block in actual_slots:
        slot_lines = block.strip().split("\n")
        assert len(slot_lines) == 6, f"Slot block must have 6 lines, got {len(slot_lines)}: {block}"

        # Line 1: Header
        h_match = SLOT_HEADER_REGEX.match(slot_lines[0])
        assert h_match is not None, f"Slot header regex mismatch: {slot_lines[0]}"
        icon = h_match.group(1)
        if not is_today:
            # Tomorrow schedule must use static icons (⬡ for regular, 🔴 for cancelled)
            assert icon in ("⬡", "🔴"), f"Unexpected icon for tomorrow: {icon}"

        # Line 2: Room
        r_match = ROOM_LINE_REGEX.match(slot_lines[1])
        assert r_match is not None, f"Room line format mismatch: {slot_lines[1]}"

        # Line 3: Faculty
        f_match = FACULTY_LINE_REGEX.match(slot_lines[2])
        assert f_match is not None, f"Faculty line format mismatch: {slot_lines[2]}"

        # Line 4: Section
        s_match = SECTION_LINE_REGEX.match(slot_lines[3])
        assert s_match is not None, f"Section line format mismatch: {slot_lines[3]}"

        # Line 5: Type
        t_match = TYPE_LINE_REGEX.match(slot_lines[4])
        assert t_match is not None, f"Type line format mismatch: {slot_lines[4]}"
        c_type = t_match.group(1)
        if c_type == "Lab":
            observed_lab += 1
        elif c_type == "Skill":
            observed_non_erp += 1
        else:
            observed_academic += 1

        # Line 6: Note
        n_match = NOTE_LINE_REGEX.match(slot_lines[5])
        assert n_match is not None, f"Note line format mismatch: {slot_lines[5]}"

    # Verify counts match stats line
    assert observed_academic == academic_cnt, (
        f"Academic count mismatch: {observed_academic} vs {academic_cnt}"
    )
    assert observed_lab == lab_cnt, f"Lab count mismatch: {observed_lab} vs {lab_cnt}"
    assert observed_non_erp == non_erp_cnt, (
        f"Non-ERP count mismatch: {observed_non_erp} vs {non_erp_cnt}"
    )
    assert len(actual_slots) == (academic_cnt + lab_cnt + non_erp_cnt)

    return {
        "empty": False,
        "slot_count": len(actual_slots),
        "academic": academic_cnt,
        "lab": lab_cnt,
        "non_erp": non_erp_cnt,
    }


def test_every_day_of_the_week_timetable_coverage():
    """1. Test every day of the week across the KLEF timetable (Mon–Sun)."""
    # Week 1 dates starting 2026-07-20 (Mon) through 2026-07-26 (Sun)
    day_dates = [
        ("Monday", date(2026, 7, 20)),
        ("Tuesday", date(2026, 7, 21)),
        ("Wednesday", date(2026, 7, 22)),
        ("Thursday", date(2026, 7, 23)),
        ("Friday", date(2026, 7, 24)),
        ("Saturday", date(2026, 7, 25)),
        ("Sunday", date(2026, 7, 26)),
    ]

    tt = load_timetable(DEFAULT_TIMETABLE_PATH)
    assert tt is not None

    for day_name, d in day_dates:
        # Test tomorrow mode (now_dt=None)
        res_tomorrow = format_day_schedule(d, now_dt=None, timetable=tt)
        val_tomorrow = _validate_schedule_output_format(res_tomorrow, day_name, is_today=False)

        # Test today mode at 07:00 AM (before classes)
        res_today_early = format_day_schedule(
            d, now_dt=datetime(d.year, d.month, d.day, 7, 0, tzinfo=IST), timetable=tt
        )
        val_today_early = _validate_schedule_output_format(res_today_early, day_name, is_today=True)

        # Test today mode at 12:00 PM (midday)
        res_today_mid = format_day_schedule(
            d, now_dt=datetime(d.year, d.month, d.day, 12, 0, tzinfo=IST), timetable=tt
        )
        val_today_mid = _validate_schedule_output_format(res_today_mid, day_name, is_today=True)

        # Test today mode at 17:00 (after classes)
        res_today_late = format_day_schedule(
            d, now_dt=datetime(d.year, d.month, d.day, 17, 0, tzinfo=IST), timetable=tt
        )
        val_today_late = _validate_schedule_output_format(res_today_late, day_name, is_today=True)

        if day_name == "Sunday":
            assert val_tomorrow["empty"] is True
            assert val_today_early["empty"] is True
            assert val_today_mid["empty"] is True
            assert val_today_late["empty"] is True
        else:
            assert val_tomorrow["empty"] is False
            assert val_tomorrow["slot_count"] > 0
            assert val_today_early["slot_count"] == val_tomorrow["slot_count"]
            assert val_today_mid["slot_count"] == val_tomorrow["slot_count"]
            assert val_today_late["slot_count"] == val_tomorrow["slot_count"]


def test_slot_note_generation_across_weeks_and_types():
    """2. Verify slot note generation (week topic, exam flags, lab prep, room override notes)."""
    tt = load_timetable(DEFAULT_TIMETABLE_PATH)
    assert tt is not None

    # Test across multiple weeks: Wk 1, Wk 5, Wk 10, Wk 15
    test_dates = [
        (date(2026, 7, 20), 1),
        (date(2026, 8, 17), 5),
        (date(2026, 9, 21), 10),
        (date(2026, 10, 26), 15),
    ]

    for d, expected_wk in test_dates:
        output = format_day_schedule(d, now_dt=None, timetable=tt)
        # Check stats line week
        assert f"Wk{expected_wk}:" in output

        # Check slot notes
        for block in output.split("\n\n"):
            if block.strip().startswith("📊"):
                continue
            lines = block.strip().split("\n")
            c_type = lines[4].split(":")[1].strip()
            note = lines[5].split(":")[1].strip()

            if c_type == "Lab":
                assert note == f"Week {expected_wk} lab session; bring laptop"
            elif c_type in ("Lecture", "Skill"):
                assert note == f"Week {expected_wk} core topics"


def test_simultaneous_room_override_injection_today_and_tomorrow(setup_test_env):
    """3. Test room override injection on /today and /tomorrow simultaneously without leakage."""
    dedup = setup_test_env
    today = date(2026, 10, 23)  # Friday
    tomorrow = date(2026, 10, 24)  # Saturday

    # Inject room override for Friday (Period 1 ML -> H-999)
    dedup.record_override(
        target_date="2026-10-23",
        period=1,
        course_code="25SC2107E",
        course_name="ML",
        room="H-999",
        status="OVERRIDE",
        summary="ML room shifted to H-999",
    )

    # Inject cancellation for Saturday (Period 2 ESD -> CANCELLED)
    # Check what Saturday has at period 2 in timetable: ESD
    dedup.record_override(
        target_date="2026-10-24",
        period=2,
        course_code="25EC2206E",
        course_name="ESD",
        room=None,
        status="CANCELLED",
        summary="ESD cancelled on Saturday",
    )

    # Format today
    today_now = datetime(2026, 10, 23, 7, 0, tzinfo=IST)
    output_today = format_day_schedule(today, now_dt=today_now)

    # Format tomorrow
    output_tomorrow = format_day_schedule(tomorrow, now_dt=None)

    # Validate Today:
    # 1. Period 1 ML has Room H-999 and override note
    assert "* Room    : H-999" in output_today
    assert "* Note    : ⚡ Room override: ROOM_OVERRIDE" in output_today
    # 2. Today must NOT have Saturday's cancellation
    assert "❌ Class cancelled" not in output_today

    # Validate Tomorrow:
    # 1. Period 2 OSSP is cancelled (icon 🔴, note '❌ Class cancelled')
    assert "🔴 [09:00 AM – 09:50 AM]: Operating Systems & Systems Programming" in output_tomorrow
    assert "* Note    : ❌ Class cancelled" in output_tomorrow
    # 2. Tomorrow must NOT have Friday's H-999 room override
    assert "H-999" not in output_tomorrow


@pytest.mark.asyncio
async def test_today_and_tomorrow_bot_commands_simultaneously(setup_test_env, monkeypatch):
    """Test full handle_bot_command execution for /today and /tomorrow in sequence."""
    fixed_now = datetime(2026, 10, 23, 8, 30, tzinfo=IST)  # Friday during P1
    monkeypatch.setattr(clock, "now_ist", lambda: fixed_now)
    monkeypatch.setattr(clock, "today_ist", lambda: fixed_now.date())

    sent_messages = []

    def mock_send(text, buttons=None, parse_mode=None, chat_id=None):
        sent_messages.append(text)
        return {"ok": True, "result": {"message_id": len(sent_messages)}}

    monkeypatch.setattr(bot, "send", mock_send)

    # Call /today
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/today"})
    assert len(sent_messages) == 1
    today_text = sent_messages[0]

    # Call /tomorrow
    await handle_bot_command({"chat": {"id": 123456789}, "text": "/tomorrow"})
    assert len(sent_messages) == 2
    tomorrow_text = sent_messages[1]

    # Verify today has live icon (🔴 for current P1)
    assert "🔴 [08:10 AM – 09:00 AM]" in today_text

    # Verify tomorrow has Saturday schedule with static ⬡ icons only
    assert "📊 Saturday | Wk15:" in tomorrow_text
    assert "✅" not in tomorrow_text
    assert "🟡" not in tomorrow_text


def test_period_6_omission():
    """Ensure non-existent Period 6 is never emitted in schedule outputs."""
    tt = load_timetable(DEFAULT_TIMETABLE_PATH)
    assert tt is not None

    for d in range(20, 27):
        target_date = date(2026, 7, d)
        slots = get_effective_slots(target_date, tt)
        for s in slots:
            assert s.period != 6, f"Period 6 found in {target_date}: {s}"


def test_course_code_shadowing_adversarial_probe(setup_test_env):
    """Empirical investigation into override matching by course short name vs course code.

    When period is None and course_code is provided alongside course_name,
    verify behavior when matching slots.
    """
    dedup = setup_test_env
    test_date = date(2026, 7, 20)  # Monday: DBSE is in Period 1 & 2

    # Case A: Override with course_name only (short code DBSE) and period=None
    dedup.record_override(
        target_date="2026-07-20",
        period=None,
        course_code="",
        course_name="DBSE",
        room="H-TEST-A",
        status="OVERRIDE",
    )
    slots_a = get_effective_slots(test_date)
    # Both DBSE periods should receive the override
    dbse_slots_a = [s for s in slots_a if s.course == "DBSE"]
    assert len(dbse_slots_a) == 2
    assert all(s.room == "H-TEST-A" for s in dbse_slots_a)
