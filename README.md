# ChatLens & SPARK PA Assistant

<p align="center">
  <img src="docs/assets/banner.svg" alt="ChatLens: AI-powered Telegram and WhatsApp chat analysis with SPARK" width="100%">
</p>

[![Awesome Dev Pipeline v2.2.0](https://img.shields.io/badge/standard-Awesome%20Dev%20Pipeline%20v2.2.0-blue.svg)](adr/0001-awesome-dev-pipeline-adoption.md)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Next.js 16](https://img.shields.io/badge/next.js-16%20App%20Router-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688.svg)](https://fastapi.tiangolo.com/)

ChatLens contains two related components: SPARK, a headless Telegram-to-Google Workspace assistant, and a web platform for importing and analyzing Telegram and WhatsApp chat exports. The SPARK settings and academic data in this repository reflect one current deployment; review Section 4 before reusing the daemon elsewhere.

---

## 1. System Architecture

The repository contains two operational stacks:
1. **SPARK PA Daemon (`src/`)**: Autonomous headless assistant watching university Telegram groups, parsing notices, validating timetable constraints, and synchronizing with Google Calendar, Tasks, and Sheets.
2. **ChatLens Platform (`chatlens-v2/`)**: Full-stack multi-channel chat analysis application with a Next.js 16 App Router frontend, a FastAPI/SQLAlchemy (`pgvector`) backend, and asynchronous Celery workers.

```mermaid
graph TD
    subgraph Telegram["Telegram Network"]
        TG_Groups["Approved Telegram Groups / Channels<br/>(SPARK_CHAT_IDS)"]
        TG_Bot["Owner Telegram Bot<br/>(BOT_TOKEN)"]
        TG_Me["Saved Messages<br/>(entity='me')"]
    end

    subgraph Daemon["SPARK PA Daemon (src/)"]
        Listener["Telethon Listener<br/>(Strictly Read-Only)"]
        Dedupe["SHA-256 Deduplicator<br/>(SQLite WAL spark.db)"]
        Regex["Tier-1 Deterministic<br/>Regex Parser (<100µs)"]
        Gemini["Tier-2 Residual Extractor<br/>(gemini-3.5-flash-lite)"]
        Timetable["Timetable Validator<br/>(L1 Cached TOML)"]
        Decision["Decision Engine<br/>(dry / confirm / live)"]
        Formatting["Formatting & Design Engine<br/>(src/formatting/templates.py)"]
        AntiBan["Anti-Ban & Rate Limiter<br/>(R-BAN-1 to R-BAN-5)"]
        Scheduler["Background Workers<br/>(Briefing 07:15 IST, Heartbeat,<br/>Reminders, Callback Poll)"]
    end

    subgraph Workspace["Google Workspace & Storage"]
        GCal["Google Calendar<br/>(Room Overrides, Schedule)"]
        GTasks["Google Tasks<br/>(Deadlines, Action Items)"]
        GSheets["Google Sheets<br/>(Audit Log, Attendance)"]
    end

    TG_Groups -->|Read-only MTProto| Listener
    Listener --> Dedupe
    Dedupe --> Regex
    Regex -->|Residual only| Gemini
    Regex --> Timetable
    Gemini --> Timetable
    Timetable --> Decision
    Decision -->|Auto-write live| GCal
    Decision -->|Auto-write live| GTasks
    Decision -->|Audit record| GSheets
    Decision --> Formatting
    Scheduler --> Formatting
    Formatting --> AntiBan
    AntiBan -->|Outbound Notification| TG_Bot
    AntiBan -->|Fallback| TG_Me
    TG_Bot -->|Inline Callback /undo| Decision
```

---

## 2. Ingestion & Decision Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor TG as Telegram Chat
    participant L as Telethon Listener
    participant G as Input Guard
    participant P as Regex / Gemini Parser
    participant T as Timetable Validator
    participant D as Decision Engine
    participant DB as SQLite spark.db
    actor O as Owner Bot
    participant W as Google Workspace

    TG->>L: Incoming message
    L->>G: Sanitize input and detect prompt injection
    alt Input quarantined
        G-->>L: Block message
        L->>DB: Record quarantine audit and dedup marker
        L-->>O: Alert owner when owner messaging is configured
    else Input clean
        L->>DB: Check message fingerprint in seen
        alt Duplicate within 24 hours
            L-->>TG: Drop duplicate
        else New message
            L->>P: Extract event
            alt Deterministic regex match
                P-->>D: Extracted event from regex
            else Residual text or supported media
                P->>P: Redact PII before Gemini request
                P-->>D: Extracted event from Gemini
            end
            D->>T: Validate timetable-dependent fields
            T-->>D: Verdict and reason
            alt Decision is DRY_RUN
                D->>DB: Record audit outcome
                D->>W: Append audit row to Sheets
                D-->>O: Send dry-run receipt when messaging is available
            else Decision is REVIEW
                D->>DB: Record review outcome
                D->>W: Append audit row to Sheets
                D->>DB: Mark message processed
                D-->>O: Notify owner without an apply button
            else Decision is CONFIRM
                D->>DB: Store pending event
                D->>W: Append audit row to Sheets
                D->>DB: Mark message and event fingerprint processed
                D-->>O: Send Apply / Ignore buttons
                O->>D: Submit owner callback
                alt Owner approves
                    D->>DB: Claim pending item atomically
                    D->>W: Apply approved Calendar or Tasks mutation
                    D->>DB: Persist prior state for undo
                else Owner rejects
                    D->>DB: Dismiss pending item without writing
                end
            else Decision is AUTO
                D->>W: Apply allowlisted Calendar or Tasks mutation
                D->>DB: Persist prior state for undo
                D->>DB: Mark message and event fingerprint processed on success
            end
        end
    end
```

---

## 3. SPARK_MODE State Machine

The daemon's runtime decision is made by `src.ingestion.handlers.decide()`. The order of
evaluation matters: **`dry` records an audit outcome but never mutates Calendar or Tasks; in
`confirm` and `live`, a failed validation goes to review before any write decision.** A valid
event in `live` is auto-applied only when it matches the narrow allowlist below. Audit records
may still be written to SQLite and Google Sheets while `SPARK_MODE=dry`.

```mermaid
stateDiagram-v2
    [*] --> Ingested
    Ingested --> QuarantineCheck

    QuarantineCheck --> Quarantined: Prompt injection detected
    QuarantineCheck --> Parsing: Input is clean

    Parsing --> RegexMatched: Deterministic regex extracts event
    Parsing --> GeminiMatched: Residual or media extraction
    RegexMatched --> ValidateEvent
    GeminiMatched --> ValidateEvent

    ValidateEvent --> DryMode: SPARK_MODE is dry
    ValidateEvent --> ValidationFailed: Verdict failed and mode is not dry
    ValidateEvent --> ConfirmMode: Verdict passed and mode is confirm
    ValidateEvent --> LiveEligibility: Verdict passed and mode is live

    DryMode --> AuditOnly: Log DRY_RUN receipt with no Calendar or Tasks writes
    ValidationFailed --> ReviewOnly: Notify owner with validation reason
    ConfirmMode --> PendingOwner: Request explicit owner approval

    LiveEligibility --> PendingOwner: HOLIDAY, CLASS_CANCELLED, Gemini, or other intent
    LiveEligibility --> TimetableGate: Regex ROOM_OVERRIDE
    LiveEligibility --> AutoWrite: Regex TASK or EXAM_DEADLINE

    TimetableGate --> AutoWrite: Timetable is authoritative and event is validated
    TimetableGate --> PendingOwner: Timetable unavailable but verdict passed

    PendingOwner --> Executed: Authorized owner approves
    PendingOwner --> Dismissed: Owner rejects or request expires
    AutoWrite --> Executed: Apply allowed Calendar or Tasks mutation
    Executed --> CanUndo: Persist prior state and write receipt
    CanUndo --> Undone: Owner invokes /undo for the latest outstanding write

    Quarantined --> [*]
    AuditOnly --> [*]
    ReviewOnly --> [*]
    Dismissed --> [*]
    Undone --> [*]
```

### 3.1 Decision matrix

| Event / condition | `dry` | `confirm` | `live` |
|---|---|---|---|
| Read-only bot command | Available | Available | Available |
| `ROOM_OVERRIDE` from regex; validation passes and authoritative timetable is ready | Audit only; no Calendar/Tasks mutation | Owner approval required | **Auto-write** |
| `ROOM_OVERRIDE` from regex; timetable is missing or marked as sample | Audit only; no Calendar/Tasks mutation | Owner approval required | Owner approval required |
| `TASK` / `EXAM_DEADLINE` from regex | Audit only; no Calendar/Tasks mutation | Owner approval required | **Auto-write** |
| Gemini-derived event | Audit only; no Calendar/Tasks mutation | Owner approval required | Owner approval required |
| `HOLIDAY` / `CLASS_CANCELLED` | Audit only; no Calendar/Tasks mutation | Owner approval required | Owner approval required |
| Timetable-dependent event fails validation | Audit outcome; no Calendar/Tasks mutation | Review notification; no apply button | Review notification; no apply button |
| Other mutation or unsupported intent | Audit only; no Calendar/Tasks mutation | Owner approval or conservative review | Owner approval or conservative review |
| Input is quarantined by the security guard | Block; alert owner when messaging is configured | Block; alert owner when messaging is configured | Block; alert owner when messaging is configured |

**Safety invariants:** Telegram group/channel ingestion is read-only. `dry` can write audit records to SQLite or Sheets but never mutates Calendar or Tasks. Validation failures in `confirm` and `live` never expose an apply action. In `live`, only regex-derived room overrides with an authoritative timetable and regex-derived tasks/deadlines can auto-write. Gemini-derived events, holidays, and class cancellations require explicit owner approval when writes are enabled.

### 3.2 Universal Message Formatting & Design System

All outbound bot communications are governed by the formatting contracts defined in [`docs/MESSAGE_FORMATTING_RULES.md`](docs/MESSAGE_FORMATTING_RULES.md) and executed through the centralized presentation engine in `src/formatting/templates.py`:

1. **The 4-Part Message Anatomy**:
   - **Header Block**: Visual emoji indicator and bold command title with italicized temporal/section context (e.g. `⏰ **Upcoming Deadlines & Academic Intel**` \n `📅 *Sunday, 25 Oct 2026*`).
   - **Body & Card Hierarchy**: Bulleted top-level entries (`•`) with structured tree connectors (`  └ `) and 3-space indented properties (`     • Key: Value`).
   - **Badges & Visual States**: High-contrast, semantic status indicators (`⚠️ Overdue`, `🚨 Due Today!`, `⏳ Due in X days`, `📌 Action Item`, `🟢 Safe`, `🟡 Borderline`, `🔴 Critical`).
   - **Footer & Navigation**: Contextual tip in italics (`💡 *Tip: ...*`) paired with a persistent 2x2 inline keyboard grid.

2. **Link Sanitization & Markdown Safety** (`src/formatting/markdown_safety.py`):
   - Bare URLs are automatically intercepted, categorized, and converted into semantic chips (`🔗 [Google Drive Folder](url)`, `🔗 [Google Form](url)`, `🔗 [CodeTantra Portal](url)`).
   - Unbalanced markdown delimiters (`*`, `` ` ``, `[`, `]`) are safely normalized to eliminate Telegram API `400 Bad Request` parser drops.

3. **Course Notice Consolidation & Semantic Grouping**:
   - Fragmentary announcements spanning multiple chat messages (e.g. repetitive MOOCS certificate reminders) are deduplicated, attributed to their canonical course codes (`25SC2107E`, `25CS2103E`, etc.), and formatted as coherent subject cards.

### 3.3 Telegram Platform Compliance & Anti-Ban Architecture

SPARK operates on personal user sessions and automated bot interfaces, strictly enforcing five non-negotiable anti-ban invariants (`R-BAN-1` through `R-BAN-5`):

- **[R-BAN-1] Leaky-Bucket Rate Limiter**: All outbound network calls to Telegram are throttled via an adaptive token bucket (`src/utils/rate_limiter.py`). Bursts are capped to prevent `FloodWaitError` and automated MTProto account restrictions.
- **[R-BAN-2] Contact Consent & Interaction Scoping**: Group ingestion is strictly read-only. The daemon never posts, reacts, or forwards inside public groups or channel feeds. Outbound delivery is restricted to direct 1:1 conversation with the owner bot or Saved Messages (`"me"`).
- **[R-BAN-3] Startup & Restart Debounce**: System notifications and startup receipts enforce a mandatory 15-minute cooldown persisted in SQLite `meta` (`last_startup_notify_ts`), preventing notification floods during crash loops or supervisor restarts.
- **[R-BAN-4] Monitored Chat Scope Boundary**: The Telethon listener only processes messages from chats explicitly allowlisted in `SPARK_CHAT_IDS`. Empty or unconfigured chat lists immediately refuse startup (exit code 2).
- **[R-BAN-5] Circuit Breaker & Safe Degradation**: Consecutive API errors trigger exponential backoff. If Telegram Bot API delivery fails, the daemon automatically falls back to MTProto Saved Messages or fails closed without crashing the ingestion worker.

### 3.4 Interactive Bot Interface & Proactive Reminders

The bot client (`src/notify/bot.py`) and command dispatcher (`src/ingestion/handlers.py`) provide comprehensive student assistance:

- **Command Directory**:
  - `/today`: Complete 4-slot day schedule with real-time slot indicators (`✅ Done`, `🔴 Live`, `🟡 Next`, `⬡ Upcoming`).
  - `/tomorrow`: Upcoming day schedule with classroom, faculty, section, and type metadata.
  - `/deadlines`: Consolidated view of overdue tasks, today's due items, active deadlines, and action items.
  - `/attendance`: Visual attendance cards with threshold alerts (`🟢 Safe`, `🟡 Borderline`, `🔴 Critical`) and margin calculations.
  - `/status`: System health card with uptime, model name, monitored chat count, ERP identity, and operational mode.
  - `/marks`, `/cgpa`, `/fee`: Instant academic records querying ERP endpoints.
  - `/rescan`: On-demand catch-up rescan of monitored course channels.
  - `/undo`: Atomic reversion of the most recent Google Calendar or Google Tasks write.
  - `/`: Standalone trigger outputting the complete interactive command menu.
- **Quick-Action Navigation**: Every outgoing message includes an interactive 2x2 inline button grid (`[ 📅 Today ] [ 📊 Attendance ]` / `[ ⏰ Deadlines ] [ 🟢 Status ]`), allowing one-tap navigation without typing.
- **Proactive Assessment Reminders**: A dedicated background worker (`run_reminders` in `src/main.py`) continuously scans pending academic events and dispatches pre-class reminder cards to the student on the morning of quizzes, lab evaluations, and assignment deadlines.

---

## 4. Deployment-Specific Data & Safe Customization

Academic data is **not universal**. Course identifiers, aliases, section names, room formats, class
periods, term dates, ERP account settings, and time zones vary by institution and academic year. The
values currently in this repository reflect one deployment and must not be treated as portable defaults.

Before using the SPARK daemon for another institution or term, review the current implementation
and update the relevant sources together:

| Concern | Current source of truth | What to verify |
|---|---|---|
| Course names, official codes, and text aliases | `src/parsing/regex_parser.py`, `src/timetable/__init__.py` | Supported courses, official IDs, aliases, and canonical names |
| Period numbers, period times, room formats, and section assumptions | `src/timetable/__init__.py`, `src/parsing/regex_parser.py` | Actual timetable periods, breaks, rooms, sections, and parsing patterns |
| Active term schedule | TOML file selected by `SPARK_TIMETABLE` (current default: `data/timetable_T04.toml`) | Term, validity dates, course slots, rooms, and faculty |
| Official academic milestones | `src/academic_calendar.py` and `data/calendar_2026_27.toml` | Exam dates, fee deadlines, last instruction day, and other protected dates |
| Time zone and date interpretation | `src/utils/clock.py` and `Dockerfile` | IST is currently hard-coded in Python and the container image; update both and test timestamp conversion before using another timezone |
| ERP account settings | `src/config.py` (`ERP_USERNAME`, `ERP_PASSWORD`) | Configure the target account explicitly; do not reuse the current deployment-specific username fallback |

Some values are currently **defined in code**, not controlled by `.env` alone. Changing
`SPARK_TIMETABLE` does not automatically update the regex course aliases, period-time mappings,
room/section assumptions, time zone, or academic-milestone rules. Verify these dependencies before
claiming another deployment is supported.

### Customization checklist

1. Use an authoritative timetable and academic calendar for the target institution and term.
2. Update the corresponding code/data sources; keep identifiers, parsing rules, time windows, and
   validation logic consistent.
3. Update or add regression tests for course detection, date interpretation, period mapping,
   timetable validation, and milestone-conflict handling.
4. Run the verification suite in Section 8. Keep `SPARK_MODE=dry` until the target deployment's
   valid, invalid, ambiguous, and approval-required cases have been tested.

The safety policy is intended to remain consistent across deployments: community messages are
untrusted input, timetable/calendar mismatches must not be silently applied, and live automatic
writes must stay limited to the explicitly approved policy cases. These rules do not make the
current course parser, timetable, ERP integration, or timezone portable without customization.
## 5. Configuration & Environment Variables

For local SPARK development, copy [`.env.example`](.env.example) to `.env`, replace its sample values, and never commit the real configuration file. The table below documents daemon settings in `src/config.py`; defaults are code defaults unless noted otherwise.

| Variable | Code default | Notes |
|---|---|---|
| `TELEGRAM_API_ID` | `0` | Required at startup; obtain from Telegram's developer portal |
| `TELEGRAM_API_HASH` | Empty | Required at startup; treat as a credential |
| `TELEGRAM_SESSION_STRING` | Empty | Required at startup; contains session credentials |
| `GOOGLE_CREDENTIALS_BASE64` | Empty | Required at startup; base64-encoded Google credentials |
| `GOOGLE_CALENDAR_ID` | `primary` | Target Google Calendar |
| `GOOGLE_SHEET_ID` | Unset | Spreadsheet used by Sheets logging and attendance features |
| `GEMINI_API_KEY` | Empty | Required at startup |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Model used for residual extraction; verify any replacement model before deployment |
| `GEMINI_DAILY_BUDGET` | `50` | Daily budget for Gemini requests |
| `SPARK_MODE` | `dry` for direct execution; `confirm` if unset in Compose | `dry`, `confirm`, or `live`; see Section 3 before enabling writes |
| `SPARK_CHAT_IDS` | Empty | Required at startup; comma-separated allowlist of permitted chat/channel IDs |
| `SPARK_DB` | `spark.db` | SQLite database path; Compose sets `/app/data/spark.db` on its persistent volume |
| `SPARK_MEDIA` | `false` | Media extraction is disabled unless explicitly enabled |
| `SPARK_TIMETABLE` | `data/timetable_T04.toml` | Active timetable file; see Section 4 for other institution-specific assumptions |
| `BOT_TOKEN` | Unset | Required when `SPARK_MODE` is `confirm` or `live` |
| `OWNER_CHAT_ID` | Unset | Owner's private Telegram chat ID; required in `confirm` or `live` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR`; avoid DEBUG in production because it can contain message details |
| `SENTRY_DSN` | Unset | Optional exception monitoring |
| `ERP_USERNAME` | Deployment-specific fallback in source | Not listed in `.env.example`; set explicitly for the target ERP account and do not rely on the current fallback |
| `ERP_PASSWORD` | Empty | Not listed in `.env.example`; set for ERP features that authenticate to the portal and never commit the value |

The root `.env.example` also shows platform-related settings. It currently omits `ERP_USERNAME` and `ERP_PASSWORD`, although the daemon supports both. For the **full Docker Compose stack**, use [`.env.production.example`](.env.production.example) instead: replace its placeholders, configure `POSTGRES_*` and `DATABASE_URL` for the Compose `postgres` service, set Firebase web/admin credentials, and configure `CHATLENS_ALLOWED_EMAILS`. If a database password contains URL-reserved characters, percent-encode it in `DATABASE_URL`.

**Do not run production Compose with sample values.** The Compose service supplies `SPARK_MODE=confirm` when `SPARK_MODE` is not set, which differs from the direct Python default of `dry`. In `confirm` or `live`, the Telegram bot token and owner chat ID must be configured.

## 6. Setup & Development

### 6.1 Prerequisites
- Python 3.12 or newer
- `uv` (Astral Python package manager)
- Node.js 24.12+ and `npm` (required by the resolved Firebase and Vitest dependency engines)
- Docker & Docker Compose (optional for full platform orchestration)

### 6.2 Local Installation
```bash
# Clone the repository
git clone https://github.com/tejaswin-amara/chatlens.git
cd chatlens

# Install Python virtual environment and dependencies
uv sync --all-extras --dev

# Install Frontend dependencies
cd chatlens-v2/frontend && npm ci && cd ../..
```

### 6.3 Helper Setup Scripts
```bash
# Generate Telethon session string
uv run python scripts/generate_session.py

# List accessible Telegram chats to find IDs for SPARK_CHAT_IDS
uv run python scripts/list_chats.py

# Encode Google Service Account credentials to base64
uv run python scripts/google_token.py
```

### 6.4 Running the SPARK PA Daemon
```bash
uv run python -m src.main
```

### 6.5 Running the full stack with Docker Compose

First create a deployment-specific environment file and replace **all** placeholders. For production, point `DOMAIN` and `DOMAIN_NAME` to a DNS name that resolves to this host, and use a valid email for certificate automation. For a local smoke test, set the domain to `localhost`.

```bash
cp .env.production.example .env
mkdir -p secrets
# Place the matching Firebase Admin service-account JSON at secrets/firebase-admin.json
# Edit .env and replace every placeholder, including database, Telegram, Google, Gemini, and Firebase values.
docker compose config --quiet
docker compose up -d --build
```

Do not commit `.env` or `secrets/firebase-admin.json`. `docker compose config --quiet` checks Compose configuration syntax but does not verify that placeholder credentials or third-party services are valid.

Services in `compose.yaml`:

| Service | Purpose / exposure |
|---|---|
| `chatlens-proxy` | Caddy reverse proxy; publishes HTTP/HTTPS on host ports `80` and `443` |
| `chatlens-frontend` | Static-exported Next.js frontend served by Nginx; reached through Caddy |
| `chatlens-backend` | FastAPI backend; host port `8000` is bound to `127.0.0.1` and routes are authenticated in production |
| `chatlens-migration` | One-shot Alembic database migration service |
| `chatlens-daemon` | Background SPARK listener and Google Workspace assistant |
| `chatlens-celery` | Asynchronous processing worker |
| `postgres` | PostgreSQL with `pgvector`; host port `5432` is bound to `127.0.0.1` |
| `redis` | Redis broker and result backend; host port `6379` is bound to `127.0.0.1` |

With a local `DOMAIN=localhost` configuration, open `https://localhost`; Caddy may use a locally issued certificate that your browser does not yet trust. For a public deployment, use the configured domain and ensure DNS and firewall rules point to this host.

## 7. Production Access Control

The ChatLens backend handles private conversation archives and must not be exposed without authentication. When `REQUIRE_AUTH=true` or `ENVIRONMENT=production`, every API route except `GET /api/healthz` requires a valid Firebase ID token and an email listed in `CHATLENS_ALLOWED_EMAILS`.

1. In the Firebase Console, enable Google as a sign-in provider and register a web app.
2. Set all six `NEXT_PUBLIC_FIREBASE_*` variables in `.env` from that web app's configuration.
3. Create a Firebase Admin service-account JSON for the same Firebase project. Store it at the path configured by `FIREBASE_ADMIN_CREDENTIALS_FILE` (default: `./secrets/firebase-admin.json`). Compose mounts this file read-only into the backend; never commit it.
4. Set `CHATLENS_ALLOWED_EMAILS` to the comma-separated list of people authorized to access this instance.
5. Rebuild and start the stack with `docker compose up -d --build` after completing Section 6.5.

The `GET /api/auth/me` endpoint reports the signed-in user's session/allowlist state. The backend fails closed when authentication is required but the ID token, Firebase Admin configuration, or email allowlist is invalid or missing.

**Data-isolation limitation:** the allowlist is an instance-level access gate, not per-user database isolation. All allowlisted users can access the same configured chat dataset. Only allowlist accounts that are permitted to see the same imported conversations.

## 8. Verification & Quality Gates

The repository's canonical full check is defined in `Makefile`. Install the project dependencies and ensure `make`, `gitleaks`, `osv-scanner`, Node.js, and npm are available, then run:

```bash
make check
```

`make check` runs Python linting and formatting, migration linting, the motion/design scan, mypy, the pytest suite with runtime warnings elevated to errors, Gitleaks and OSV dependency scans, and frontend linting, TypeScript checking, Vitest tests, and the production build.

For focused checks:

```bash
# Python tests (integration tests requiring Docker are excluded by the pytest configuration)
uv run pytest -q -W error::RuntimeWarning

# Message design system, handlers, and E2E bot remediation tests
uv run pytest -q tests/test_templates.py tests/test_handlers.py tests/test_e2e_remediation.py

# Python style and type safety
uv run ruff check src tests scripts
uv run mypy src

# Prompt fixture / implementation drift
uv run pytest -q tests/test_prompt_drift.py

# Frontend checks
cd chatlens-v2/frontend
npm run lint
npx tsc --noEmit
npx vitest run
npm run build
```

Do not describe the project as fully verified unless the relevant checks actually pass in the target environment.

## 9. License & Governance
* See [`LICENSE`](LICENSE) for the project's license terms.
* Built under **Awesome Dev Pipeline v2.2.0**.
* Architectural decisions documented in [`adr/`](adr/).
* Threat model documented in [`adr/threat-model.md`](adr/threat-model.md).
