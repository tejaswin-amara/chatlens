# Ponytail Technical Debt Ledger

Tracked deferrals and shortcuts harvested from codebase annotations (`shortcut:` / `ponytail:`).

| ID | File:Line | Description / Ceiling / Upgrade Path | Status |
|---|---|---|---|
| DEBT-01 | `chatlens-v2/frontend/scripts/challenger-icon-stress.ts:382` | '), | no-trigger |
| DEBT-02 | `chatlens-v2/frontend/src/app/page.tsx:219` | reuse handleLogin with overrides to bypass async state update delay | no-trigger |
| DEBT-03 | `chatlens-v2/frontend/src/components/Navigation.tsx:217` | prefix-sweep instead of maintaining a key list; upgrade to namespace if storage grows | Tracked |
| DEBT-04 | `chatlens-v2/frontend/src/lib/request-utils.ts:125` | auto-detect Vercel; upgrade to explicit allowlist if multi-provider needed | Tracked |
| DEBT-05 | `chatlens-v2/frontend/src/lib/scrapers/http-jar.ts:9` | Object.create(null) prevents prototype-pollution via route params (e.g. /constructor) | no-trigger |

**Summary**: 5 total debt markers tracked in ledger.
