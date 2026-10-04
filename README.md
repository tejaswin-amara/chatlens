# ChatLens: SPARK PA Daemon

A headless Telegram to Google Workspace assistant ("SPARK PA daemon") designed for one KLEF student.

## Architecture

A Telethon user-account listener reads an allowlist of chats, classifies each message (regex first, Gemini only for the residual), then writes to Google Calendar, Tasks, and Sheets, and sends receipts to Saved Messages.

## Environment Variables
See `.env.example` for details.

| Variable | Description |
| -------- | ----------- |
| `TELEGRAM_API_ID` | Telegram API ID |
| `TELEGRAM_API_HASH` | Telegram API Hash |
| `TELEGRAM_SESSION_STRING` | Telegram Session String |
| `GOOGLE_CREDENTIALS_BASE64` | Base64-encoded Google Credentials JSON |
| `GOOGLE_CALENDAR_ID` | Google Calendar ID (default: primary) |
| `GOOGLE_SHEET_ID` | Google Sheet ID for audit logging |
| `GEMINI_API_KEY` | Gemini API Key |
| `GEMINI_MODEL` | Gemini Model (default: `gemini-3.5-flash-lite`) |
| `GEMINI_DAILY_BUDGET` | Daily limit for API calls (default: 50) |
| `SPARK_MODE` | Operating mode: `dry`, `confirm`, or `live` |
| `SPARK_CHAT_IDS` | Comma-separated list of allowed chat IDs |
| `SPARK_DB` | Path to SQLite DB (default: `spark.db`) |
| `SPARK_MEDIA` | Enable media processing (default: `false`) |
| `SPARK_TIMETABLE` | Path to timetable TOML file |
| `LOG_LEVEL` | Logging level (default: `INFO`) |
| `SENTRY_DSN` | Sentry DSN for error tracking (optional) |
| `BOT_TOKEN` | Telegram Bot token for notifications |
| `OWNER_CHAT_ID` | Chat ID of the owner for notifications |

## Setup

1. **Telegram Session**: Run `python scripts/generate_session.py` to get your `TELEGRAM_SESSION_STRING`.
2. **List Chats**: Run `python scripts/list_chats.py` to get IDs for `SPARK_CHAT_IDS`.
3. **Google Token**: Run `python scripts/google_token.py` to get your `GOOGLE_CREDENTIALS_BASE64`.

## Modes and Invariants

- `dry` (default): Classifies, validates, and audits, but makes no Calendar or Tasks writes.
- `confirm`: Requires the owner's ✅ for every write.
- `live`: Auto-writes only `ROOM_OVERRIDE` (regex-sourced & timetable-validated) and `TASK`/`EXAM_DEADLINE` (regex-sourced). Gemini-derived events and holidays always need confirmation.

*Free-tier note: Free Gemini API prompts may be used by Google to improve its products.*

## Academic Terms
For the T04 to T05 switch, replace `data/timetable_T04.toml` with the new timetable, and update `SPARK_TIMETABLE` in `.env`.

## Troubleshooting
Check the application logs for any errors. If a session expires, regenerate it.

---

## Legacy web app

The web app is a Flask/FastAPI based chat analyzer.

### Setup (Legacy)
Start via Docker:
```bash
docker compose -f chatlens-v2/docker-compose.yml up -d
```
The root `requirements.txt` is the legacy v1 list (the daemon installs with `pip install -e .`).
