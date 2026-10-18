# AgentShield Security Specification (ECC v2.2.3 Alignment)

> Standard: `affaan-m/ECC` AgentShield & Awesome Dev Pipeline Security Hierarchy (Rank 0)  
> Scope: All daemon operations, API ingress, database queries, and external scrapers.

---

## 1. Zero Plaintext Secrets
- Secrets (tokens, passwords, session strings, API keys) must NEVER be committed to version control, embedded in source code, or written to unencrypted logs.
- Secrets must be loaded exclusively via environment variables or `.env` (which must remain in `.gitignore`).
- When logging, all credentials and API keys must be masked or omitted entirely.

## 2. Input Boundaries & Prompt Injection Defense
- Untrusted inputs from Telegram messages, group chats, channels, and external web scraping must be sanitized before processing.
- All LLM inputs must be guarded by adversarial canary checks (verifying inputs do not hijack system directives).
- PII redaction must actively scrub 12-digit Aadhaar numbers, phone numbers, and student registration IDs before any external LLM invocation.

## 3. Telegram Ingress Invariant
- Telegram listener operates in STRICT READ-ONLY mode.
- The daemon must NEVER send messages to groups, channels, or non-allowlisted entities.
- Outbound responses are restricted exclusively to the bot owner's private chat ID (`OWNER_CHAT_ID`) or Telegram Saved Messages (`"me"`).

## 4. Database & Persistence Guardrails
- All SQLite queries must use parameterized placeholders (`?`). String formatting or interpolation into SQL queries is strictly prohibited.
- WAL (Write-Ahead Logging) mode is mandatory for concurrent read/write resilience.
- Irreversible destructive operations (dropping tables, broad recursive deletes) are strictly prohibited.
