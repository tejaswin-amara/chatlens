# ChatLens 🔍

**AI-powered Telegram & WhatsApp chat analyzer using Google Gemini.**

ChatLens ingests your messaging history, indexes it locally, and lets you explore it through AI — summaries, sentiment analysis, topic extraction, relationship mapping, timeline of key events, and natural-language Q&A.

## Features

- **Multi-platform**: Import chats from Telegram (JSON export or live API) and WhatsApp (.txt export)
- **AI Analysis**: Powered by Google Gemini with 1M+ token context window
  - Conversation summaries
  - Sentiment analysis
  - Topic extraction & clustering
  - Relationship mapping (who talks to whom, tone, frequency)
  - Timeline of key events and decisions
  - Interactive Q&A — ask anything about your chats
- **Dual interface**: CLI for quick tasks, web UI for exploration
- **Local-first**: All data stored in SQLite on your machine. Nothing leaves your device except Gemini API calls.
- **Multi-device**: Works anywhere Python runs. Telegram sessions are portable.

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/chatlens.git
cd chatlens
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your Gemini API key
```

Get your free Gemini API key from [Google AI Studio](https://aistudio.google.com/).

For live Telegram access, also add your `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from [my.telegram.org](https://my.telegram.org).

### 3. Import Your Chats

**Telegram** (from Desktop export):
```bash
# In Telegram Desktop: Settings → Advanced → Export Telegram Data → JSON format
python -m chatlens.cli import telegram path/to/result.json
```

**Telegram** (live from your account):
```bash
python -m chatlens.cli import telegram-live
# First run will ask for phone number authentication
```

**WhatsApp**:
```bash
# In WhatsApp: Open chat → ⋮ → More → Export Chat → Without Media
python -m chatlens.cli import whatsapp path/to/chat.txt
```

### 4. Analyze

```bash
# List imported chats
python -m chatlens.cli list

# Summarize a conversation
python -m chatlens.cli summarize "Chat Name"

# Full analysis (summary + sentiment + topics + relationships + timeline)
python -m chatlens.cli analyze "Chat Name"

# Ask a question across all your chats
python -m chatlens.cli ask "What did we decide about the project deadline?"

# Search for keywords
python -m chatlens.cli search "meeting tomorrow"
```

### 5. Web UI

```bash
python -m chatlens.cli web
# Open http://localhost:5000
```

## Architecture

```
chatlens/
├── cli.py            # CLI interface (Click)
├── web.py            # Web interface (Flask)
├── config.py         # Settings from .env
├── storage.py        # SQLite + FTS5 message store
├── analyzer.py       # Gemini AI analysis engine
├── parsers/
│   ├── telegram.py      # Telegram JSON export parser
│   ├── whatsapp.py      # WhatsApp .txt export parser
│   └── telegram_live.py # Live Telegram API (Telethon)
└── templates/
    └── index.html       # Web UI
```

## How It Works

1. **Ingest**: Parsers normalize messages from different platforms into a unified format
2. **Store**: Messages go into SQLite with full-text search indexing
3. **Analyze**: When you ask a question or request analysis, relevant messages are retrieved and sent to Gemini as context
4. **Chunk**: For large chats (800+ messages), the analyzer splits by time windows, processes each chunk, and combines results

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Your Google Gemini API key |
| `TELEGRAM_API_ID` | No | — | Telegram API ID (for live access) |
| `TELEGRAM_API_HASH` | No | — | Telegram API hash (for live access) |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model to use |
| `DB_PATH` | No | `chatlens.db` | SQLite database file path |

## Privacy

- All chat data is stored **locally** in a SQLite database on your machine
- The only external calls are to the Google Gemini API for analysis
- No data is stored on Google's servers beyond API processing
- `.env`, database files, and Telegram sessions are gitignored

## License

MIT
