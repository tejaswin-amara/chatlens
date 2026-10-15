# Ponytail Technical Debt Ledger

Tracked deferrals and shortcuts harvested from codebase annotations (`shortcut:` / `ponytail:`).

| ID | File:Line | Description / Ceiling / Upgrade Path | Status |
|---|---|---|---|
| DEBT-01 | `chatlens-v2/backend/parsers/telegram_live.py:86` | cap to 5 most recent dialogs to avoid hanging during sync | no-trigger |
| DEBT-02 | `chatlens-v2/backend/parsers/telegram_live.py:130` | uses asyncio.run; breaks if called inside an existing event loop. | no-trigger |
| DEBT-03 | `chatlens-v2/backend/parsers/whatsapp.py:29` | brute-force tries multiple date formats instead of locale detection | no-trigger |

**Summary**: 3 total debt markers tracked in ledger.
