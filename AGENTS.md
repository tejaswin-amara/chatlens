# AGENTS.md — SPARK PA daemon (`src/`)

## What this is
Headless Telegram → Google Workspace assistant for one KLEF student (IST, `Asia/Kolkata`).
Entry point: `python -m src.main`. A read-only Telethon listener watches an allowlist of chats,
classifies each message (regex first, Gemini only for the residual), validates room changes against
the timetable, then writes to Google Calendar, Tasks and Sheets and reports to the owner through a
Telegram bot.

Legacy, do not modify unless a task says so: `chatlens/` (v1 Flask app), `chatlens-v2/` (web app),
root `requirements.txt` (v1 only), `_next/`, `docs/`, `index.html`, `.nojekyll`, `scratch/`.
`data/calendar_2026_27.toml` is verified against the official PDF: read it, never edit it.

## Commands
- Setup: `pip install -e ".[dev]"` (Python 3.12 or newer)
- Test: `python -m pytest -q`
- Lint: `ruff check src tests scripts`
- Types: `mypy src`

## Invariants (target behavior; each task prompt says which parts already exist)
1. Telegram is read-only. Never send into groups or channels. Output goes only to Saved Messages
   (`"me"`) or to the owner through the bot.
2. `SPARK_MODE`:
   - `dry` (default): classify, validate and audit; no Calendar or Tasks writes.
   - `confirm`: every write needs the owner's ✅ in the bot.
   - `live`: auto-write only ROOM_OVERRIDE (regex-sourced and timetable-validated) and
     TASK/EXAM_DEADLINE (regex-sourced). Gemini-derived events, HOLIDAY and CLASS_CANCELLED always
     need ✅, in every mode.
3. Only chats listed in `SPARK_CHAT_IDS` are processed. An empty allowlist refuses to start.
4. No secrets in code, logs or fixtures. Message text, sender names and chat titles appear only in
   DEBUG logs; INFO logs carry ids, intent, status and latency.
5. All dates and times are IST. Telegram messages never change academic-calendar dates (exams, last
   instruction day, detention list, fee deadlines); conflicts are flagged, not applied.
6. Tests never touch the network, Telegram, Google or Gemini. Mock at the adapter boundary, as in
   `tests/test_handlers.py`. No network call at import time.
7. Never reintroduce Google Keep (enterprise-only API) or any Postgres, Celery or Redis dependency
   into the daemon.
8. Exit codes: 0 = clean shutdown; 2 = unrecoverable configuration or authentication error (the
   process manager must not restart it); anything else = crash, safe to restart. A configuration
   validation failure exits 2.
9. Gemini: the model name comes only from `GEMINI_MODEL` (default `gemini-3.5-flash-lite`). Never
   default to a `gemini-2.x` model. Do not pass `temperature`, `top_p` or `top_k` (deprecated for
   current models). One message per call, redacted, counted against `GEMINI_DAILY_BUDGET`, media
   only when `SPARK_MEDIA` is true. A 4xx or quota error is never retried.
10. Every write path is idempotent and records prior state so `/undo` can revert it.

## Environment variables
`TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION_STRING`, `GOOGLE_CREDENTIALS_BASE64`,
`GOOGLE_CALENDAR_ID`, `GOOGLE_SHEET_ID`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `SPARK_MODE`,
`SPARK_CHAT_IDS`, `SPARK_DB`, `LOG_LEVEL`, `SENTRY_DSN` (optional). Added by Task A: `BOT_TOKEN`,
`OWNER_CHAT_ID`, `GEMINI_DAILY_BUDGET`, `SPARK_MEDIA`, `SPARK_TIMETABLE`. Use these exact names as
pydantic aliases in `src/config.py` and keep `.env.example` in sync.

## Domain constants (do not regress; `tests/test_spark_rules.py` pins them)
| Key | Course | Code |
|---|---|---|
| DSA | Data Structures & Algorithms-3 (also written DSA3, DSA-3) | 25CS2103E |
| OSSP | Operating Systems & Systems Programming | 25CS2104E |
| ML | Machine Learning | 25SC2107E |
| ESD | Embedded System Design & IoT | 25EC2206E |
| DBSE | Database Systems Engineering | 25CS1302E |
| JAPANESE | Japanese Language Proficiency-2 | 25FL2112E |

Periods (IST, there is no P6): P1 08:10–09:00, P2 09:00–09:50, P3 10:00–10:50, P4 10:50–11:40,
P5 11:50–12:40, P7 13:20–14:10, P8 14:20–15:10, P9 15:10–16:00. Rooms look like `H-005`, `HC-15C`,
`H301A`, `H006`, `H107A`.

## SQLite state (`SPARK_DB`, default `spark.db`, WAL mode)
Tables are created on demand. Existing: `seen(key PRIMARY KEY, ts)`. Tasks add: `chat_state`,
`llm_budget`, `pending`, `writes`, `meta`. Use the connection-helper pattern from
`src/utils/deduplication.py`; no ORM.

## Style
- Python 3.12, ruff line length 100, pytest-asyncio in auto mode.
- Smallest diff that works. Reuse existing helpers. Standard library before new dependencies. Add no
  abstraction nobody asked for.
- Mark deliberate corner-cutting with `# ponytail: <known ceiling> -> <upgrade path>`.
- Every behavior you add or change gets a test in `tests/`. Keep existing tests green. Change an
  existing assertion only when the task says the behavior changes, and say so in the PR.

## Working rules for Jules
- Stay inside the scope listed in the task. If something outside the scope needs changing, list it
  under "Not done" in the PR instead of editing it.
- Your plan must name every file you will touch. Do not add dependencies.
- Where a task is ambiguous, pick the safer option (no write over a wrong write) and record it under
  "Decisions" in the PR.
- Each task ends with: `python -m pytest -q` green, `ruff check src tests scripts` clean on touched
  files, and one PR whose description has the sections Changed, Decisions, Not done.
