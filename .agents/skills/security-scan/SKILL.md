---
name: security-scan
description: Execute AgentShield security and privacy audits including hardcoded secrets detection, SQL injection checks, prompt injection canary validation, and PII masking audits.
---

# AgentShield Security Scan Skill (`security-scan`)

Use this skill to audit repository security boundaries, verify PII masking filters, prevent prompt injection, and validate zero-secret policies.

## Security Audit Areas

### 1. Zero Hardcoded Secrets
Scan tracked files for secret patterns (API keys, bot tokens, private keys):
- Google AI API keys (`AIza...`)
- Telegram bot tokens (`bot<id>:<token>`)
- OpenAI keys (`sk-...`)
- GitHub Personal Access Tokens (`ghp_...`, `github_pat_...`)
- Private key headers (`-----BEGIN ... KEY-----`)

### 2. PII Masking & Privacy Scrubber
Verify zero disclosure of sensitive identifiers across logs and LLM contexts:
- **Aadhaar Numbers**: Masked as `[Aadhaar Redacted]`
- **RRN**: Masked as `[RRN Redacted]`
- **MyNumber**: Masked as `[MyNumber Redacted]`
- **Phone Numbers**: Masked as `[PHONE]`
- **Emails**: Masked as `[EMAIL]`
- **URLs**: Masked as `[URL]`

Run privacy unit tests:
```bash
uv run pytest tests/test_logging_privacy.py -v
```

### 3. SQL Injection Resistance
Verify that all SQLite and database queries use strictly parameterized bindings (`?` or SQLAlchemy bound parameters). Confirm SQLite connections use WAL mode (`PRAGMA journal_mode=WAL`).

### 4. Adversarial Prompt Injection Defense
Verify data-instruction delimiters (`<untrusted_telegram_message>`, `<untrusted_chat_history>`) and execute adversarial canary suites:
```bash
uv run pytest tests/test_prompt_injection_canaries.py -v
```

### 5. Ingress & Egress Invariants
Confirm Telegram listener is strictly read-only for monitored groups:
- Inbound handler drops outgoing messages.
- Command handler is restricted to Saved Messages (`"me"`).
- Outbound bot messages target only `OWNER_CHAT_ID`.
