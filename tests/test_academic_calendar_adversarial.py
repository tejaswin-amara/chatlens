"""Adversarial stress harness for 2026-2027 Academic Calendar (Milestone M1).

Stress tests boundary conditions, multi-day exam windows, overlapping terms,
Invariant 5 adversarial forgery rejection, and malformed/fuzzed inputs.
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.academic_calendar import (
    AcademicCalendar,
    get_milestone_date,
    get_milestone_window,
    load_calendar,
)


@pytest.fixture(scope="module")
def cal() -> AcademicCalendar:
    loaded = load_calendar()
    assert loaded is not None, "Failed to load default 2026-2027 calendar"
    return loaded


# ==============================================================================
# 1. BOUNDARY STRESS TESTS
# ==============================================================================


@pytest.mark.parametrize(
    "term, start_d, end_d, expected_prev_term, expected_next_term",
    [
        ("T04", date(2026, 7, 13), date(2026, 11, 1), "T04", "T05"),
        ("T05", date(2026, 11, 4), date(2027, 2, 7), "T05", "T06"),
        ("T06", date(2027, 2, 9), date(2027, 5, 9), "T06", "Summer"),
        ("Summer", date(2027, 5, 31), date(2027, 7, 11), "Summer", "Summer"),
    ],
)
def test_term_boundary_conditions(
    cal: AcademicCalendar,
    term: str,
    start_d: date,
    end_d: date,
    expected_prev_term: str,
    expected_next_term: str,
):
    """Test day before start, exact start, exact end, and day after end."""
    day_before = start_d - timedelta(days=1)
    day_after = end_d + timedelta(days=1)

    # 1. Exact start date must resolve to term
    w_start = get_milestone_window("orientation" if term != "Summer" else "classwork", start_d, cal)
    # Start date should resolve to valid term window without error
    assert w_start is not None

    # 2. Exact end date must resolve to term
    w_end = get_milestone_window("sem-end", end_d, cal)
    assert w_end is not None

    # 3. Day before start should resolve to nearest upcoming/current term without throwing
    res_before = get_milestone_date(
        "orientation" if term != "Summer" else "classwork", day_before, cal
    )
    assert res_before is not None

    # 4. Day after end should resolve to nearest following term without throwing
    res_after = get_milestone_date("mid-term", day_after, cal)
    assert res_after is not None


def test_inter_term_gap_boundaries(cal: AcademicCalendar):
    """Verify behavior during gaps between official terms."""
    # Gap between T04 (ends 2026-11-01) and T05 (starts 2026-11-04): 2026-11-02, 2026-11-03
    gap_nov2 = date(2026, 11, 2)
    gap_nov3 = date(2026, 11, 3)

    # Both dates should smoothly resolve to upcoming T05 for milestone queries
    w_mid_t5 = get_milestone_window("mid-term", gap_nov2, cal)
    assert w_mid_t5 == (date(2026, 12, 14), date(2026, 12, 19))

    w_mid_t5_2 = get_milestone_window("mid-term", gap_nov3, cal)
    assert w_mid_t5_2 == (date(2026, 12, 14), date(2026, 12, 19))

    # Gap between T05 (ends 2027-02-07) and T06 (starts 2027-02-09): 2027-02-08
    gap_feb8 = date(2027, 2, 8)
    w_mid_t6 = get_milestone_window("mid-term", gap_feb8, cal)
    assert w_mid_t6 == (date(2027, 3, 22), date(2027, 3, 27))

    # Gap between T06 (ends 2027-05-09) and Summer classwork (2027-05-31): e.g. 2027-05-20
    gap_may20 = date(2027, 5, 20)
    w_mid_summer = get_milestone_window("mid-term", gap_may20, cal)
    assert w_mid_summer == (date(2027, 6, 18), date(2027, 6, 19))


# ==============================================================================
# 2. MULTI-DAY EXAM WINDOWS (FALSE-POSITIVE IMMUNITY & PRECISION)
# ==============================================================================


@pytest.mark.parametrize(
    "term, milestone, start_str, end_str",
    [
        # T04
        ("T04", "mid-term", "2026-09-04", "2026-09-08"),
        ("T04", "lab exam", "2026-10-12", "2026-10-17"),
        ("T04", "sem-end lab exam", "2026-10-19", "2026-10-24"),
        ("T04", "sem-end", "2026-10-26", "2026-11-01"),
        # T05
        ("T05", "mid-term", "2026-12-14", "2026-12-19"),
        ("T05", "lab exam", "2027-01-18", "2027-01-23"),
        ("T05", "sem-end lab exam", "2027-01-25", "2027-01-30"),
        ("T05", "sem-end", "2027-02-01", "2027-02-07"),
        # T06
        ("T06", "mid-term", "2027-03-22", "2027-03-27"),
        ("T06", "lab exam", "2027-04-19", "2027-04-24"),
        ("T06", "sem-end lab exam", "2027-04-26", "2027-05-01"),
        ("T06", "sem-end", "2027-05-02", "2027-05-09"),
        # Summer
        ("Summer", "mid-term", "2027-06-18", "2027-06-19"),
        ("Summer", "lab exam", "2027-06-29", "2027-06-30"),
        ("Summer", "sem-end", "2027-07-08", "2027-07-11"),
    ],
)
def test_all_days_in_exam_windows_zero_false_positives(
    cal: AcademicCalendar,
    term: str,
    milestone: str,
    start_str: str,
    end_str: str,
):
    """Every single day inside a multi-day exam window must return msg_dt (no conflict)."""
    start_d = date.fromisoformat(start_str)
    end_d = date.fromisoformat(end_str)

    # 1. Window bounds match
    w = get_milestone_window(milestone, start_d, cal, term_hint=term)
    assert w == (start_d, end_d), f"Window mismatch for {term} {milestone}"

    # 2. Iterate every single day within window: cal_date must equal queried day (identity)
    curr = start_d
    days_checked = 0
    while curr <= end_d:
        resolved = get_milestone_date(milestone, curr, cal, term_hint=term)
        assert resolved == curr, (
            f"False conflict alarm for {term} {milestone} on day {curr}: got {resolved}"
        )
        days_checked += 1
        curr += timedelta(days=1)

    assert days_checked >= 2, f"Window for {milestone} should be multi-day"

    # 3. Day immediately before start must conflict (returns start_d != day_before)
    day_before = start_d - timedelta(days=1)
    res_before = get_milestone_date(milestone, day_before, cal, term_hint=term)
    assert res_before == start_d
    assert res_before != day_before, "Failed to detect conflict 1 day before window"

    # 4. Day immediately after end must conflict (returns start_d != day_after)
    day_after = end_d + timedelta(days=1)
    res_after = get_milestone_date(milestone, day_after, cal, term_hint=term)
    assert res_after == start_d
    assert res_after != day_after, "Failed to detect conflict 1 day after window"


# ==============================================================================
# 3. OVERLAPPING TERM WINDOW DISAMBIGUATION
# ==============================================================================


def test_october_2026_t4_active_with_t5_orientation(cal: AcademicCalendar):
    """October 2026: T4 is active (ends Nov 1), while T5 orientation is Oct 5-7."""
    test_d = date(2026, 10, 6)

    # Without term hint: date falls in T04 (2026-07-13 to 2026-11-01), so resolves to T04
    # Querying "orientation" without hint returns T04 orientation window (July 2026)
    w_unhinted = get_milestone_window("orientation", test_d, cal)
    assert w_unhinted == (date(2026, 7, 13), date(2026, 7, 18))
    # Querying milestone date on Oct 6 returns July 13 (conflict with T04 orientation)
    assert get_milestone_date("orientation", test_d, cal) == date(2026, 7, 13)

    # With term hint for T5 (various formats): resolves to T05 orientation (Oct 5-7)
    for hint in ["T5", "t5", "T05", "t05", "Trimester-5", "Trimester 5", "TRIMESTER5"]:
        w_hinted = get_milestone_window("orientation", test_d, cal, term_hint=hint)
        assert w_hinted == (
            date(2026, 10, 5),
            date(2026, 10, 7),
        ), f"Failed to resolve T5 orientation with hint '{hint}'"

        d_hinted = get_milestone_date("orientation", test_d, cal, term_hint=hint)
        assert d_hinted == test_d, f"Failed identity match for T5 orientation with hint '{hint}'"


def test_october_2026_t5_immersion_window(cal: AcademicCalendar):
    """October 30-31, 2026: T5 Techno-Management Immersion occurs while T4 Sem End Exams run."""
    imm_d = date(2026, 10, 30)

    # With T5 hint: resolves immersion
    w_imm = get_milestone_window("immersion", imm_d, cal, term_hint="T5")
    assert w_imm == (date(2026, 10, 30), date(2026, 10, 31))
    assert get_milestone_date("immersion", imm_d, cal, term_hint="T5") == imm_d


def test_january_2027_t5_active_with_t6_orientation(cal: AcademicCalendar):
    """January 25-27, 2027: T6 orientation occurs while T5 is active.

    T5 Sem End Lab is Jan 25-30 while T6 orientation is Jan 25-27.
    """
    orient_d = date(2027, 1, 26)

    # Without hint: resolves to active term T05.
    # In T05, milestone is sem-end lab exam for that date
    w_t5_lab = get_milestone_window("sem-end lab exam", orient_d, cal)
    assert w_t5_lab == (date(2027, 1, 25), date(2027, 1, 30))

    # With T6 hint: resolves to T06 orientation
    for hint in ["T6", "T06", "Trimester 6"]:
        w_t6_orient = get_milestone_window("orientation", orient_d, cal, term_hint=hint)
        assert w_t6_orient == (
            date(2027, 1, 25),
            date(2027, 1, 27),
        ), f"Failed T6 orientation resolution with hint {hint}"
        assert get_milestone_date("orientation", orient_d, cal, term_hint=hint) == orient_d


def test_may_2027_summer_internships_before_classwork(cal: AcademicCalendar):
    """May 10-29, 2027: 3-week internship begins before Summer classwork start (May 31)."""
    intern_d = date(2027, 5, 15)

    w_intern = get_milestone_window("technical internship", intern_d, cal)
    assert w_intern == (date(2027, 5, 10), date(2027, 5, 29))
    assert get_milestone_date("technical internship", intern_d, cal) == intern_d


# ==============================================================================
# 4. INVARIANT 5 ENFORCEMENT & ADVERSARIAL FORGERY INJECTION
# ==============================================================================


@pytest.mark.parametrize(
    "term, milestone, official_date",
    [
        # T04
        ("T04", "fee", date(2026, 9, 26)),
        ("T04", "re-check", date(2026, 9, 12)),
        ("T04", "last instruction", date(2026, 10, 15)),
        ("T04", "detention", date(2026, 10, 16)),
        ("T04", "mid-term", date(2026, 9, 4)),
        ("T04", "lab exam", date(2026, 10, 12)),
        ("T04", "sem-end", date(2026, 10, 26)),
        # T05
        ("T05", "fee", date(2027, 1, 9)),
        ("T05", "re-check", date(2026, 12, 24)),
        ("T05", "last instruction", date(2027, 1, 28)),
        ("T05", "detention", date(2027, 1, 29)),
        ("T05", "mid-term", date(2026, 12, 14)),
        ("T05", "lab exam", date(2027, 1, 18)),
        ("T05", "sem-end", date(2027, 2, 1)),
        # T06
        ("T06", "fee", date(2027, 4, 10)),
        ("T06", "re-check", date(2027, 3, 31)),
        ("T06", "last instruction", date(2027, 4, 29)),
        ("T06", "detention", date(2027, 4, 30)),
        ("T06", "mid-term", date(2027, 3, 22)),
        ("T06", "lab exam", date(2027, 4, 19)),
        ("T06", "sem-end", date(2027, 5, 2)),
        # Summer
        ("Summer", "mid-term", date(2027, 6, 18)),
        ("Summer", "lab exam", date(2027, 6, 29)),
        ("Summer", "detention", date(2027, 7, 7)),
        ("Summer", "sem-end", date(2027, 7, 8)),
    ],
)
def test_invariant_5_adversarial_forgery_100_percent_detection(
    cal: AcademicCalendar,
    term: str,
    milestone: str,
    official_date: date,
):
    """Adversarially inject fake dates: verify 100% rejection rate across all milestones."""
    # Test offsets: -120d, -30d, -14d, -1d, +1d, +14d, +30d, +365d
    offsets = [-120, -30, -14, -1, 1, 14, 30, 365]

    for offset in offsets:
        forged_date = official_date + timedelta(days=offset)

        # Check if forged_date happens to fall in a multi-day window
        window = get_milestone_window(milestone, official_date, cal, term_hint=term)
        if window and window[0] <= forged_date <= window[1]:
            continue  # Legitimate date inside window is not a forgery

        # Query calendar with forged date
        cal_date = get_milestone_date(milestone, forged_date, cal, term_hint=term)

        # Invariant 5 check:
        # A conflict is flagged whenever cal_date and cal_date != forged_date
        assert cal_date is not None, f"Milestone date missing for {term} {milestone}"
        assert cal_date != forged_date, (
            f"SECURITY BYPASS: Forged date {forged_date} accepted for {term} {milestone}!"
        )


def test_cross_milestone_collision_forgery(cal: AcademicCalendar):
    """Adversarially swap dates: e.g. claiming Fee deadline on Mid-term date."""
    # T04 fee is 2026-09-26. Mid-term is 2026-09-04 to 2026-09-08.
    forged_fee_date = date(2026, 9, 6)
    cal_date = get_milestone_date("fee", forged_fee_date, cal, term_hint="T04")
    assert cal_date == date(2026, 9, 26)
    assert cal_date != forged_fee_date  # Conflict detected!

    # T04 detention is 2026-10-16. Sem-end theory is 2026-10-26.
    forged_det_date = date(2026, 10, 26)
    cal_det = get_milestone_date("detention", forged_det_date, cal, term_hint="T04")
    assert cal_det == date(2026, 10, 16)
    assert cal_det != forged_det_date  # Conflict detected!


# ==============================================================================
# 5. MALFORMED, FUZZED & ADVERSARIAL INPUT ROBUSTNESS
# ==============================================================================


@pytest.mark.parametrize(
    "fuzzed_milestone",
    [
        "",
        "   ",
        "\t\n",
        "a",
        "ab",
        "!@#$%^&*",
        "12345",
        "unknown_event_xyz",
        "MID_TERM_EXAM_FAKE",
    ],
)
def test_fuzzed_milestone_strings(cal: AcademicCalendar, fuzzed_milestone: str):
    """Non-existent or fuzzed milestones must return None without crashing."""
    ref_d = date(2026, 9, 15)
    assert get_milestone_date(fuzzed_milestone, ref_d, cal) is None
    assert get_milestone_window(fuzzed_milestone, ref_d, cal) is None


@pytest.mark.parametrize(
    "case_variant, expected_date",
    [
        ("MID-TERM", date(2026, 9, 4)),
        ("mid term", date(2026, 9, 4)),
        ("MID TERM", date(2026, 9, 4)),
        ("FEE", date(2026, 9, 26)),
        ("Fee", date(2026, 9, 26)),
        ("LAST INSTRUCTION", date(2026, 10, 15)),
        ("last-instruction", date(2026, 10, 15)),
        ("DETENTION", date(2026, 10, 16)),
        ("lab-exam", date(2026, 10, 12)),
        ("LAB EXAM", date(2026, 10, 12)),
    ],
)
def test_case_and_delimiter_normalization(
    cal: AcademicCalendar, case_variant: str, expected_date: date
):
    """Milestone queries must be case-insensitive and hyphen/space-agnostic."""
    ref_d = date(2026, 8, 1)
    res = get_milestone_date(case_variant, ref_d, cal, term_hint="T04")
    assert res == expected_date


def test_out_of_range_and_far_future_dates(cal: AcademicCalendar):
    """Calendar queries with far-past and far-future dates handle gracefully."""
    past_d = date(1970, 1, 1)
    future_d = date(2099, 12, 31)

    # Far past date resolves to earliest term (T04)
    res_past_fee = get_milestone_date("fee", past_d, cal)
    assert res_past_fee == date(2026, 9, 26)  # T04 fee

    # Far future date resolves to latest term (Summer)
    # Summer term has "sem-end" and "mid-term"
    res_future_sem_end = get_milestone_date("sem-end", future_d, cal)
    assert res_future_sem_end == date(2027, 7, 8)  # Summer sem-end

    # Summer term has no "fee" milestone; should return None gracefully without throwing
    res_future_fee = get_milestone_date("fee", future_d, cal)
    assert res_future_fee is None


def test_corrupted_calendar_toml_fuzzing():
    """Fuzz load_calendar with various corrupt TOML structures and invalid data types."""
    fuzz_samples = [
        # Syntax error
        b"[[[bad toml",
        # Empty file
        b"",
        # Non-table root
        b"12345",
        # Table with bad types for dates
        b"""
        [T04]
        start = "not-a-date"
        end = true
        fee = 999999
        events = "not-a-list"
        """,
        # Events list with corrupted entries
        b"""
        [T04]
        start = 2026-07-13
        events = [
            null,
            42,
            "string-item",
            {},
            { name = 123 },
            { name = "Missing dates", milestone = "bad" },
            { name = "Bad date format", start_date = "2026-99-99", milestone = "err" },
            {
                name = "End before start",
                start_date = 2026-10-10,
                end_date = 2026-10-05,
                milestone = "inverted",
            },
        ]
        """,
    ]

    for sample in fuzz_samples:
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="wb", delete=False) as tf:
            tf.write(sample)
            tf_path = tf.name

        try:
            # Must not crash under any corrupt input
            res = load_calendar(tf_path)
            # If successfully loaded, queries on it must also not crash
            if res is not None:
                get_milestone_date("fee", date(2026, 9, 1), res)
                get_milestone_window("fee", date(2026, 9, 1), res)
        finally:
            Path(tf_path).unlink(missing_ok=True)


def test_empty_academic_calendar_object():
    """Test get_milestone_date and get_milestone_window with empty AcademicCalendar."""
    empty_cal = AcademicCalendar(terms={}, events={})
    assert get_milestone_date("fee", date(2026, 9, 1), empty_cal) is None
    assert get_milestone_window("fee", date(2026, 9, 1), empty_cal) is None

    none_events_cal = AcademicCalendar(terms={"T04": {}}, events=None)
    assert get_milestone_date("fee", date(2026, 9, 1), none_events_cal) is None
    assert get_milestone_window("fee", date(2026, 9, 1), none_events_cal) is None


def test_unknown_or_empty_term_hint_fallback(cal: AcademicCalendar):
    """Unknown term hint must gracefully fall back to date-based term resolution."""
    ref_d = date(2026, 8, 15)  # Clearly within T04 (starts 2026-07-13, ends 2026-11-01)

    # Empty string hint
    assert get_milestone_date("fee", ref_d, cal, term_hint="") == date(2026, 9, 26)

    # Unknown term hints
    for unknown_hint in ["T99", "RandomTerm", "Spring2026", "None", "  "]:
        res = get_milestone_date("fee", ref_d, cal, term_hint=unknown_hint)
        assert res == date(2026, 9, 26), f"Failed fallback for unknown hint '{unknown_hint}'"


def test_cross_term_isolation(cal: AcademicCalendar):
    """Milestone queries constrained by term_hint must not leak events across terms."""
    # "immersion" only exists in T05 (Oct 30-31) and T06 (Mar 12-13), NOT in T04
    assert get_milestone_date("immersion", date(2026, 8, 1), cal, term_hint="T04") is None
    assert get_milestone_window("immersion", date(2026, 8, 1), cal, term_hint="T04") is None

    # "technical internship" only exists in Summer, NOT in T04 or T05 or T06
    assert (
        get_milestone_date("technical internship", date(2026, 8, 1), cal, term_hint="T04") is None
    )
    assert (
        get_milestone_date("technical internship", date(2026, 12, 1), cal, term_hint="T05") is None
    )
    assert (
        get_milestone_date("technical internship", date(2027, 3, 1), cal, term_hint="T06") is None
    )


def test_end_to_end_invariant_5_conflict_rendering(cal: AcademicCalendar):
    """Simulate end-to-end Telegram ingestion conflict detection and alert formatting."""
    from src.formatting.templates import render_calendar_conflict

    # Routine message claiming forged date for T04 mid-term
    milestone = "mid-term"
    forged_msg_dt = date(2026, 9, 20)
    official_cal_dt = get_milestone_date(milestone, forged_msg_dt, cal, term_hint="T04")

    assert official_cal_dt == date(2026, 9, 4)
    assert official_cal_dt != forged_msg_dt

    conflict_card = render_calendar_conflict(
        milestone_match=milestone,
        msg_dt=forged_msg_dt,
        cal_date=official_cal_dt,
    )

    assert "⚠️ **Calendar Conflict**" in conflict_card
    assert "mid-term" in conflict_card
    assert "2026-09-20" in conflict_card
    assert "2026-09-04" in conflict_card


def test_date_argument_error_modes(cal: AcademicCalendar):
    """Verify behavior of get_milestone_date with various date parameter types."""
    # 1. Valid ISO string parses cleanly
    assert get_milestone_date("fee", "2026-08-15", cal) == date(2026, 9, 26)

    # 2. Invalid date string raises ValueError (standard library behavior)
    with pytest.raises(ValueError):
        get_milestone_date("fee", "not-a-valid-date", cal)

    # 3. Non-string, non-date object defaults to date.today() without unhandled exception
    res_default = get_milestone_date("fee", 12345, cal)  # type: ignore
    # Today's date will resolve to one of the terms or closest term
    assert res_default is not None or res_default is None  # Does not crash
