import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.briefing import next_run
from src.main import run_briefing, run_heartbeat
from src.utils.clock import IST
from src.utils.deduplication import deduplicator


async def guard(coro, seconds: float = 5.0):
    return await asyncio.wait_for(coro, timeout=seconds)


def test_next_run_before_target():
    # 07:00 IST -> should return 07:15 today
    now = datetime(2026, 10, 15, 7, 0, 0, tzinfo=IST)
    target = next_run(now)
    assert target == datetime(2026, 10, 15, 7, 15, 0, tzinfo=IST)


def test_next_run_after_target():
    # 07:30 IST -> should return 07:15 tomorrow
    now = datetime(2026, 10, 15, 7, 30, 0, tzinfo=IST)
    target = next_run(now)
    assert target == datetime(2026, 10, 16, 7, 15, 0, tzinfo=IST)


def test_next_run_exact_second():
    # 07:15:00 IST -> should return 07:15 tomorrow (not today)
    now = datetime(2026, 10, 15, 7, 15, 0, tzinfo=IST)
    target = next_run(now)
    assert target == datetime(2026, 10, 16, 7, 15, 0, tzinfo=IST)


def test_next_run_timezone_naive():
    # Naive datetime must raise ValueError
    now = datetime(2026, 10, 15, 7, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        next_run(now)


@pytest.mark.asyncio
async def test_briefing_idempotent():
    # Running briefing twice on same day dispatches bot message only once
    deduplicator.meta_set("briefing_last_date", "2026-10-15")

    with (
        patch("src.utils.clock.now_ist", return_value=datetime(2026, 10, 15, 7, 15, tzinfo=IST)),
        patch("src.utils.clock.today_ist", return_value=datetime(2026, 10, 15).date()),
        patch("src.briefing.fetch_briefing_inputs") as mock_inputs,
        patch("src.notify.bot.bot.send") as mock_send,
        patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
    ):
        with pytest.raises(asyncio.CancelledError):
            await guard(run_briefing())

        mock_inputs.assert_not_called()
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_briefing_retry_on_failure():
    # Bot send failure retries once after 5s before logging error
    deduplicator.meta_set("briefing_last_date", "2026-10-14")

    fake_inputs = ([], [], [], {})
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)
        if len(sleep_calls) >= 3:
            raise asyncio.CancelledError()

    with (
        patch("src.utils.clock.now_ist", return_value=datetime(2026, 10, 15, 7, 15, tzinfo=IST)),
        patch("src.utils.clock.today_ist", return_value=datetime(2026, 10, 15).date()),
        patch("src.briefing.fetch_briefing_inputs", return_value=fake_inputs),
        patch("src.notify.bot.bot.send", side_effect=[Exception("Network Error 1"), MagicMock()]),
        patch("asyncio.sleep", side_effect=fake_sleep),
    ):
        with pytest.raises(asyncio.CancelledError):
            await guard(run_briefing())

        # Slept before target (0.0), then slept 5 seconds on retry
        assert 5 in sleep_calls
        assert deduplicator.meta_get("briefing_last_date") == "2026-10-15"


@pytest.mark.asyncio
async def test_heartbeat_interval():
    # Heartbeat logs immediately on start and writes timestamp to meta table
    with (
        patch("src.workspace.sheets_logger.sheets_logger.log_heartbeat") as mock_hb,
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
    ):
        with pytest.raises(asyncio.CancelledError):
            await guard(run_heartbeat())

        mock_hb.assert_called_once()
        ts = deduplicator.meta_get("last_heartbeat")
        assert ts is not None
        assert float(ts) > 0
