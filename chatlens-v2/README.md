# ChatLens v2.0

Full-stack asynchronous multi-platform chat analytics and semantic intelligence platform.

---

## 1. Architecture Overview

ChatLens v2 provides scalable chat ingestion, semantic search, AI summarization, and interactive analytics across WhatsApp and Telegram exports.

```
┌─────────────────────────────────────────────────────────┐
│              Next.js 16 App Router (React 19)           │
│   src/app (Pages) · src/components · src/hooks · src/types
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / JSON
┌──────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend                      │
│   Lifespan Migration Runner · Async SQLAlchemy Engine   │
└────────────┬─────────────────────────────┬──────────────┘
             │                             │
    pgvector │ Storage              Celery │ Async Ingestion
┌────────────▼─────────────┐     ┌─────────▼──────────────┐
│  PostgreSQL + pgvector   │     │    Redis + Celery      │
│  Embeddings & Messages   │     │ Distributed Task Queue │
└──────────────────────────┘     └────────────────────────┘
```

---

## 2. Directory Structure

```
chatlens-v2/
├── backend/
│   ├── analyzer.py        # Gemini AI semantic query & summarizer
│   ├── celery_worker.py   # Background file parsing & batch ingestion
│   ├── database.py        # Async SQLAlchemy engine & session factory
│   ├── main.py            # FastAPI REST endpoints & lifespan manager
│   ├── migrations/        # SQL schema migrations (001_content_hash.sql)
│   ├── models.py          # Declarative SQLAlchemy models (Message, Base)
│   └── parsers/           # Deterministic WhatsApp & Telegram export parsers
└── frontend/
    ├── src/
    │   ├── app/           # App Router pages (layout.tsx, page.tsx, globals.css)
    │   ├── components/    # Reusable UI widgets (Dashboard, Sidebar, MessageList)
    │   ├── hooks/         # Client data fetching hooks (useApi.ts)
    │   └── types.ts       # Shared TypeScript domain contracts
    ├── package.json
    └── tsconfig.json
```

---

## 3. Environment Variables

### Backend (`chatlens-v2/backend/.env`)
| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/chatlens` |
| `CELERY_BROKER_URL` | Redis URL for Celery task queuing | `redis://localhost:6379/0` |
| `GEMINI_API_KEY` | Google Gemini API key for analysis | (Required) |
| `GEMINI_MODEL` | Gemini extraction & analysis model | `gemini-3.5-flash-lite` |

### Frontend (`chatlens-v2/frontend/.env.local`)
| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the running FastAPI backend | `http://localhost:8000` |

---

## 4. Setup and Execution

### Prerequisites
- Python 3.12+ (managed via `uv`)
- Node.js 20+ (managed via `npm`)
- PostgreSQL with `pgvector` extension enabled
- Redis server running on `localhost:6379`

### Running the Backend
```bash
cd chatlens-v2/backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Running the Celery Worker
```bash
cd chatlens-v2/backend
# On Windows, always specify --pool=solo
uv run celery -A celery_worker.celery_app worker --loglevel=info --pool=solo

# On Linux / macOS
uv run celery -A celery_worker.celery_app worker --loglevel=info
```

### Running the Frontend
```bash
cd chatlens-v2/frontend
npm ci
npm run dev
# Production build check:
npm run build
```

---

## 5. Key REST API Endpoints

- `GET /api/chats` — List available chats and message counts.
- `GET /api/chats/{chat_name}/messages` — Paginated chat history.
- `POST /api/upload/whatsapp` — Asynchronous WhatsApp `.txt` export ingestion.
- `POST /api/upload/telegram` — Asynchronous Telegram JSON export ingestion.
- `POST /api/ask` — Semantic Q&A over ingested chats via vector similarity & Gemini.
- `POST /api/summarize` — AI-generated summary of chat activity.
- `GET /api/stats` — Global volume, chat, and platform statistics.
