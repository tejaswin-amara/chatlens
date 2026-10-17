"""Unit tests for dynamic timetable override merging and persistence."""

from datetime import date

from src.timetable import Meta, Slot, Timetable, get_effective_slots
from src.utils.deduplication import MessageDeduplicator


def test_timetable_override_merging(tmp_path) -> None:
    db_file = str(tmp_path / "test_overrides.db")
    dedup = MessageDeduplicator(db_path=db_file)

    # Monkeypatch deduplicator for testing

    test_date = "2026-10-19"  # Monday
    slots = [
        Slot(day="Mon", period=1, course="DBSE", room="H-005", faculty="Divya Priya Degala"),
        Slot(day="Mon", period=2, course="DBSE", room="H-005", faculty="Divya Priya Degala"),
        Slot(day="Mon", period=3, course="ESD & IoT", room="H301A", faculty="Kurakula Anudeep"),
    ]
    tt_model = Timetable(
        meta=Meta(
            term="T04",
            valid_from=date(2026, 8, 1),
            valid_to=date(2026, 11, 30),
            sample=False,
        ),
        slots=slots,
    )

    # 1. Base slots without overrides
    base = get_effective_slots(test_date, tt_model)
    assert len(base) == 3
    assert base[0].room == "H-005"
    assert base[0].override is None

    # 2. Add room override for P1 to H-106
    dedup.record_override(
        target_date=test_date,
        period=1,
        course_code="25CS1302E",
        course_name="DBSE",
        room="H-106",
        status="OVERRIDE",
        summary="Lab shifted to H-106",
    )

    # 3. Add class cancellation for P3
    dedup.record_override(
        target_date=test_date,
        period=3,
        course_code="25EC2206E",
        course_name="ESD & IoT",
        room=None,
        status="CANCELLED",
        summary="Faculty on leave",
    )

    # Patch deduplicator in timetable module for test run
    from unittest.mock import patch

    with patch("src.utils.deduplication.deduplicator", dedup):
        effective = get_effective_slots(test_date, tt_model)
        assert len(effective) == 3

        # P1: Room overridden
        assert effective[0].period == 1
        assert effective[0].room == "H-106"
        assert "ROOM_OVERRIDE" in (effective[0].override or "")

        # P2: Untouched
        assert effective[1].period == 2
        assert effective[1].room == "H-005"
        assert effective[1].override is None

        # P3: Cancelled
        assert effective[2].period == 3
        assert effective[2].override == "CANCELLED"
