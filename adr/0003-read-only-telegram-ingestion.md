# ADR 0003: Read-Only Telegram Ingestion Guardrail

* Status: accepted
* Deciders: Autonomous Engineering Team, Privacy & Policy
* Date: 2026-10-15

## Context and Problem Statement
The SPARK PA daemon connects to an allowlist of university Telegram channels and student groups using Telethon (MTProto user client). Because user client sessions possess privileges to post, reply, forward, and modify messages in joined chats, any bug, unexpected loop, or unauthorized command could post automated notifications or internal error traces into university groups.

Posting into university groups violates university communication policies, causes student disturbance, and leaks private personal assistant metadata.

## Decision Drivers
* Zero risk of transmitting automated or debug messages into university groups and broadcast channels.
* Strict separation of user ingestion channel from the private assistant management channel.
* Robust fallback mechanisms for delivering actionable alerts exclusively to the owner.

## Considered Options
* Option 1: Bidirectional Telegram user client handling both message ingestion and interactive conversational replies in-place.
* Option 2: Strictly read-only ingestion via Telethon with completely decoupled unidirectional outbound reporting via a private Telegram Bot (`BOT_TOKEN` + `OWNER_CHAT_ID`) or Saved Messages (`"me"`).

## Decision Outcome
Chosen option: **Option 2**.

### Implementation Guarantees
1. Telethon `TelegramClient` is configured solely as an event listener across configured `SPARK_CHAT_IDS`.
2. Outbound interaction with the owner uses a private Telegram Bot via HTTPS requests to `https://api.telegram.org/bot<TOKEN>/...` directed solely to `OWNER_CHAT_ID`.
3. If the Telegram Bot is unconfigured, outbound delivery falls back exclusively to Telethon's private Saved Messages dialogue (`entity="me"`).
4. Calling `client.send_message()` to any group, supergroup, or channel ID is structurally forbidden across all codebase modules.

### Positive Consequences
* Absolute privacy and zero noise in university groups.
* Clear operational demarcation between observation and execution.

### Negative Consequences / Tradeoffs
* The assistant cannot directly answer peer inquiries in public groups (by design).

## Confirmation & Verification
* Invariant verified in unit and integration tests (`tests/test_handlers.py`, `tests/test_main.py`).
* Audit of all network calls and message sending paths confirms destinations are strictly `OWNER_CHAT_ID` or `"me"`.
