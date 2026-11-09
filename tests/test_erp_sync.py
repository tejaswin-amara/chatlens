"""Comprehensive test suite for the Autonomous Academic ERP Sync Agent."""

import json
from datetime import datetime, time, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.config import settings
from src.erp.sync import (
    AcademicERPSyncAgent,
    enrich_course_record,
    format_attendance_delta_alert,
    next_sync_run,
)
from src.utils import clock
from src.utils.deduplication import deduplicator


def test_next_sync_run_mon_morning():
    # Monday 06:00 IST -> Expected next run: Monday 07:15 IST
    # 2026-11-09 is a Monday
    now = datetime(2026, 11, 9, 6, 0, tzinfo=clock.IST)
    nxt = next_sync_run(now)
    assert nxt.date() == now.date()
    assert nxt.time() == time(7, 15)


def test_next_sync_run_midday():
    # Monday 08:00 IST -> Expected next run: Monday 13:15 IST
    now = datetime(2026, 11, 9, 8, 0, tzinfo=clock.IST)
    nxt = next_sync_run(now)
    assert nxt.date() == now.date()
    assert nxt.time() == time(13, 15)


def test_next_sync_run_evening_wrapup():
    # Monday 14:00 IST -> Expected next run: Monday 17:15 IST
    now = datetime(2026, 11, 9, 14, 0, tzinfo=clock.IST)
    nxt = next_sync_run(now)
    assert nxt.date() == now.date()
    assert nxt.time() == time(17, 15)


def test_next_sync_run_post_evening_next_day():
    # Monday 18:00 IST -> Expected next run: Tuesday 07:15 IST
    now = datetime(2026, 11, 9, 18, 0, tzinfo=clock.IST)
    nxt = next_sync_run(now)
    assert nxt.date() == now.date() + timedelta(days=1)
    assert nxt.time() == time(7, 15)


def test_next_sync_run_saturday_night_skips_sunday():
    # 2026-11-14 is Saturday
    sat_night = datetime(2026, 11, 14, 18, 0, tzinfo=clock.IST)
    nxt = next_sync_run(sat_night)
    # 2026-11-16 is Monday (skipping Sunday 2026-11-15)
    assert nxt.date() == sat_night.date() + timedelta(days=2)
    assert nxt.weekday() == 0  # Monday
    assert nxt.time() == time(7, 15)


def test_enrich_course_record_cluster_4():
    raw_record = {
        "course_code": "25CS3112E",
        "course_name": "",
        "ltps": "S",
        "section": "",
        "conducted": 10,
        "attended": 10,
        "percentage": 100.0,
    }
    enriched = enrich_course_record(raw_record)
    assert enriched["course_name"] == "Deep Learning With Accelerated Computing"
    assert enriched["category"] == "PCC"
    assert enriched["faculty"] == "Ms. Ch. Anitha"
    assert enriched["section"] == "S-10"
    assert enriched["safe_bunks_85"] == 1
    assert enriched["safe_bunks_75"] == 3
    assert enriched["recovery_needed"] == 0


def test_enrich_course_record_low_attendance():
    raw_record = {
        "course_code": "25CS2208E",
        "course_name": "",
        "ltps": "L",
        "section": "",
        "conducted": 4,
        "attended": 2,
        "percentage": 50.0,
    }
    enriched = enrich_course_record(raw_record)
    assert enriched["course_name"] == "Computer Networks And Network Programming"
    assert enriched["safe_bunks_85"] == 0
    assert enriched["safe_bunks_75"] == 0
    # Needs (0.85 * 4 - 2) / 0.15 = 1.4 / 0.15 = 9.33 -> 10 classes
    assert enriched["recovery_needed"] == 10


def test_format_attendance_delta_alert():
    deltas = [
        {
            "course_name": "Deep Learning With Accelerated Computing",
            "course_code": "25CS3112E",
            "ltps": "Skill",
            "conducted": 5,
            "attended": 5,
            "percentage": 100.0,
            "diff_summary": "🟢 **+1 class attended**",
            "safe_bunks_85": 1,
            "safe_bunks_75": 2,
            "recovery_needed": 0,
        }
    ]
    now_dt = datetime(2026, 11, 9, 13, 15, tzinfo=clock.IST)
    alert = format_attendance_delta_alert(deltas, now_dt)
    assert "Attendance Update Detected (KL ERP — Y25 T05)" in alert
    assert "Deep Learning With Accelerated Computing" in alert
    assert "25CS3112E" in alert
    assert "+1 class attended" in alert
    assert "1 safe bunks" in alert


@pytest.mark.asyncio
async def test_sync_once_baseline_populates_cache_without_spam(monkeypatch):
    agent = AcademicERPSyncAgent()
    settings.owner_chat_id = 99999
    settings.bot_token = "mock_token"

    # Clear previous cache
    deduplicator.meta_set("erp_attendance_cache", "")

    sample_att = [
        {
            "course_code": "25CS3112E",
            "course_name": "DLAC",
            "ltps": "S",
            "conducted": 4,
            "attended": 4,
            "percentage": 100.0,
        }
    ]

    dispatched_alerts = []

    with (
        patch(
            "src.erp.client.klu_erp.get_attendance", new_callable=AsyncMock, return_value=sample_att
        ),
        patch("src.erp.client.klu_erp.get_marks", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_exam_seating", new_callable=AsyncMock, return_value=[]),
        patch(
            "src.notify.bot.bot.send", side_effect=lambda text, **kw: dispatched_alerts.append(text)
        ),
    ):
        result = await agent.sync_once(send_alerts=True)
        assert result["success"] is True
        assert result["attendance_deltas"] == 0
        assert len(dispatched_alerts) == 0  # No alert on baseline population

        cached = deduplicator.meta_get("erp_attendance_cache")
        assert cached is not None
        assert "25CS3112E" in cached


@pytest.mark.asyncio
async def test_sync_once_delta_triggers_alert(monkeypatch):
    agent = AcademicERPSyncAgent()
    settings.owner_chat_id = 99999
    settings.bot_token = "mock_token"

    # Set prior baseline cache
    prior_cache = [
        {
            "course_code": "25CS3112E",
            "course_name": "Deep Learning With Accelerated Computing",
            "ltps": "S",
            "conducted": 4,
            "attended": 4,
            "percentage": 100.0,
        }
    ]
    deduplicator.meta_set("erp_attendance_cache", json.dumps(prior_cache))

    # New scrape has +1 attended class
    new_att = [
        {
            "course_code": "25CS3112E",
            "course_name": "Deep Learning With Accelerated Computing",
            "ltps": "S",
            "conducted": 5,
            "attended": 5,
            "percentage": 100.0,
        }
    ]

    dispatched_alerts = []

    with (
        patch(
            "src.erp.client.klu_erp.get_attendance", new_callable=AsyncMock, return_value=new_att
        ),
        patch("src.erp.client.klu_erp.get_marks", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_exam_seating", new_callable=AsyncMock, return_value=[]),
        patch(
            "src.notify.bot.bot.send", side_effect=lambda text, **kw: dispatched_alerts.append(text)
        ),
    ):
        result = await agent.sync_once(send_alerts=True)
        assert result["success"] is True
        assert result["attendance_deltas"] == 1
        assert len(dispatched_alerts) == 1
        assert "+1 class attended" in dispatched_alerts[0]


@pytest.mark.asyncio
async def test_sync_once_absence_delta_triggers_recovery_alert(monkeypatch):
    agent = AcademicERPSyncAgent()
    settings.owner_chat_id = 99999
    settings.bot_token = "mock_token"

    prior_cache = [
        {
            "course_code": "25CS2206E",
            "course_name": "Cloud Infrastructure And Services",
            "ltps": "S",
            "conducted": 3,
            "attended": 2,
            "percentage": 66.67,
        }
    ]
    deduplicator.meta_set("erp_attendance_cache", json.dumps(prior_cache))

    # New scrape: class conducted, but absent (attended stayed 2, conducted became 4)
    new_att = [
        {
            "course_code": "25CS2206E",
            "course_name": "Cloud Infrastructure And Services",
            "ltps": "S",
            "conducted": 4,
            "attended": 2,
            "percentage": 50.0,
        }
    ]

    dispatched_alerts = []

    with (
        patch(
            "src.erp.client.klu_erp.get_attendance", new_callable=AsyncMock, return_value=new_att
        ),
        patch("src.erp.client.klu_erp.get_marks", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_exam_seating", new_callable=AsyncMock, return_value=[]),
        patch(
            "src.notify.bot.bot.send", side_effect=lambda text, **kw: dispatched_alerts.append(text)
        ),
    ):
        result = await agent.sync_once(send_alerts=True)
        assert result["success"] is True
        assert result["attendance_deltas"] == 1
        assert len(dispatched_alerts) == 1
        assert "absence recorded" in dispatched_alerts[0]
        assert "Recovery" in dispatched_alerts[0]


@pytest.mark.asyncio
async def test_sync_once_network_timeout_leaves_cache_intact():
    agent = AcademicERPSyncAgent()
    prior_cache = [{"course_code": "25CS3112E", "attended": 4, "conducted": 4}]
    deduplicator.meta_set("erp_attendance_cache", json.dumps(prior_cache))

    with (
        patch(
            "src.erp.client.klu_erp.get_attendance",
            new_callable=AsyncMock,
            side_effect=TimeoutError("ERP Gateway 504"),
        ),
        patch("src.erp.client.klu_erp.get_marks", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_exam_seating", new_callable=AsyncMock, return_value=[]),
    ):
        result = await agent.sync_once(send_alerts=True)
        # Does not crash, records error
        assert "attendance_error" in result
        # Cache is intact
        cached = json.loads(deduplicator.meta_get("erp_attendance_cache"))
        assert len(cached) == 1
        assert cached[0]["course_code"] == "25CS3112E"


@pytest.mark.asyncio
async def test_handle_bot_command_sync():
    from src.ingestion.handlers import handle_bot_command
    from src.notify.bot import bot

    settings.owner_chat_id = 12345
    sent = []

    mock_sync_result = {
        "success": True,
        "attendance_deltas": 0,
        "marks_deltas": 0,
        "seating_deltas": 0,
    }

    with (
        patch(
            "src.erp.sync.erp_sync_agent.sync_once",
            new_callable=AsyncMock,
            return_value=mock_sync_result,
        ),
        patch.object(bot, "send", side_effect=lambda text, **kw: sent.append(text)),
    ):
        await handle_bot_command(
            {
                "chat": {"id": 12345},
                "from": {"id": 12345},
                "text": "/sync",
            }
        )

        assert len(sent) == 2
        assert "Starting on-demand KLU ERP synchronization" in sent[0]
        assert "ERP Sync Complete" in sent[1]
        assert "No new deltas detected" in sent[1]
