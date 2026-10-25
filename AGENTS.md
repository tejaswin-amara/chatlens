# AGENTS.md — ChatLens & SPARK

## Purpose and architecture
This repository contains two maintained components:

- **SPARK PA daemon (`src/`)** — a headless Telegram-to-Google-Workspace academic assistant. Its entry point is `python -m src.main`; it classifies allowlisted messages, validates events against the timetable, and synchronizes approved changes to Google Calendar, Tasks, and Sheets.
- **ChatLens platform (`chatlens-v2/`)** — a web application with a FastAPI backend, Next.js frontend, asynchronous ingestion workers, PostgreSQL/pgvector, and Redis/Celery.

The root `compose.yaml` is the canonical Compose definition. Do not treat `chatlens-v2/` or `docs/` as legacy. Keep the SPARK daemon isolated from the web stack: PostgreSQL, Redis, and Celery belong to the web platform, not `src/`.

The current academic data is deployment-specific (IST); verify dates, course metadata, and time-zone assumptions against authoritative institutional documents before reusing it elsewhere.

## Commands
- Setup: `uv sync --all-extras --dev` (Python 3.12 or newer).
- Python tests: `uv run pytest -q -W error::RuntimeWarning`.
- Python lint/format: `uv run ruff check src tests scripts chatlens-v2/backend` and `uv run ruff format --check src tests scripts chatlens-v2/backend`.
- Type checks: `uv run mypy src scripts benchmarks chatlens-v2/backend`.
- Frontend checks: from `chatlens-v2/frontend/`, run `npm ci`, `npm test -- --run`, `npm run lint`, `npx tsc --noEmit`, and `npm run build`.
- Full local gate: `make check` (also requires `make`, `gitleaks`, and `osv-scanner`).

## SPARK daemon invariants
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
5. Date/time handling follows the timezone defined in `src/utils/clock.py` (currently IST). Telegram
   messages never change official academic-calendar dates (exams, last instruction day, detention
   list, fee deadlines); conflicts are flagged, not applied.
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
11. Universal Outbound Formatting: Every user-facing bot message must adhere to `docs/MESSAGE_FORMATTING_RULES.md` and render through `src/formatting/templates.py`. Never output raw database dumps, bare URLs, or unstructured text.
12. Anti-Ban Compliance (`R-BAN-1`–`R-BAN-5`): Outbound messaging strictly respects leaky-bucket rate limits, 15-minute startup debounce, read-only group ingestion, allowlisted chat boundaries, and circuit breaker backoff.

## Environment variables
`TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION_STRING`, `GOOGLE_CREDENTIALS_BASE64`,
`GOOGLE_CALENDAR_ID`, `GOOGLE_SHEET_ID`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `SPARK_MODE`,
`SPARK_CHAT_IDS`, `SPARK_DB`, `LOG_LEVEL`, `SENTRY_DSN` (optional). Added by Task A: `BOT_TOKEN`,
`OWNER_CHAT_ID`, `GEMINI_DAILY_BUDGET`, `SPARK_MEDIA`, `SPARK_TIMETABLE`. Use these exact names as
pydantic aliases in `src/config.py` and keep `.env.example` in sync.

## Instance-specific academic data
Course names, official codes, aliases, period numbering and times, room/section formats, term dates,
and time zones are deployment-specific. Do not present the current values as universal defaults or
copy them to another institution without verification.

Current implementation locations:
- Course aliases and course codes: `src/parsing/regex_parser.py`
- Course metadata, period-time mapping, period parsing, and timetable behavior: `src/timetable/__init__.py`
- Active-term timetable: the TOML file selected by `SPARK_TIMETABLE` (current default:
  `data/timetable_T04.toml`)
- Date/time handling: `src/utils/clock.py` (current deployment uses IST)
- Academic milestone rules/data: `src/academic_calendar.py` and its academic-calendar data file
- Message templates and link safety: `src/formatting/templates.py`, `src/formatting/markdown_safety.py`
- Message design standards: `docs/MESSAGE_FORMATTING_RULES.md`
- Background workers & lifecycle: `src/main.py` (`run_reminders`, `briefing_loop`, `heartbeat_loop`, `bot_callback_poll`)

Treat institution-published calendars and timetables as the authority. Do not silently change
official dates or periods. When modifying deployment-specific academic data or parsing rules, update
the relevant tests in `tests/` and verify both valid and conflicting/ambiguous notices. Changing
`SPARK_TIMETABLE` alone does not make the parser, period mappings, or timezone portable.

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
