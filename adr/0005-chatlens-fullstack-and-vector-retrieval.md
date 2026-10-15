# ADR 0005: ChatLens Full-Stack Architecture, Vector Retrieval, and SPARK Bridge

* Status: accepted
* Deciders: Autonomous Engineering Team, Principal Software Engineer
* Date: 2026-10-15

## Context and Problem Statement
The ChatLens platform comprises two primary operational components:
1. A headless personal assistant daemon (`src/`) consuming live Telegram messages to automate academic calendar, timetable, and Google Workspace updates.
2. A full-stack chat analytics application (`chatlens-v2/`) providing WhatsApp/Telegram export ingestion, statistical dashboards, and LLM-driven insights.

Previously, `chatlens-v2` had several architectural limitations:
* Asynchronous file uploads returned `status: "processing"`, which conflicted with frontend expectations of immediate completion.
* Vector embeddings in PostgreSQL `messages.embedding` were hardcoded to 1536 dimensions (OpenAI format) and left unpopulated on ingest, causing AI question answering to fall back entirely to recency-based message slices.
* No bridge existed to inspect SPARK PA daemon execution state, pending approvals, or undo history within the visual interface.
* Lack of in-chat search, chat deletion, and export capabilities.

## Decision Drivers
* Native Gemini embedding support (`text-embedding-004`, 768 dimensions) with cosine distance search via `pgvector`.
* Non-blocking ingestion with Celery background worker and automatic synchronous fallback for lightweight developer environments.
* Read-only SPARK PA daemon bridge that accesses SQLite state without introducing PostgreSQL dependencies into the daemon.
* Production-grade frontend UX featuring in-chat message search, chat deletion, markdown export, and pagination.

## Considered Options
* Option 1: Retain 1536-dim embeddings and require separate OpenAI API keys for vector search.
* Option 2: Standardize on Google Gemini ecosystem with 768-dim `text-embedding-004`, HNSW cosine index, Celery background worker with synchronous fallback, and SQLite read-only status bridge.

## Decision Outcome
Chosen option: **Option 2 (Unified Gemini 768-dim pgvector and SPARK Bridge)**.

### Positive Consequences
* Vector embeddings are generated in batches using `text-embedding-004` and indexed via PostgreSQL HNSW.
* `/api/ask` executes true semantic similarity retrieval with cosine distance, gracefully falling back to recent context if embeddings are unpopulated.
* File uploads support polling via `/api/tasks/{task_id}` and transparent synchronous fallback if Celery/Redis is offline.
* SPARK PA daemon remains completely decoupled from PostgreSQL while its state is observable in ChatLens via `/api/spark/status`.
* In-chat message search, chat deletion, markdown export, and message pagination are natively supported.

### Negative Consequences / Tradeoffs
* Schema migration `002_vector_768.sql` alters the `embedding` column from `vector(1536)` to `vector(768)`.

## Confirmation & Verification
* Automated parser unit tests pass in `tests/test_backend_parsers.py`.
* API unit tests pass in `tests/test_backend_api.py`.
* Container integration tests pass against `pgvector/pgvector:pg16` in `tests/integration/test_db_integration.py`.
* ADR conformity verified via `scripts/check_adrs.py`.
