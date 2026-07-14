# ChatLens v2.0 🔍

**AI-powered Telegram & WhatsApp chat analyzer using Google Gemini.**

ChatLens ingests your messaging history, indexes it in a PostgreSQL database using `pgvector`, and lets you explore it through AI — summaries, sentiment analysis, topic extraction, relationship mapping, and natural-language Q&A.

## Features

- **Multi-platform**: Import chats from Telegram (JSON export or live API) and WhatsApp (.txt export).
- **AI Analysis**: Powered by Google Gemini with a 1M+ token context window.
  - Conversation summaries
  - Sentiment analysis
  - Topic extraction & clustering
  - Relationship mapping (who talks to whom, tone, frequency)
  - Interactive Q&A — ask anything about your chats
- **Next.js Web UI**: A beautiful, premium, glassmorphic UI built with Next.js App Router and TailwindCSS.
- **FastAPI Backend**: Asynchronous Python backend powered by FastAPI, SQLAlchemy, and Celery.
- **Vector Search**: PostgreSQL with `pgvector` for advanced semantic search across your messages.

## Architecture

```
chatlens/
├── backend/
│   ├── main.py            # FastAPI entry point
│   ├── database.py        # PostgreSQL config and connection
│   ├── models.py          # SQLAlchemy models (pgvector)
│   ├── celery_worker.py   # Celery worker for async parsing
│   ├── analyzer.py        # Gemini AI analysis engine
│   └── parsers/           # WhatsApp and Telegram parsers
└── frontend/
    ├── src/app/           # Next.js App Router
    ├── components/        # React components (TailwindCSS + Lucide)
    ├── hooks/             # Custom React hooks (useApi)
    └── types.ts           # Shared TypeScript interfaces
```

## Quick Start (Docker Compose)

The easiest way to run ChatLens v2 is using Docker Compose, which sets up the backend, frontend, PostgreSQL (with pgvector), and Redis.

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/chatlens.git
cd chatlens

# Create environment configuration
cp .env.example .env
```
Edit `.env` and add your Gemini API key (Get your free key from [Google AI Studio](https://aistudio.google.com/)).

### 2. Run with Docker Compose

```bash
docker-compose up -d --build
```

### 3. Open Web UI
Open your browser and navigate to `http://localhost:3000`.

## Manual Setup

If you prefer to run the services locally without Docker:

### 1. Prerequisites
- PostgreSQL with `pgvector` extension installed and running.
- Redis server running locally.
- Node.js (v18+) and Python 3.10+.

### 2. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
In a separate terminal, start the Celery worker:
```bash
celery -A celery_worker.celery_app worker --loglevel=info
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000`.

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Your Google Gemini API key |
| `TELEGRAM_API_ID` | No | — | Telegram API ID (for live access) |
| `TELEGRAM_API_HASH` | No | — | Telegram API hash (for live access) |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model to use |
| `DATABASE_URL` | No | `postgresql+asyncpg://...` | PostgreSQL connection URL |
| `CELERY_BROKER_URL`| No | `redis://localhost:6379/0`| Redis broker URL |

## Privacy

- All chat data is stored locally in your own PostgreSQL database.
- The only external calls are to the Google Gemini API for analysis.
- No data is stored on Google's servers beyond API processing.

## License

MIT
