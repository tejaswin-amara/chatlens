"""Tests for /bunk, /briefing, and margin calculation commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.config import settings
from src.ingestion.handlers import handle_bot_command


@pytest.mark.asyncio
async def test_bunk_command(monkeypatch):
    """Verify /bunk calculates margins from ERP attendance."""
    monkeypatch.setattr(settings, "owner_chat_id", 12345)
    monkeypatch.setattr(settings, "bot_token", "test_bot_token")

    fake_records = [
        {
            "course_name": "Data Structures & Algorithms-3",
            "course_code": "25CS2103E",
            "attended": 18,
            "conducted": 20,
            "percentage": 90.0,
            "safe_bunks": 4,
            "recovery_needed": 0,
        },
        {
            "course_name": "Machine Learning",
            "course_code": "25SC2107E",
            "attended": 14,
            "conducted": 20,
            "percentage": 70.0,
            "safe_bunks": 0,
            "recovery_needed": 4,
        },
    ]

    bot_sends = []
    with (
        patch("src.erp.klu_erp.get_attendance", new_callable=AsyncMock) as mock_get_att,
        patch("src.notify.bot.bot.send", side_effect=bot_sends.append),
    ):
        mock_get_att.return_value = fake_records

        await handle_bot_command({"chat": {"id": 12345}, "text": "/bunk"})

        assert len(bot_sends) >= 2
        # First send is progress
        assert "Calculating attendance bunk margins" in bot_sends[0]
        # Second send is the calculated output
        result = bot_sends[1]
        assert "Bunk Margin Calculator" in result
        assert "25CS2103E" in result
        assert "Safe bunks (≥75%): **4**" in result
        assert "25SC2107E" in result
        assert "Attend next: **4** classes" in result


@pytest.mark.asyncio
async def test_briefing_command(monkeypatch):
    """Verify /briefing compiles and returns today's academic briefing."""
    monkeypatch.setattr(settings, "owner_chat_id", 12345)
    monkeypatch.setattr(settings, "bot_token", "test_bot_token")

    bot_sends = []
    fake_inputs = ([], [], [], {})

    with (
        patch(
            "src.briefing.fetch_briefing_inputs",
            new_callable=AsyncMock,
            return_value=fake_inputs,
        ),
        patch("src.notify.bot.bot.send", side_effect=bot_sends.append),
    ):
        await handle_bot_command({"chat": {"id": 12345}, "text": "/briefing"})

        assert len(bot_sends) >= 2
        assert "Compiling today's academic briefing" in bot_sends[0]
        assert "Today's Classes" in bot_sends[1]


def test_simulate_bunk_impact_scenarios():
    """Verify simulate_bunk_impact detects safe bunks, breaches, and missing courses."""
    from src.briefing import simulate_bunk_impact

    records = [
        {
            "course_name": "Cloud Infrastructure And Services",
            "course_code": "25CS2206E",
            "attended": 18,
            "conducted": 20,
        },
        {
            "course_name": "Deep Learning With Accelerated Computing",
            "course_code": "25CS3112E",
            "attended": 15,
            "conducted": 20,
        },
    ]

    # Safe bunk (18/20 = 90% -> 18/21 = 85.7% >= 75%)
    res_safe = simulate_bunk_impact(records, "CIS", skip_count=1)
    assert "Attendance Bunk Simulation (1 class)" in res_safe
    assert "25CS2206E" in res_safe
    assert "90.0%" in res_safe
    assert "85.7%" in res_safe
    assert "Safe Bunk Confirmed" in res_safe

    # Critical breach (15/20 = 75% -> 15/21 = 71.4% < 75%)
    res_breach = simulate_bunk_impact(records, "DLAC", skip_count=1)
    assert "CRITICAL DETENTION THRESHOLD BREACH!" in res_breach
    assert "71.4%" in res_breach

    # Unknown course
    res_unknown = simulate_bunk_impact(records, "NON_EXISTENT")
    assert "not found in attendance records" in res_unknown


def test_detect_high_stakes_classes():
    """Verify detect_high_stakes_classes flags courses in the 75-78% window
    or single-absence breach.
    """
    from datetime import date
    from unittest.mock import MagicMock, patch

    from src.briefing import detect_high_stakes_classes

    # Course at 15/20 = 75.0% (single absence drops it to 15/21 = 71.4%)
    records = [
        {
            "course_name": "Cloud Infrastructure And Services",
            "course_code": "25CS2206E",
            "attended": 15,
            "conducted": 20,
        },
        {
            "course_name": "Deep Learning With Accelerated Computing",
            "course_code": "25CS3112E",
            "attended": 20,
            "conducted": 20,
        },
    ]

    fake_slot = MagicMock()
    fake_slot.course = "CIS"
    fake_slot.course_code = "25CS2206E"
    fake_slot.period = 3
    fake_slot.room = "HC-15C"
    fake_slot.faculty = "Dr. Divya"

    with patch("src.timetable.get_effective_slots", return_value=[fake_slot]):
        hs = detect_high_stakes_classes(date(2026, 10, 23), records)
        assert len(hs) == 1
        assert hs[0]["code"] == "25CS2206E"
        assert hs[0]["current_pct"] == 75.0
        assert hs[0]["projected_pct"] == 71.4
        assert hs[0]["danger"] is True


@pytest.mark.asyncio
async def test_bunk_simulation_command(monkeypatch):
    """Verify /bunk <course> [count] dispatches simulation."""
    monkeypatch.setattr(settings, "owner_chat_id", 12345)
    monkeypatch.setattr(settings, "bot_token", "test_bot_token")

    fake_records = [
        {
            "course_name": "Cloud Infrastructure And Services",
            "course_code": "25CS2206E",
            "attended": 15,
            "conducted": 20,
        }
    ]

    bot_sends = []
    with (
        patch("src.erp.klu_erp.get_attendance", new_callable=AsyncMock) as mock_get_att,
        patch("src.notify.bot.bot.send", side_effect=bot_sends.append),
    ):
        mock_get_att.return_value = fake_records

        await handle_bot_command({"chat": {"id": 12345}, "text": "/bunk CIS 2"})

        assert len(bot_sends) >= 2
        sim_output = bot_sends[1]
        assert "Attendance Bunk Simulation (2 classes)" in sim_output
        assert "25CS2206E" in sim_output
        assert "CRITICAL DETENTION THRESHOLD BREACH!" in sim_output


@pytest.mark.asyncio
async def test_fee_download_command(monkeypatch, tmp_path):
    """Verify /fee download <order_id> downloads and confirms file save."""
    monkeypatch.setattr(settings, "owner_chat_id", 12345)
    monkeypatch.setattr(settings, "bot_token", "test_bot_token")

    bot_sends = []
    fake_pdf = b"%PDF-1.4 Mock Fee Receipt Content"

    with (
        patch(
            "src.erp.klu_erp.download_fee_receipt",
            new_callable=AsyncMock,
            return_value=fake_pdf,
        ) as mock_dl,
        patch("src.notify.bot.bot.send", side_effect=bot_sends.append),
    ):
        await handle_bot_command({"chat": {"id": 12345}, "text": "/fee download 987654"})

        mock_dl.assert_called_once_with("987654")
        assert len(bot_sends) >= 2
        assert "Downloading fee receipt for Order `987654`" in bot_sends[0]
        assert "Fee Receipt Downloaded" in bot_sends[1]
        assert "Order ID: `987654`" in bot_sends[1]
        assert f"{len(fake_pdf)} bytes" in bot_sends[1]
