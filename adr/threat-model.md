# STRIDE Threat Model: ChatLens & SPARK PA Assistant

* Version: 2.0.0
* Date: 2026-10-15
* Scope: SPARK PA Daemon (`src/`), Web Platform (`chatlens-v2/`), CI/CD & Deployments

---

## 1. System Architecture & Trust Boundaries

```
[ Telegram Groups / Channels ] (Untrusted)
              │
              ▼ (MTProto read-only session)
   [ Ingestion Layer (Telethon) ]
              │
    ┌─────────┴───────────────────────┐
    ▼                                 ▼
[ Regex Parser ]             [ Gemini LLM Adapter ]
    │                                 │
    └─────────┬───────────────────────┘
              ▼
   [ Decision Engine & Timetable Validation ]
              │
    ┌─────────┼───────────────────────┐
    ▼         ▼                       ▼
[ SQLite DB ] [ Telegram Bot API ] [ Google Workspace API ]
(Local WAL)   (Private to Owner)   (Calendar, Tasks, Sheets)
```

### Trust Boundaries
* **TB1 (Ingestion Boundary)**: Untrusted Telegram messages from multi-user groups entering the read-only ingestion client.
* **TB2 (LLM Boundary)**: Data sent across the network to Google Gemini API endpoints.
* **TB3 (Google Workspace Boundary)**: Mutating calendar entries, tasks, and attendance spreadsheets via OAuth credentials.
* **TB4 (Owner Interaction Boundary)**: Inbound bot callbacks and command controls (`/undo`) from the Telegram Bot API.
* **TB5 (Supply Chain & Deployment Boundary)**: GitHub Actions workflows, third-party actions, container images, and package dependencies.

---

## 2. STRIDE Threat Analysis by Component

### 2.1 Ingestion Layer (Telethon Listener)
| Category | Threat Description | Severity | Mitigation in Place |
|---|---|---|---|
| **Spoofing** | Attacker impersonates university administrator in Telegram chat. | High | Ingestion restricted to explicitly configured `SPARK_CHAT_IDS`. Messages classified as cancellations/holidays mandate manual confirmation by the student owner (`Decision.CONFIRM`). |
| **Tampering** | Man-in-the-Middle tampering with incoming Telegram updates. | Low | MTProto 2.0 end-to-end and transport encryption protocol natively verified by Telethon. |
| **Repudiation** | Disputes over whether a message was received or processed. | Medium | SQLite `seen` table records message hash, peer ID, message ID, and timestamp. |
| **Information Disclosure** | Telethon session credentials or student chat contents leaked in logs. | Critical | Telethon session string stored exclusively in environment variable. Logging scrubbers strip all message text, sender names, and tokens from INFO logs. |
| **Denial of Service** | Message flood causing Telegram `FloodWaitError` or rate limits. | High | Asynchronous event processing with exponential backoff handling for `FloodWaitError` in `src/main.py`. |
| **Elevation of Privilege** | Daemon hijacked to send unauthorized broadcast messages into university chats. | Critical | Daemon is strictly read-only on ingestion channels; outbound sending is structurally limited to `OWNER_CHAT_ID` via dedicated Bot API or Saved Messages `"me"`. |

### 2.2 Parsing & LLM Layer (Regex & Gemini)
| Category | Threat Description | Severity | Mitigation in Place |
|---|---|---|---|
| **Spoofing** | Prompt injection attacks (PI-01 to PI-10) attempting to override assistant rules or extract internal prompts. | High | Regex-first parsing bypasses LLM for routine patterns. Residual messages to Gemini are sanitised, wrapped in XML `<telegram_message>` delimiters, and governed by strict JSON schemas. |
| **Tampering** | LLM hallucinating incorrect exam dates or room overrides. | High | Strict post-extraction timetable validation against canonical student timetable (`src/timetable/`). Unmatched classes trigger `Decision.REVIEW`. |
| **Repudiation** | Lack of traceability for AI vs Regex classification decisions. | Low | Extraction metadata tracks source (`regex`, `gemini`), model version, and confidence in audit logs and DB state. |
| **Information Disclosure** | PII (student roll numbers, email addresses, phone numbers) sent to external LLM provider. | High | Pre-extraction regex scrubbers replace emails, URLs, and phone numbers with tokens (`[EMAIL]`, `[URL]`, `[PHONE]`) before LLM payload construction. |
| **Denial of Service** | Malicious users spamming chat to exhaust `GEMINI_DAILY_BUDGET`. | Medium | Daily call accounting with hard cutoffs (`GEMINI_DAILY_BUDGET`); 4xx HTTP errors are never retried. |
| **Elevation of Privilege** | Injected message tricking system into executing auto-writes for destructive events. | Critical | `HOLIDAY`, `CLASS_CANCELLED`, and all Gemini-derived events unconditionally require manual confirmation (`Decision.CONFIRM`). |

### 2.3 Workspace Synchronization Layer (Calendar, Tasks, Sheets)
| Category | Threat Description | Severity | Mitigation in Place |
|---|---|---|---|
| **Spoofing** | Forged webhook or event attempting to trigger Google Calendar writes. | High | No inbound public webhooks; the system operates as a client polling Telegram updates and bot callbacks directly. |
| **Tampering** | Erroneous calendar write overwriting legitimate academic class entries. | High | All write operations record previous state in SQLite `writes` table, enabling instantaneous rollback via `/undo`. Room overrides use non-destructive `spark_override` extended properties. |
| **Repudiation** | Inability to determine why an event was written or modified. | Low | Event descriptions include original Telegram message metadata and timestamp. Full audit trail maintained in SQLite and Sheets. |
| **Information Disclosure** | Exposure of `GOOGLE_CREDENTIALS_BASE64` service account key. | Critical | Credentials parsed in-memory; secret patterns scrubbed across all log entries and Sentry exception payloads. |
| **Denial of Service** | Google Workspace API quota exhaustion. | Medium | Tenacity exponential backoff with jitter on 5xx errors; idempotent batch writes. |
| **Elevation of Privilege** | Service account possessing excessive administrative access across Google Workspace. | High | Service account restricted via IAM to the specific calendar and spreadsheet IDs configured in `.env`. |

### 2.4 State & Persistence Layer (SQLite Database)
| Category | Threat Description | Severity | Mitigation in Place |
|---|---|---|---|
| **Spoofing** | Rogue process modifying local SQLite database. | Medium | File system permissions restrict database access to the application service user. |
| **Tampering** | Concurrent writes corrupting state during bot callback processing. | Medium | SQLite configured in Write-Ahead Logging (`PRAGMA journal_mode=WAL; busy_timeout=5000`). Atomic state transitions with conditional claims (`UPDATE pending SET status='CLAIMED' WHERE id=? AND status='PENDING'`). |
| **Repudiation** | Deletion of audit records. | Low | Append-only write log in `writes` table; `mark_undone` updates `undone=1` rather than deleting records. |
| **Information Disclosure** | Raw sensitive database content exposed in repository or backups. | High | `spark.db` excluded via `.gitignore` and `.dockerignore`. |
| **Denial of Service** | Database lock contention causing daemon freeze. | Medium | Connection timeouts configured, connections scoped within context managers and closed promptly. |
| **Elevation of Privilege** | SQL injection via parsed message content. | High | Zero dynamic query concatenation; all database operations use parameterized queries (`?`). |

### 2.5 Supply Chain & CI/CD Layer
| Category | Threat Description | Severity | Mitigation in Place |
|---|---|---|---|
| **Spoofing** | Compromised GitHub Action tags pointing to malicious upstream commits. | Critical | All third-party GitHub Actions pinned to immutable 40-character commit SHAs. |
| **Tampering** | Compromised dependency version injected during build (e.g., CVE-2026-33634). | High | Dependency lockfiles (`uv.lock`, `package-lock.json`) enforced with hash verification; Trivy action pinned and audited. |
| **Repudiation** | Unaudited code merged into master branch. | Medium | Mandatory CI status checks and PR template with explicit evidence reporting. |
| **Information Disclosure** | Hardcoded secrets or tokens committed into git repository. | Critical | Pre-commit hooks (`gitleaks git --staged`) and CI scanning (`gitleaks git --redact --no-banner`). |
| **Denial of Service** | CI pipeline execution loops. | Low | Concurrency group cancellation configured on push/PR updates. |
| **Elevation of Privilege** | Container escape or root privileges inside production container. | High | Container runs as unprivileged user `appuser` (UID 10001) with read-only root where applicable. |
