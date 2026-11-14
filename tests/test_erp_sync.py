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
    assert enriched["faculty"] in ("Anitha Chekuri", "Ms. Ch. Anitha")
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


def test_integer_scaled_attendance_arithmetic_boundaries():
    # 1. Exact distinction boundary: 17/20 = 85.0%
    # 100 * 17 >= 85 * 20 (1700 >= 1700) -> safe_bunks_85 = floor(0/85) = 0
    # safe_bunks_75 = floor((1700 - 75*20)/75) = floor(200/75) = 2
    r_dist = enrich_course_record({"conducted": 20, "attended": 17})
    assert r_dist["safe_bunks_85"] == 0
    assert r_dist["safe_bunks_75"] == 2
    assert r_dist["recovery_needed"] == 0

    # 2. Exact bunk floor boundary: 15/20 = 75.0%
    # 100 * 15 >= 75 * 20 (1500 >= 1500) -> safe_bunks_75 = floor(0/75) = 0
    # 100 * 15 < 85 * 20 (1500 < 1700) -> safe_bunks_85 = 0
    # recovery_needed = ceil((1700 - 1500)/15) = ceil(200/15) = 14
    r_floor = enrich_course_record({"conducted": 20, "attended": 15})
    assert r_floor["safe_bunks_85"] == 0
    assert r_floor["safe_bunks_75"] == 0
    assert r_floor["recovery_needed"] == 14

    # 3. Below bunk floor: 10/20 = 50.0%
    # safe_bunks_75 = 0, safe_bunks_85 = 0
    # recovery_needed = ceil((85*20 - 100*10)/15) = ceil(700/15) = 47
    r_low = enrich_course_record({"conducted": 20, "attended": 10})
    assert r_low["safe_bunks_85"] == 0
    assert r_low["safe_bunks_75"] == 0
    assert r_low["recovery_needed"] == 47

    # 4. Zero conducted classes edge case
    r_zero = enrich_course_record({"conducted": 0, "attended": 0})
    assert r_zero["safe_bunks_85"] == 0
    assert r_zero["safe_bunks_75"] == 0
    assert r_zero["recovery_needed"] == 0


@pytest.mark.asyncio
async def test_erp_sync_rate_pacing_400ms():
    agent = AcademicERPSyncAgent()
    settings.owner_chat_id = 99999
    settings.bot_token = "mock_token"

    sleep_calls = []

    async def mock_sleep(delay):
        sleep_calls.append(delay)

    with (
        patch("asyncio.sleep", side_effect=mock_sleep),
        patch("src.erp.client.klu_erp.get_attendance", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_marks", new_callable=AsyncMock, return_value=[]),
        patch("src.erp.client.klu_erp.get_exam_seating", new_callable=AsyncMock, return_value=[]),
    ):
        await agent.sync_once(send_alerts=False)
        # Exactly two 400ms sleeps between the three sequential ERP queries
        # (attendance -> marks -> seating)
        assert sleep_calls == [0.4, 0.4]


def test_is_daytime_academic_hours():
    from src.erp.sync import is_daytime_academic_hours

    # Monday 10:00 AM IST -> True
    mon_morning = datetime(2026, 11, 9, 10, 0, tzinfo=clock.IST)
    assert is_daytime_academic_hours(mon_morning) is True

    # Monday 06:59 AM IST -> False (before 07:00)
    mon_early = datetime(2026, 11, 9, 6, 59, tzinfo=clock.IST)
    assert is_daytime_academic_hours(mon_early) is False

    # Monday 18:01 PM IST -> False (after 18:00)
    mon_evening = datetime(2026, 11, 9, 18, 1, tzinfo=clock.IST)
    assert is_daytime_academic_hours(mon_evening) is False

    # Sunday 12:00 PM IST -> False (Sunday excluded)
    sun_noon = datetime(2026, 11, 15, 12, 0, tzinfo=clock.IST)
    assert is_daytime_academic_hours(sun_noon) is False


@pytest.mark.asyncio
async def test_erp_keep_alive_ping_success():
    import httpx
    from pydantic import SecretStr

    from src.erp.client import klu_erp
    from src.erp.sync import erp_keep_alive_ping

    settings.erp_username = "test_user"
    settings.erp_password = SecretStr("test_pass")
    klu_erp._cookies = {"PHPSESSID": "mock_valid_session"}

    async def mock_get(url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(200, request=req, text="<div>Welcome Student</div>")

    mock_client = AsyncMock()
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(klu_erp, "_get_http_client", return_value=mock_client):
        result = await erp_keep_alive_ping()
        assert result is True
        ts = deduplicator.meta_get("last_erp_keep_alive_ts")
        assert ts is not None and float(ts) > 0


@pytest.mark.asyncio
async def test_erp_keep_alive_ping_expired_triggers_login():
    import httpx
    from pydantic import SecretStr

    from src.erp.client import klu_erp
    from src.erp.sync import erp_keep_alive_ping

    settings.erp_username = "test_user"
    settings.erp_password = SecretStr("test_pass")
    klu_erp._cookies = {"PHPSESSID": "expired_session"}

    async def mock_get(url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            text='<form id="login-form"><input id="loginform-username"/></form>',
        )

    mock_client = AsyncMock()
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(klu_erp, "_get_http_client", return_value=mock_client),
        patch.object(klu_erp, "login", new_callable=AsyncMock, return_value=True) as mock_login,
    ):
        result = await erp_keep_alive_ping()
        assert result is True
        mock_login.assert_called_once()


@pytest.mark.asyncio
async def test_run_erp_keep_alive_lifecycle():
    import asyncio

    from src.erp.sync import run_erp_keep_alive

    stop_event = asyncio.Event()

    ping_calls = 0

    async def fake_ping():
        nonlocal ping_calls
        ping_calls += 1
        return True

    with (
        patch("src.erp.sync.is_daytime_academic_hours", return_value=True),
        patch("src.erp.sync.erp_keep_alive_ping", side_effect=fake_ping),
    ):
        task = asyncio.create_task(run_erp_keep_alive(stop_event))
        # Yield control so loop runs first iteration
        await asyncio.sleep(0.05)
        stop_event.set()
        await task
        assert ping_calls >= 1


def test_format_attendance_delta_alert_hard_detention():
    from src.erp.sync import format_attendance_delta_alert

    deltas = [
        {
            "course_name": "Machine Learning",
            "course_code": "25SC2107E",
            "ltps": "Practical",
            "conducted": 30,
            "attended": 18,
            "percentage": 60.0,
            "diff_summary": "🔴 **+1 absence recorded**",
            "safe_bunks_85": 0,
            "safe_bunks_75": 0,
            "recovery_needed": 34,
            "remaining_classes": 12,
            "hard_detention": True,
        }
    ]
    now_dt = datetime(2026, 11, 9, 13, 15, tzinfo=clock.IST)
    alert = format_attendance_delta_alert(deltas, now_dt)
    assert "HARD DETENTION LOCKOUT" in alert
    assert "34 classes" in alert
    assert "12 classes" in alert


@pytest.mark.asyncio
async def test_sync_once_emits_outbox_events(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_spark.db")
    monkeypatch.setattr(settings, "spark_db", db_file)
    monkeypatch.setattr(settings, "owner_chat_id", 99999)
    monkeypatch.setattr(settings, "bot_token", "mock_token")

    agent = AcademicERPSyncAgent()

    # Prior attendance cache
    prior_att = [
        {
            "course_code": "25CS3112E",
            "course_name": "DLAC",
            "ltps": "S",
            "conducted": 10,
            "attended": 10,
            "percentage": 100.0,
        }
    ]
    deduplicator.meta_set("erp_attendance_cache", json.dumps(prior_att))

    # New attendance: 1 new class attended
    new_att = [
        {
            "course_code": "25CS3112E",
            "course_name": "DLAC",
            "ltps": "S",
            "conducted": 11,
            "attended": 11,
            "percentage": 100.0,
        }
    ]

    # Prior marks cache
    prior_marks = [
        {
            "course_code": "25CS3112E",
            "component": "Mid-Term 1",
            "secured_marks": 25.0,
            "max_marks": 30.0,
        }
    ]
    deduplicator.meta_set("erp_marks_cache", json.dumps(prior_marks))

    # New marks: Mid-Term 2 published
    new_marks = prior_marks + [
        {
            "course_code": "25CS3112E",
            "component": "Mid-Term 2",
            "secured_marks": 28.0,
            "max_marks": 30.0,
            "percentage": 93.33,
        }
    ]

    with (
        patch(
            "src.erp.client.klu_erp.get_attendance",
            new_callable=AsyncMock,
            return_value=new_att,
        ),
        patch(
            "src.erp.client.klu_erp.get_marks",
            new_callable=AsyncMock,
            return_value=new_marks,
        ),
        patch(
            "src.erp.client.klu_erp.get_exam_seating",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch("src.notify.bot.bot.send"),
    ):
        res = await agent.sync_once(send_alerts=False)
        assert res["attendance_deltas"] == 1
        assert res["marks_deltas"] == 1

        events = deduplicator.list_outbox_events(limit=10, unprocessed_only=False)
        event_types = [e["event_type"] for e in events]
        assert "erp.attendance_update" in event_types
        assert "erp.marks_update" in event_types

        att_event = next(e for e in events if e["event_type"] == "erp.attendance_update")
        payload = att_event["payload"]
        assert payload["deltas_count"] == 1
        assert payload["deltas"][0]["course_code"] == "25CS3112E"
