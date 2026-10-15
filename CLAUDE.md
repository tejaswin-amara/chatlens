# CLAUDE.md — ChatLens Assistant Guide

## Essential Commands
- Sync: `uv sync --all-extras --dev` && `(cd chatlens-v2/frontend && npm ci)`
- Test: `uv run pytest -q -W error::RuntimeWarning`
- Lint: `uv run ruff check src tests scripts` && `uv run mypy src`
- Build Frontend: `cd chatlens-v2/frontend && npm run build`
- Run Daemon: `uv run python -m src.main`

## Architecture & Conventions
- Runtime: Python 3.12 (`uv`) + Next.js 16 (`npm`) + FastAPI + PostgreSQL `pgvector`.
- Timezone: IST (`Asia/Kolkata`, UTC+05:30) everywhere via `src.utils.clock`.
- Zero raw `datetime.now()` in `src/`. Always use `clock.now_ist()` or `clock.today_ist()`.
- Read-only Telegram ingestion via Telethon. Messages routed only to owner bot or "me".
- Privacy: Never leak secrets, tokens, or PII (`msg_text`, `sender_name`, `chat_title`) in INFO logs.
- Gemini: `GEMINI_MODEL` (default `gemini-3.5-flash-lite`). Never pass temperature/top_p/top_k.
- Tests: Mock at adapter boundaries. Zero network calls at test or import time.
- Style: Smallest working diff, standard library first, ruff line length 100.
