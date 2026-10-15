# Ponytail Technical Debt Ledger

Tracked deferrals and shortcuts harvested from codebase annotations (`shortcut:` / `ponytail:`).

| ID | File:Line | Scope / Simplification | Ceiling | Upgrade Path / Trigger | Status |
|---|---|---|---|---|---|
| DEBT-01 | `chatlens-v2/backend/parsers/telegram_live.py:86` | Dialog list truncation | Cap to 5 most recent dialogs | User explicitly requests full sync or paginated dialogs | `no-trigger` |
| DEBT-02 | `chatlens-v2/backend/parsers/telegram_live.py:130` | Sync wrapper around Telethon | Uses `asyncio.run()`; breaks inside running loop | Accept optional loop param or use `nest_asyncio` | Tracked |
| DEBT-03 | `chatlens-v2/backend/parsers/whatsapp.py:29` | WhatsApp date parsing | Brute-force tries 12 regex formats | Dynamic locale detection when non-standard format reported | `no-trigger` |
| DEBT-04 | `chatlens/analyzer.py:9` (v1 legacy) | LLM chat chunking | Hard-coded 800 message chunk size | Estimate tokens instead of message count | Tracked |
| DEBT-05 | `chatlens/parsers/telegram_live.py:106` (v1 legacy) | Sync wrapper around Telethon | Uses `asyncio.run()`; breaks inside running loop | Accept optional loop param or use `nest_asyncio` | Tracked |
| DEBT-06 | `chatlens/parsers/whatsapp.py:29` (v1 legacy) | WhatsApp date parsing | Brute-force tries 12 regex formats | Dynamic locale detection when non-standard format reported | `no-trigger` |
| DEBT-07 | `chatlens/storage.py:36` (v1 legacy) | SQLite FTS5 table storage | Stores full duplicate text in FTS table | Use `content=''` external content table if disk space constrained | `no-trigger` |
| DEBT-08 | `chatlens/web.py:20` (v1 legacy) | Flask app state singletons | Module-level `_store` singleton | Application factory pattern (`create_app`) if multi-worker WSGI needed | `no-trigger` |

**Summary**: 8 debt markers (3 in `chatlens-v2/`, 5 in legacy `chatlens/`), 5 with no formal upgrade trigger.
