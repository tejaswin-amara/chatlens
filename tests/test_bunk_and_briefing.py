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
