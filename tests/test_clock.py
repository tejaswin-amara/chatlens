from datetime import UTC, date, datetime, timedelta, timezone

from src.utils import clock
from src.utils.clock import IST, to_ist


def test_clock_offset_and_tzname():
    assert IST.utcoffset(None) == timedelta(hours=5, minutes=30)
    assert IST.tzname(None) == "IST"


def test_clock_today_ist_evening_utc():
    # 2026-09-29T20:00Z -> 2026-09-30 01:30:00 IST
    dt = datetime(2026, 9, 29, 20, 0, tzinfo=UTC)
    ist_dt = dt.astimezone(IST)
    assert ist_dt.date() == date(2026, 9, 30)


def test_clock_to_ist_naive_treated_as_utc():
    naive = datetime(2026, 9, 29, 20, 0)
    ist_dt = to_ist(naive)
    assert ist_dt.date() == date(2026, 9, 30)


def test_clock_to_ist_aware_converted():
    aware = datetime(2026, 9, 29, 10, 0, tzinfo=timezone(timedelta(hours=-4)))
    ist_dt = to_ist(aware)
    # 10:00 -04:00 is 14:00 UTC, which is 19:30 IST
    assert ist_dt.hour == 19
    assert ist_dt.minute == 30


def test_frozen_clock_fixture(frozen_clock):
    frozen_clock("2026-09-29T20:00:00Z")
    assert clock.now_ist().isoformat() == "2026-09-30T01:30:00+05:30"


def test_clock_boundary():
    # 18:29Z vs 18:31Z
    dt1 = to_ist(datetime(2026, 9, 29, 18, 29, tzinfo=UTC))
    dt2 = to_ist(datetime(2026, 9, 29, 18, 31, tzinfo=UTC))

    assert dt1.date() == date(2026, 9, 29)  # 23:59 IST
    assert dt2.date() == date(2026, 9, 30)  # 00:01 IST
