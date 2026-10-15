# Ponytail Technical Debt Ledger

Tracked deferrals and shortcuts harvested from codebase annotations (`shortcut:` / `ponytail:`).

| ID | File:Line | Description / Ceiling / Upgrade Path | Status |
|---|---|---|---|
| DEBT-01 | `chatlens/analyzer.py:9` | hard-coded chunk size; good enough for gemini-2.0-flash context window. | no-trigger |
| DEBT-02 | `chatlens/storage.py:36` | content='' (external content) would save space but complicates inserts. | no-trigger |
| DEBT-03 | `chatlens/web.py:20` | module-level singletons; fine for single-process dev server. | no-trigger |
| DEBT-04 | `chatlens-v2/backend/parsers/telegram_live.py:86` | cap to 5 most recent dialogs to avoid hanging during sync | no-trigger |
| DEBT-05 | `chatlens-v2/backend/parsers/telegram_live.py:130` | uses asyncio.run; breaks if called inside an existing event loop. | no-trigger |
| DEBT-06 | `chatlens-v2/backend/parsers/whatsapp.py:29` | brute-force tries multiple date formats instead of locale detection | no-trigger |
| DEBT-07 | `chatlens/parsers/telegram_live.py:106` | uses asyncio.run; breaks if called inside an existing event loop. | no-trigger |
| DEBT-08 | `chatlens/parsers/whatsapp.py:29` | brute-force tries multiple date formats instead of locale detection | no-trigger |

**Summary**: 8 total debt markers tracked in ledger.
