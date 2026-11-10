"""Empirical adversarial test suite for Milestone 2 remediation challenges.

Author: challenger_m2_2
Target:
  1. src/academic_calendar.py: Timezone fallback, Invariant 5, midnight boundary
  2. src/erp/sync.py: Rate-limit pacing (400ms delay), event loop non-blocking
"""

import asyncio
import time
from datetime import UTC, date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from src.academic_calendar import (
    AcademicCalendar,
    _normalize_args,
    get_milestone_date,
    get_milestone_window,
    load_calendar,
)
from src.config import settings
from src.erp.sync import AcademicERPSyncAgent
from src.utils import clock

# ==============================================================================
# SECTION 1: ACADEMIC CALENDAR & TIMEZONE BOUNDARY ADVERSARIAL TESTS
# ==============================================================================


@pytest.fixture(scope="module")
def cal() -> AcademicCalendar:
    loaded = load_calendar()
    assert loaded is not None, "Failed to load default 2026-2027 academic calendar"
    return loaded


def test_normalize_args_polymorphism_with_none_date(cal: AcademicCalendar):
    """Verify _normalize_args returns clock.today_ist() for all arg styles with raw_date=None."""
    expected_today = clock.today_ist()

    # Style 1: (milestone, None, cal)
    m1, d1, c1 = _normalize_args("fee", None, cal)
    assert m1 == "fee"
    assert d1 == expected_today
    assert c1 is cal

    # Style 2: (cal, milestone, None)
    m2, d2, c2 = _normalize_args(cal, "fee", None)
    assert m2 == "fee"
    assert d2 == expected_today
    assert c2 is cal

    # Style 3: (cal, milestone, c=None) (e.g. 2-argument invocation)
    m3, d3, c3 = _normalize_args(cal, "fee", None)
    assert m3 == "fee"
    assert d3 == expected_today
    assert c3 is cal


@pytest.mark.parametrize(
    "fuzzed_raw_date",
    [
        None,
        False,
        0,
        [],
        {},
        (),
        object(),
        123456,
        -1,
        3.14159,
    ],
)
def test_normalize_args_fuzzed_raw_date_graceful_ist_fallback(
    cal: AcademicCalendar, fuzzed_raw_date
):
    """Non-date, non-str objects must fall back to clock.today_ist() without crashing."""
    expected_today = clock.today_ist()
    m, d, c = _normalize_args("mid-term", fuzzed_raw_date, cal)
    assert m == "mid-term"
    assert d == expected_today
    assert c is cal


def test_timezone_midnight_boundary_utc_vs_ist(cal: AcademicCalendar):
    """Adversarially simulate host running at UTC midnight boundary.

    Scenario:
      At 2026-11-01 20:00:00 UTC:
      - Host in UTC: date is 2026-11-01 (T04 active).
      - Host in PST (UTC-8): date is 2026-11-01 12:00:00 (T04 active).
      - Institutional IST: 2026-11-02 01:30:00 AM -> date is 2026-11-02 (T05 active!).

    If date.today() was used, it would yield 2026-11-01 -> T04 fee (2026-09-26).
    With clock.today_ist(), it yields 2026-11-02 -> T05 fee (2027-01-09).
    """
    fixed_utc_dt = datetime(2026, 11, 1, 20, 0, 0, tzinfo=UTC)

    # Patch clock.now_ist to simulate the exact UTC moment converted to IST
    simulated_ist_dt = fixed_utc_dt.astimezone(clock.IST)
    assert simulated_ist_dt.date() == date(2026, 11, 2)

    with patch("src.utils.clock.now_ist", return_value=simulated_ist_dt):
        today_date = clock.today_ist()
        assert today_date == date(2026, 11, 2), "clock.today_ist() failed to reflect IST date"

        # Style A: (cal, milestone, None)
        fee_date_a = get_milestone_date(cal, "fee", None)
        assert fee_date_a == date(2027, 1, 9), (
            f"Expected T05 fee date 2027-01-09, got {fee_date_a} (Invariant 5 boundary breach!)"
        )

        # Style B: (milestone, None, cal)
        fee_date_b = get_milestone_date("fee", None, cal)
        assert fee_date_b == date(2027, 1, 9)

        # Window query with raw_date=None
        window = get_milestone_window(cal, "mid-term", None)
        assert window == (date(2026, 12, 14), date(2026, 12, 19))


def test_timezone_midnight_boundary_pst_vs_ist(cal: AcademicCalendar):
    """Adversarially simulate host running in US Pacific Time (PST/PDT).

    Scenario:
      At 2027-02-07 22:00:00 UTC:
      - Host in PST (UTC-8): date is 2027-02-07 14:00:00 (T05 active).
      - Host in UTC: date is 2027-02-07 22:00:00 (T05 active).
      - IST (UTC+5:30): time is 2027-02-08 03:30:00 AM -> date is 2027-02-08 (T06 transition / gap).

    With IST date 2027-02-08:
      _resolve_term must resolve to T06 (the upcoming term).
      Milestone "fee" for T06 is 2027-04-10.
    """
    fixed_utc_dt = datetime(2027, 2, 7, 22, 0, 0, tzinfo=UTC)
    simulated_ist_dt = fixed_utc_dt.astimezone(clock.IST)
    assert simulated_ist_dt.date() == date(2027, 2, 8)

    with patch("src.utils.clock.now_ist", return_value=simulated_ist_dt):
        today_date = clock.today_ist()
        assert today_date == date(2027, 2, 8)

        t6_fee_date = get_milestone_date(cal, "fee", None)
        assert t6_fee_date == date(2027, 4, 10), (
            f"Expected T06 fee date 2027-04-10 across PST/IST boundary, got {t6_fee_date}"
        )


def test_clock_timezone_invariants():
    """Verify clock.py strict adherence to Invariant 5 (IST +05:30)."""
    now = clock.now_ist()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(hours=5, minutes=30)
    assert clock.today_ist() == now.date()

    # Naive datetime treated as UTC and converted to IST
    naive_utc = datetime(2026, 11, 9, 0, 0, 0)
    converted = clock.to_ist(naive_utc)
    assert converted.tzinfo is not None
    assert converted.hour == 5
    assert converted.minute == 30
    assert converted.date() == date(2026, 11, 9)

    # Aware datetime in non-IST timezone (e.g. UTC-8 PST)
    pst = timezone(timedelta(hours=-8), "PST")
    pst_dt = datetime(2026, 11, 9, 12, 0, 0, tzinfo=pst)
    ist_converted = clock.to_ist(pst_dt)
    # 12:00 PST = 20:00 UTC = 01:30 IST next day
    assert ist_converted.date() == date(2026, 11, 10)
    assert ist_converted.hour == 1
    assert ist_converted.minute == 30


# ==============================================================================
# SECTION 2: ERP SYNC RATE-LIMIT PACING & CONCURRENCY ADVERSARIAL TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_erp_sync_sequential_timing_enforces_400ms_delays():
    """Empirically measure delays between sequential ERP requests in sync_once.

    Verifies:
      1. get_attendance finishes -> at least 0.38s delay before get_marks begins.
      2. get_marks finishes -> at least 0.38s delay before get_exam_seating begins.
      3. Total duration of sync_once is >= 0.78s (2 x 400ms pacing delays).
    """
    agent = AcademicERPSyncAgent()
    settings.erp_username = "test_user"
    settings.erp_password = SecretStr("test_password")

    event_timestamps = []

    async def mock_get_attendance(**kw):
        event_timestamps.append(("att_start", time.perf_counter()))
        await asyncio.sleep(0.01)
        event_timestamps.append(("att_end", time.perf_counter()))
        return []

    async def mock_get_marks(**kw):
        event_timestamps.append(("marks_start", time.perf_counter()))
        await asyncio.sleep(0.01)
        event_timestamps.append(("marks_end", time.perf_counter()))
        return []

    async def mock_get_exam_seating(**kw):
        event_timestamps.append(("seating_start", time.perf_counter()))
        await asyncio.sleep(0.01)
        event_timestamps.append(("seating_end", time.perf_counter()))
        return []

    with (
        patch("src.erp.client.klu_erp.get_attendance", side_effect=mock_get_attendance),
        patch("src.erp.client.klu_erp.get_marks", side_effect=mock_get_marks),
        patch("src.erp.client.klu_erp.get_exam_seating", side_effect=mock_get_exam_seating),
    ):
        t0 = time.perf_counter()
        result = await agent.sync_once(send_alerts=False)
        total_duration = time.perf_counter() - t0

    assert result["success"] is True

    # Extract recorded times
    ts = dict(event_timestamps)
    gap_1 = ts["marks_start"] - ts["att_end"]
    gap_2 = ts["seating_start"] - ts["marks_end"]

    # 400ms delay with 25ms tolerance for system timer jitter
    assert gap_1 >= 0.375, (
        f"Delay between attendance and marks was too short: {gap_1:.4f}s < 0.375s"
    )
    assert gap_2 >= 0.375, f"Delay between marks and seating was too short: {gap_2:.4f}s < 0.375s"
    assert total_duration >= 0.775, (
        f"Total sync_once duration was too short: {total_duration:.4f}s < 0.775s"
    )


@pytest.mark.asyncio
async def test_erp_sync_does_not_block_asyncio_event_loop():
    """Verify that asyncio.sleep(0.4) does NOT block concurrent coroutines.

    Adversarial challenge:
      A background worker running a high-frequency loop (50ms interval) must
      continue to fire multiple times while sync_once is executing its 400ms delays.
    """
    agent = AcademicERPSyncAgent()
    settings.erp_username = "test_user"
    settings.erp_password = SecretStr("test_password")

    concurrent_ticks = []

    async def high_frequency_background_worker(stop_evt: asyncio.Event):
        while not stop_evt.is_set():
            concurrent_ticks.append(time.perf_counter())
            await asyncio.sleep(0.05)

    with (
        patch("src.erp.client.klu_erp.get_attendance", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_marks", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_exam_seating", new_callable=AsyncMock, return_value=[]),
    ):
        stop_evt = asyncio.Event()
        bg_task = asyncio.create_task(high_frequency_background_worker(stop_evt))

        # Run sync_once concurrently with background worker
        sync_result = await agent.sync_once(send_alerts=False)

        stop_evt.set()
        await bg_task

    assert sync_result["success"] is True
    # In ~0.8s, a 50ms task should tick at least 12 times. Assert >= 8 for conservative headroom.
    assert len(concurrent_ticks) >= 8, (
        f"Event loop was blocked! Concurrent ticks only fired {len(concurrent_ticks)} times"
    )


@pytest.mark.asyncio
async def test_erp_sync_pacing_preserved_when_requests_fail_with_exceptions():
    """Adversarially verify that the 400ms delay executes even if ERP calls raise exceptions.

    If get_attendance throws a ConnectionError or TimeoutError, the agent MUST still
    respect the 400ms backoff before calling get_marks.
    """
    agent = AcademicERPSyncAgent()
    settings.erp_username = "test_user"
    settings.erp_password = SecretStr("test_password")

    marks_called_time = None
    att_failed_time = None

    async def failing_attendance(**kw):
        nonlocal att_failed_time
        att_failed_time = time.perf_counter()
        raise ConnectionResetError("ERP host forcibly closed connection")

    async def mock_get_marks(**kw):
        nonlocal marks_called_time
        marks_called_time = time.perf_counter()
        raise TimeoutError("ERP marks gateway timeout")

    async def mock_get_exam_seating(**kw):
        return []

    with (
        patch("src.erp.client.klu_erp.get_attendance", side_effect=failing_attendance),
        patch("src.erp.client.klu_erp.get_marks", side_effect=mock_get_marks),
        patch("src.erp.client.klu_erp.get_exam_seating", side_effect=mock_get_exam_seating),
    ):
        result = await agent.sync_once(send_alerts=False)

    assert result["success"] is True
    assert "attendance_error" in result
    assert "marks_error" in result
    assert att_failed_time is not None
    assert marks_called_time is not None

    delay = marks_called_time - att_failed_time
    assert delay >= 0.375, f"Delay after failed attendance call was not enforced: {delay:.4f}s"


@pytest.mark.asyncio
async def test_erp_sync_skips_delays_when_credentials_unconfigured():
    """Verify that sync_once exits immediately without sleeping if credentials are missing."""
    agent = AcademicERPSyncAgent()
    settings.erp_username = ""

    t0 = time.perf_counter()
    result = await agent.sync_once(send_alerts=False)
    elapsed = time.perf_counter() - t0

    assert result["success"] is False
    assert result["reason"] == "Unconfigured ERP credentials"
    assert elapsed < 0.05, f"Unconfigured sync pass took unexpectedly long: {elapsed:.4f}s"


@pytest.mark.asyncio
async def test_erp_sync_cancellation_propagates_cleanly():
    """Verify that cancelling sync_once during its 400ms sleep propagates asyncio.CancelledError."""
    agent = AcademicERPSyncAgent()
    settings.erp_username = "test_user"
    settings.erp_password = SecretStr("test_password")

    with (
        patch("src.erp.client.klu_erp.get_attendance", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_marks", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_exam_seating", new_callable=AsyncMock, return_value=[]),
    ):
        task = asyncio.create_task(agent.sync_once(send_alerts=False))
        # Give it 50ms to finish attendance and enter the first 400ms sleep
        await asyncio.sleep(0.05)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


# ==============================================================================
# SECTION 3: ADDITIONAL ADVERSARIAL STRESS & CONCURRENCY HARNESSES
# ==============================================================================


def test_year_end_midnight_boundary_utc_vs_ist(cal: AcademicCalendar):
    """Adversarially simulate host at New Year's Eve midnight crossover.

    Scenario:
      At 2026-12-31 20:00:00 UTC:
      - Host in UTC: date is 2026-12-31.
      - Host in PST: date is 2026-12-31 12:00:00.
      - Institutional IST: date is 2027-01-01 01:30:00 AM (New Year 2027!).

    In T05:
      On 2027-01-01 IST, upcoming fee deadline is 2027-01-09.
      Lab exam is 2027-01-18.
    """
    fixed_utc_dt = datetime(2026, 12, 31, 20, 0, 0, tzinfo=UTC)
    simulated_ist_dt = fixed_utc_dt.astimezone(clock.IST)
    assert simulated_ist_dt.date() == date(2027, 1, 1)

    with patch("src.utils.clock.now_ist", return_value=simulated_ist_dt):
        today_date = clock.today_ist()
        assert today_date == date(2027, 1, 1)

        fee_date = get_milestone_date(cal, "fee", None)
        assert fee_date == date(2027, 1, 9)

        lab_exam = get_milestone_date(cal, "lab exam", None)
        assert lab_exam == date(2027, 1, 18)


def test_datetime_instance_subclass_behavior_in_normalize_args(cal: AcademicCalendar):
    """Python datetime is a subclass of date (isinstance(dt, date) == True).

    Adversarial discovery:
      If a caller passes a datetime instance (e.g. clock.now_ist()),
      _normalize_args branches into `elif isinstance(raw_date, date): ref_date = raw_date`,
      retaining the datetime object.
      Downstream in _resolve_term(), comparing `date <= datetime` raises TypeError!
      However, with raw_date=None, clock.today_ist() explicitly calls .date(),
      guaranteeing a pure date instance that avoids this TypeError.
    """
    aware_dt = datetime(2026, 9, 1, 14, 30, tzinfo=clock.IST)
    m, d, c = _normalize_args("fee", aware_dt, cal)
    assert m == "fee"
    assert isinstance(d, datetime)  # Retains datetime because isinstance(datetime, date) is True

    # Passing datetime directly to get_milestone_date raises TypeError in _resolve_term
    with pytest.raises(
        TypeError,
        match="not supported between instances of 'datetime.date' and 'datetime.datetime'",
    ):
        get_milestone_date(cal, "fee", aware_dt)

    # Calling .date() avoids this issue cleanly
    resolved = get_milestone_date(cal, "fee", aware_dt.date())
    assert resolved == date(2026, 9, 26)


@pytest.mark.asyncio
async def test_erp_sync_five_concurrent_sync_runs():
    """Verify that 5 concurrent sync_once executions run concurrently without deadlocks."""
    agent = AcademicERPSyncAgent()
    settings.erp_username = "test_user"
    settings.erp_password = SecretStr("test_password")

    async def mock_fetch(**kw):
        await asyncio.sleep(0.01)
        return []

    with (
        patch("src.erp.client.klu_erp.get_attendance", side_effect=mock_fetch),
        patch("src.erp.client.klu_erp.get_marks", side_effect=mock_fetch),
        patch("src.erp.client.klu_erp.get_exam_seating", side_effect=mock_fetch),
    ):
        t0 = time.perf_counter()
        results = await asyncio.gather(*[agent.sync_once(send_alerts=False) for _ in range(5)])
        elapsed = time.perf_counter() - t0

    for res in results:
        assert res["success"] is True

    # Each sync has two 400ms sleeps; running 5 concurrently should take ~0.8s, not 4.0s.
    assert elapsed < 2.0, (
        f"Concurrent sync passes took too long ({elapsed:.2f}s), indicating serialized execution"
    )


@pytest.mark.asyncio
async def test_erp_sync_pacing_preserved_with_active_deltas_and_alerts():
    """Verify delays execute cleanly when records have deltas and trigger alert formatting."""
    agent = AcademicERPSyncAgent()
    settings.erp_username = "test_user"
    settings.erp_password = SecretStr("test_password")

    sample_att = [
        {
            "course_code": "25CS3112E",
            "course_name": "Deep Learning With Accelerated Computing",
            "ltps": "S",
            "section": "S-10",
            "conducted": 10,
            "attended": 9,
            "percentage": 90.0,
        }
    ]
    sample_marks = [
        {
            "course_code": "25CS3112E",
            "component": "Sem-In Exam 1",
            "marks": 24.5,
            "max_marks": 25.0,
        }
    ]

    event_log = []

    async def tracked_att(**kw):
        event_log.append(("att", time.perf_counter()))
        return sample_att

    async def tracked_marks(**kw):
        event_log.append(("marks", time.perf_counter()))
        return sample_marks

    async def tracked_seating(**kw):
        event_log.append(("seating", time.perf_counter()))
        return []

    dispatched = []

    async def mock_dispatch(text):
        dispatched.append(text)

    with (
        patch("src.erp.client.klu_erp.get_attendance", side_effect=tracked_att),
        patch("src.erp.client.klu_erp.get_marks", side_effect=tracked_marks),
        patch("src.erp.client.klu_erp.get_exam_seating", side_effect=tracked_seating),
        patch.object(agent, "_dispatch_alert", side_effect=mock_dispatch),
    ):
        res = await agent.sync_once(send_alerts=True)

    assert res["success"] is True
    times = dict(event_log)
    assert times["marks"] - times["att"] >= 0.375
    assert times["seating"] - times["marks"] >= 0.375


@pytest.mark.asyncio
async def test_erp_sync_scheduler_graceful_shutdown():
    """Verify run_erp_sync terminates immediately when stop_event is set."""
    from src.erp.sync import run_erp_sync

    stop_evt = asyncio.Event()
    # Trigger stop immediately
    stop_evt.set()

    t0 = time.perf_counter()
    # Should exit immediately without waiting for next scheduled run (hours away)
    await run_erp_sync(stop_event=stop_evt)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.2, f"Scheduler did not terminate immediately on stop_event: {elapsed:.4f}s"
