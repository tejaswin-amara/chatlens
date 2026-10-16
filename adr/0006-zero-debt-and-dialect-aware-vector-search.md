# ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing

* Status: accepted
* Deciders: Autonomous Engineering Team, Principal Software Engineer
* Date: 2026-10-16

## Context and Problem Statement
Following the baseline Awesome Dev Pipeline v2.0.0 remediation (`6717bbe`), several codebase gaps remained:
1. Active technical debt markers (`PONYTAIL-DEBT.md`) tracked temporary shortcuts in event loop handling and date format heuristics.
2. In vector retrieval and database insertions, `chatlens-v2/backend` presumed PostgreSQL dialect features (such as `pgvector` cosine distance ordering and PostgreSQL `ON CONFLICT` semantics), which prohibited lightweight in-memory testing with SQLite (`sqlite:///:memory:` with `StaticPool`).
3. Static typing (`mypy`) did not extend to `chatlens-v2/backend/`, allowing untyped variables, missing parameter types, and unhandled coroutines to go undetected.
4. Chat transcripts fed into AI Q&A (`/api/ask`) lacked strict XML prompt fencing, creating vulnerability to indirect prompt injection from imported chat files.
5. In the frontend dashboard, top contributors were non-interactive and could not be filtered by participant.

## Decision Drivers
* Complete debt elimination according to Ponytail Ultra (`/ponytail all`), bringing `PONYTAIL-DEBT.md` to 0.
* Dialect-aware SQL execution supporting PostgreSQL with `pgvector` in production and in-memory SQLite with `StaticPool` in automated test suites.
* Strict static type checking (`mypy`) encompassing `src/`, `scripts/`, `benchmarks/`, and `chatlens-v2/backend/`.
* Untrusted prompt fencing enclosing chat history inside `<untrusted_chat_history>` to prevent prompt hijacking.
* Interactive sender filtering across the Next.js frontend (`page.tsx`, `Dashboard.tsx`, `ChatHeader.tsx`).

## Considered Options
* Option 1: Maintain PostgreSQL-only backend code requiring Docker containers (`testcontainers`) for all tests, retain debt markers in `PONYTAIL-DEBT.md`, and leave `chatlens-v2/backend` untyped in mypy.
* Option 2: Implement dialect-aware vector search and insertion with SQLite fallback, resolve all debt markers to 0, fence AI prompt context inside `<untrusted_chat_history>`, extend full `mypy` coverage across the entire codebase, and wire interactive frontend sender filtering.

## Decision Outcome
Chosen option: **Option 2 (Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing)**.

### Positive Consequences
* `PONYTAIL-DEBT.md` reaches 0 active debt markers.
* `_retrieve_relevant_messages` and `save_messages` dynamically detect dialect name (`postgresql` vs `sqlite`), leveraging `pgvector` cosine distance when available and falling back deterministically to chronological recency under SQLite.
* `chatlens-v2/backend` achieves 100% clean `mypy` compliance with zero errors.
* Offline unit and integration tests run entirely against in-memory SQLite (`sqlite:///:memory:` with `StaticPool`) in < 4 seconds with zero network calls.
* Q&A transcript generation fences all chat content inside `<untrusted_chat_history>...</untrusted_chat_history>` with instructions treating context as untrusted data.
* Frontend dashboard contributors are clickable buttons that instantly filter messages by sender and expose active filter badges with clear buttons.

### Negative Consequences / Tradeoffs
* Dialect checking branches require maintenance if additional database engines are introduced.

## Confirmation & Verification
* `PONYTAIL-DEBT.md` contains 0 entries verified by `python scripts/harvest_debt.py`.
* `uv run mypy src scripts benchmarks chatlens-v2/backend` passes with 0 issues.
* `uv run pytest -q -W error::RuntimeWarning` passes with 100% green tests.
* Next.js App Router passes `npm run lint`, `npx tsc --noEmit`, and `npm run build`.
* ADR conformity verified via `python scripts/check_adrs.py`.
