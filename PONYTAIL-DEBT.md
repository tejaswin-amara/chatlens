# Ponytail Technical Debt Ledger

Tracked deferrals and shortcuts harvested from codebase annotations (`shortcut:` / `ponytail:`).

| ID | File:Line | Description / Ceiling / Upgrade Path | Status |
|---|---|---|---|
| DEBT-01 | `chatlens-v2/frontend/src/app/page.tsx:219` | direct handleLogin call with overrides, upgrade: migrate to unified form action hook if form state expands | Tracked |
| DEBT-02 | `chatlens-v2/frontend/src/components/Navigation.tsx:217` | prefix-sweep instead of maintaining a key list; upgrade to namespace if storage grows | Tracked |
| DEBT-03 | `chatlens-v2/frontend/src/lib/request-utils.ts:125` | auto-detect Vercel; upgrade to explicit allowlist if multi-provider needed | Tracked |

**Summary**: 3 total debt markers tracked in ledger.
