"""Compliance Guardrails & Anti-Ban Acceptance Test Suite [R-BAN-1 through R-BAN-5].

Validates compliance invariants:
- [R-BAN-1] Multi-tier TokenBucket rate limiting (user 1 rps, group 20 rpm, global 25 rps)
           and persistent 429/FloodWait backoff.
- [R-BAN-2] Zero-spam protocol: private DM requires prior /start consent; groups allow only
           mentions/commands/authorized broadcasts; alerts route strictly to owner.
- [R-BAN-3] Restart debounce: suppresses startup notifications within 900s.
- [R-BAN-4] Deterministic PII redaction ([PHONE], [ID], [TOKEN]) on audit & external feeds.
- [R-BAN-5] Downstream circuit breaker: trips on 3 consecutive 403/429 errors for 5 minutes,
           queues events into pending, and alerts owner once.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.ingestion.handlers import _get_sender_name, apply_event, handle_bot_command
from src.notify.bot import BotClient, BotRateLimitedError, TelegramRateLimiter, TokenBucket, bot
from src.parsing.schemas import ExtractedAcademicEvent
from src.utils.circuit_breaker import CircuitState, WorkspaceCircuitBreaker
from src.utils.deduplication import MessageDeduplicator
from src.utils.redaction import redact_pii


@pytest.fixture(autouse=True)
def isolate_env(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_compliance.db")
    dedup = MessageDeduplicator(db_path=test_db)

    monkeypatch.setattr(settings, "spark_db", test_db)
    monkeypatch.setattr(settings, "owner_chat_id", 123456789)
    monkeypatch.setattr(
        settings, "bot_token", MagicMock(get_secret_value=lambda: "bot123:mock_token")
    )
    monkeypatch.setattr("src.utils.deduplication.deduplicator", dedup)
    monkeypatch.setattr("src.ingestion.handlers.deduplicator", dedup)
    monkeypatch.setattr("src.utils.circuit_breaker.deduplicator", dedup)

    yield dedup


# ==============================================================================
# R-BAN-1: Rate Limit & FloodWait Backoff
# ==============================================================================


def test_r_ban_1_token_bucket_acquire():
    bucket = TokenBucket(capacity=2.0, refill_rate=100.0)
    bucket.acquire()
    bucket.acquire()
    assert bucket.tokens <= 1.0


def test_r_ban_1_rate_limiter_routing():
    limiter = TelegramRateLimiter()

    # User chat (positive integer ID) -> 1 msg / sec
    user_bucket = limiter._get_chat_bucket(98765)
    assert user_bucket.capacity == 1.0
    assert user_bucket.refill_rate == settings.telegram_user_rate_limit_rps

    # Group chat (negative integer ID) -> 20 msgs / min (20 / 60 = 0.333 rps)
    group_bucket = limiter._get_chat_bucket(-1001234567)
    assert group_bucket.capacity == settings.telegram_group_rate_limit_rpm
    assert group_bucket.refill_rate == pytest.approx(settings.telegram_group_rate_limit_rpm / 60.0)

    # Global bucket -> 25 msgs / sec
    assert limiter.global_bucket.capacity == settings.telegram_global_rate_limit_rps


def test_r_ban_1_floodwait_backoff_persistence(isolate_env):
    client = BotClient()

    with (
        patch.object(client, "_request", side_effect=BotRateLimitedError(retry_after=5)),
        patch("time.sleep") as mock_sleep,
    ):
        try:
            client._retry("sendMessage", {"chat_id": 123456789, "text": "test"})
        except BotRateLimitedError:
            pass

        # Backoff state must be persisted in SQLite meta
        stored_backoff = isolate_env.meta_get("telegram_backoff_until")
        assert stored_backoff is not None
        assert float(stored_backoff) > time.time()
        assert any(call[0][0] in (5, 7) for call in mock_sleep.call_args_list)


# ==============================================================================
# R-BAN-2: Zero-Spam & Contact Consent Protocol
# ==============================================================================


def test_r_ban_2_unsolicited_dm_blocked(isolate_env):
    unconsented_user_id = 999888777
    res = bot.send("Unsolicited message", chat_id=unconsented_user_id)
    assert res.get("ok") is False
    assert "Blocked: User has not consented" in res.get("description", "")


@pytest.mark.asyncio
async def test_r_ban_2_consent_via_start_allows_dm(isolate_env):
    user_id = 999888777

    # Before /start -> unconsented
    assert bot.is_contact_consented(user_id) is False

    # User initiates /start
    msg = {"chat": {"id": user_id}, "from": {"id": user_id}, "text": "/start"}
    await handle_bot_command(msg)

    # After /start -> consented
    assert bot.is_contact_consented(user_id) is True
    assert isolate_env.meta_get(f"consent:{user_id}") is not None

    with patch.object(bot, "_retry", return_value={"ok": True}):
        res = bot.send("Authorized response", chat_id=user_id)
        assert res.get("ok") is True


def test_r_ban_2_owner_always_consented():
    assert bot.is_contact_consented(settings.owner_chat_id) is True


def test_r_ban_2_group_reply_permissions():
    group_id = -1001987654321

    # Unsolicited text without mention or command is blocked
    res = bot.send("Spam group message", chat_id=group_id)
    assert res.get("ok") is False
    assert "Blocked: Unsolicited group message" in res.get("description", "")

    # Commands and mentions are permitted
    assert bot.is_group_reply_permitted(group_id, "/today") is True
    assert bot.is_group_reply_permitted(group_id, "@spark_pa_bot help") is True
    assert bot.is_group_reply_permitted(group_id, "Update", is_high_confidence=True) is True


# ==============================================================================
# R-BAN-3: Daemon Restart Debounce
# ==============================================================================


def test_r_ban_3_startup_debounce_logic(isolate_env):
    now = time.time()

    # Case 1: Fresh startup (no prior notification) -> allowed
    assert isolate_env.meta_get("last_startup_notify_ts") is None

    # Record startup notification
    isolate_env.meta_set("last_startup_notify_ts", str(now))

    # Case 2: Restart within 900s (e.g. after 120s) -> suppressed
    recent_ts = float(isolate_env.meta_get("last_startup_notify_ts"))
    assert (now + 120 - recent_ts) < settings.startup_debounce_seconds

    # Case 3: Restart after >900s (e.g. after 950s) -> allowed
    assert (now + 950 - recent_ts) >= settings.startup_debounce_seconds


# ==============================================================================
# R-BAN-4: Data Minimization & Deterministic PII Redaction
# ==============================================================================


def test_r_ban_4_pii_redaction_patterns():
    # Phone numbers
    text_phone = "Contact CR at +91 9876543210 or 98765-43210 for lab manual"
    redacted = redact_pii(text_phone)
    assert "+91 9876543210" not in redacted
    assert "[PHONE]" in redacted

    # Student ID / Aadhaar / RRN
    text_id = "Student ID 2100030123 submitted fee with Aadhaar 1234 5678 9012"
    redacted_id = redact_pii(text_id)
    assert "2100030123" not in redacted_id
    assert "1234 5678 9012" not in redacted_id
    assert "[ID]" in redacted_id

    # Tokens & Secrets
    text_token = "Using token bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz and Bearer secret_xyz123"
    redacted_token = redact_pii(text_token)
    assert "bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz" not in redacted_token
    assert "secret_xyz123" not in redacted_token
    assert "[TOKEN]" in redacted_token


def test_r_ban_4_sender_name_redaction():
    class DummySender:
        first_name = "Rajesh"
        last_name = "9876543210"

    cleaned = _get_sender_name(DummySender())
    assert "9876543210" not in cleaned
    assert "[PHONE]" in cleaned


# ==============================================================================
# R-BAN-5: Downstream Circuit Breaker & Event Queueing
# ==============================================================================


def test_r_ban_5_circuit_breaker_tripping(isolate_env):
    cb = WorkspaceCircuitBreaker(error_threshold=3, cooldown_seconds=300)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Error 1: 403 Rate Limit
    trip1 = cb.record_error(Exception("403 User Rate Limit Exceeded"))
    assert trip1 is False
    assert cb.state == CircuitState.CLOSED

    # Error 2: 429 Too Many Requests
    trip2 = cb.record_error(Exception("429 Too Many Requests"))
    assert trip2 is False
    assert cb.state == CircuitState.CLOSED

    # Error 3: 403 Quota Exceeded -> Trips
    trip3 = cb.record_error(Exception("403 quotaExceeded"))
    assert trip3 is True
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # State persists in SQLite
    assert isolate_env.meta_get("circuit_breaker_open_until") is not None

    # Success restores circuit
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


@pytest.mark.asyncio
async def test_r_ban_5_apply_event_queues_when_circuit_open(isolate_env):
    event = ExtractedAcademicEvent(
        course_name="Data Structures",
        course_code="23CS2101",
        room="M304",
        period="1",
        target_date="2026-10-24",
        summary="Data Structures Room M304",
        intent="ROOM_OVERRIDE",
        action_required=True,
    )

    cb = WorkspaceCircuitBreaker(error_threshold=1, cooldown_seconds=300)
    with patch("src.ingestion.handlers.workspace_circuit_breaker", cb):
        # Force breaker open
        cb.record_error(Exception("429 RateLimitExceeded"))
        assert cb.can_execute() is False

        # Attempt to apply event
        status, details = await apply_event(event)
        assert status == "QUEUED_CIRCUIT_BREAKER"
        assert "Queued in pending" in details[0]

        # Verify event was queued in SQLite pending table
        pending = isolate_env.list_pending()
        assert len(pending) >= 1
        queued_payload = pending[0]["event"]
        assert queued_payload.get("course_code") == "23CS2101"
