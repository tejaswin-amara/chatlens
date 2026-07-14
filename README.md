# ChatLens v2.0 🔍

<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0.0-00d4aa?style=for-the-badge&logo=github" alt="Version" />
  <img src="https://img.shields.io/badge/Gemini-1.5%20%7C%202.0%20%7C%202.5-00b4d8?style=for-the-badge&logo=google-gemini" alt="Gemini" />
  <img src="https://img.shields.io/badge/Next.js-16.0-ffffff?style=for-the-badge&logo=nextdotjs&logoColor=black" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169e1?style=for-the-badge&logo=postgresql" alt="PostgreSQL" />
</p>

---

### **AI-powered Telegram & WhatsApp chat analyzer utilizing Google Gemini.**

**ChatLens** indexes your chat history in a PostgreSQL database using `pgvector` and lets you explore your conversations using Gemini AI. Generate summaries, analyze sentiments, cluster topics, map relationships, and perform natural-language Q&A across your messages.

---

## ✨ Features

*   **🗂️ Multi-Platform Ingestion**
    *   **Telegram**: Import standard JSON exports or authorize live via Telethon API.
    *   **WhatsApp**: Import standard `.txt` chat exports.
*   **🧠 Deep AI Analysis** (Powered by Gemini's 1M+ token context window):
    *   **Summarization**: Dynamic, context-aware chat recaps.
    *   **Sentiment Tracking**: Analyze emotional trends and tone shifts.
    *   **Topic Clustering**: Auto-extract themes and key discussion points.
    *   **Relationship Mapping**: Map interaction frequencies and dynamics.
*   **💬 Interactive Q&A**: Ask natural language questions about your chats (e.g. *"What did we decide on for dinner last Tuesday?"*).
*   **📊 Spotify-Wrapped style Stats**:
    *   Quantitative dashboards with hourly and daily activity graphs.
    *   Fun, automated awards: `🗣️ Top Talker`, `👀 The Observer`, `📜 The Monologuer`, `🧊 The Icebreaker`, and `⚡ Speed Demon`.
*   **🎨 Premium Glassmorphic Web UI**: A responsive UI built using Next.js App Router and TailwindCSS.

---

## 🏗️ Architecture

```
chatlens/
├── chatlens/             # Legacy v1.0 Module (Flask + SQLite)
└── chatlens-v2/          # Modern v2.0 Next.js + FastAPI Stack
    ├── backend/
    │   ├── main.py            # FastAPI Entry Point
    │   ├── database.py        # SQLAlchemy & pgvector Connection
    │   ├── models.py          # SQLAlchemy Models (pgvector)
    │   ├── celery_worker.py   # Asynchronous celery parser tasks
    │   ├── analyzer.py        # Gemini AI Analysis Engine
    │   └── parsers/           # WhatsApp and Telegram Parsers
    └── frontend/
        ├── src/app/           # Next.js App Router (Turbopack)
        ├── components/        # React Components (Lucide + Chart.js)
        ├── hooks/             # Custom useApi Hook
        └── types.ts           # Shared TypeScript Interfaces
```

---

## 🚀 Quick Start (Docker Compose)

The easiest way to run ChatLens v2.0 is using Docker Compose, which configures the FastAPI backend, Next.js frontend, PostgreSQL (with pgvector), and Redis.

### 1. Clone & Configure
```bash
git clone https://github.com/tejaswin-amara/chatlens.git
cd chatlens

# Copy environment template
cp .env.example .env
```
Edit `.env` and add your **Gemini API Key** (get one free at [Google AI Studio](https://aistudio.google.com/)).

### 2. Launch Services
```bash
docker-compose up -d --build
```

### 3. Open Web UI
Open your browser and navigate to `http://localhost:3000` to start importing and exploring!

---

## 🛠️ Manual Local Setup

If you prefer to run the services locally without Docker:

### ⚙️ Prerequisites
*   PostgreSQL with the `pgvector` extension installed and running.
*   Redis server running locally.
*   Node.js (v18+) and Python 3.10+.

### 🐍 Backend setup
```bash
cd chatlens-v2/backend

# Create & activate a virtualenv
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

In a separate terminal, start the Celery worker:
```bash
celery -A celery_worker.celery_app worker --loglevel=info
```

### ⚛️ Frontend setup
```bash
cd chatlens-v2/frontend

# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```
Open `http://localhost:3000`.

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `GEMINI_API_KEY` | **Yes** | — | Google Gemini API key from Google AI Studio |
| `TELEGRAM_API_ID` | No | — | Telegram App API ID (from [my.telegram.org](https://my.telegram.org)) |
| `TELEGRAM_API_HASH` | No | — | Telegram App API Hash (from [my.telegram.org](https://my.telegram.org)) |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model to use for analysis |
| `DATABASE_URL` | No | `postgresql+asyncpg://...` | PostgreSQL async connection string |
| `CELERY_BROKER_URL`| No | `redis://localhost:6379/0`| Redis Celery broker connection string |

---

## 🔒 Privacy & Safety

*   **Local First**: All chat messages, parses, and stats are stored locally in your own PostgreSQL instance.
*   **Transient AI Calls**: The only data that leaves your machine is the contextual prompt sent directly to Google's Gemini API for summarization and Q&A analysis. No chat data is permanently stored on Google's servers.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
