# Security & Privacy Rules (ChatLens & SPARK PA)

## Privacy & Logging Standards
- **Zero PII in INFO Logs**: Student message content (`msg_text`), sender names (`sender_name`), and chat titles (`chat_title`) are strictly confined to `DEBUG` logs.
- **Log Scrubber**: Structlog processor `_scrub_secrets` scrubs all string keys matching bot tokens, Google API keys, GitHub tokens, and OpenAI keys across all log entries.
- **Sentry Guard**: `_sentry_before_send` strips PII from `event["extra"]` and redacts secret patterns from error values and messages before transmission.

## Ingestion Boundaries
- **Strictly Read-Only Telegram Ingestion**: Telethon client NEVER posts into groups or broadcast channels. Outbound communication is directed exclusively to the owner via the Telegram Bot API or Saved Messages (`"me"`).
- **Prompt Injection Defense**: Untrusted messages sent to Gemini are sanitized, stripped of PII tokens (`[EMAIL]`, `[URL]`, `[PHONE]`), and enclosed within `<telegram_message>` structural delimiters.
- **Mandatory Confirmation**: `HOLIDAY`, `CLASS_CANCELLED`, and all Gemini-derived events unconditionally require manual confirmation (`Decision.CONFIRM`) by the owner before any Calendar/Tasks write occurs.
