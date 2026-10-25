# Project: ChatLens PA Daemon & Telegram Bot Architecture

## Architecture
- **Daemon Ingestion & Background Workers** (`src/main.py`): Supervises Telethon listener for read-only group messages, runs background `bot_callback_poll()`, sets native bot commands on startup, runs the daily morning `briefing_loop` (07:15 IST), executes periodic `heartbeat_loop()`, runs proactive `run_reminders()` assessment daemon, and manages startup debounce via SQLite `meta` table.
- **Universal Message Formatting & Design System** (`src/formatting/templates.py`, `src/formatting/markdown_safety.py`): Centralized presentation engine implementing the 4-part message anatomy (Header, Body/Cards, Badges, Footer/Nav) and rules `R-UI-1` through `R-UI-7` defined in `docs/MESSAGE_FORMATTING_RULES.md`. Provides executive cards for deadlines, schedules, system status, attendance analytics, and proactive reminders with link sanitization and balanced token safety.
- **Bot Communication & Anti-Ban Architecture** (`src/notify/bot.py`, `src/utils/circuit_breaker.py`): Minimalist standard library `urllib.request` client for Telegram Bot API with token redaction, exponential backoff, auto Markdown fallback, default 2x2 quick-action inline keyboard, and `R-BAN-1` to `R-BAN-5` compliance guardrails (leaky-bucket rate limiting, contact consent, restart debounce, chat scope boundary, circuit breaker).
- **Command Handling & Scheduling** (`src/ingestion/handlers.py`): Dispatches owner commands (`/today`, `/tomorrow`, `/attendance`, `/deadlines`, `/status`, `/marks`, `/cgpa`, `/fee`, `/rescan`, `/undo`, `/`), enforces §0 Operating Rules, executes fuzzy routing with `difflib`, and synthesizes inline button callbacks.
- **Timetable & Overrides** (`src/timetable/__init__.py`): Loads KLEF timetable data with automatic fallback to `data/timetable_T04.toml`, validates slots and periods, applies dynamic SQLite overrides, and formats 4-slot day schedules.
- **Persistence & Deduplication** (`src/utils/deduplication.py`, `src/utils/db.py`): SQLite storage with WAL mode and `busy_timeout = 5000` for message deduplication, dynamic timetable overrides, and generic `meta` key-value properties (`last_startup_notify_ts`, `last_heartbeat`).
- **Process Supervisor** (`scripts/run_daemon.ps1`): PowerShell 5.1/7+ supervisor with single-instance detection, auto-restart on crashes with exponential backoff, `-Background` process execution, `-HealthCheck` validation, `-Status`, and `-Stop`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1.1 Timetable Fallback | Automatic fallback to `data/timetable_T04.toml` if custom timetable missing/unconfigured ([R1] No Excuses) | M1 | survey |
| 2 | F1.2 Zero Filler | Output starts immediately without pleasantries or conversational filler ([R2]) | M1 | survey |
| 3 | F1.3 4-Slot Structure | Standardized 4-slot structure with Room, Faculty, Section, Type, Note for `/today` and `/tomorrow` ([R3]) | M1 | survey |
| 4 | F1.4 Status Icons | Live status icons (`✅`, `🔴`, `🟡`, `⬡`) for `/today`; static `⬡`/`🔴` for `/tomorrow` ([R4] Today Only) | M1 | survey |
| 5 | F1.5 Stats Line | Stats line appended to full day outputs: `📊 [Day] \| Wk[N]: ...` ([R9]) | M1 | survey |
| 6 | F1.6 Live Calculation | Dynamic live computation from current IST date and time ([R6]) | M1 | survey |
| 7 | F1.7 `/tomorrow` Command | Add `/tomorrow` to `recognized_commands` and dispatch via unified schedule formatter | M1 | survey |
| 8 | F2.1 Quick-Action Buttons | 2x2 grid (`[ 📅 Today ] [ 📊 Attendance ]` / `[ ⏰ Deadlines ] [ 🟢 Status ]`) on outgoing replies | M2 | survey |
| 9 | F2.2 Inline Callbacks | Intercept `cmd:<action>` callback queries, dismiss spinner with `answer_callback`, synthesize slash commands | M2 | survey |
| 10 | F2.3 Autocomplete Commands | Native `setMyCommands` registration of 10 commands on bot startup | M2 | survey |
| 11 | F2.4 Standalone `/` Trigger | Sending `/` outputs complete interactive command directory with quick-action buttons | M2 | survey |
| 12 | F2.5 Fuzzy Command Routing | Resilient fuzzy matching using `difflib.get_close_matches(cutoff=0.75)` routing typos | M2 | survey |
| 13 | F3.1 Startup Debounce | Persist `last_startup_notify_ts` in SQLite `meta` table with 15-minute cooldown to prevent spam across restarts | M3 | survey |
| 14 | F3.2 Meta KV Store Reliability | Concurrency-safe `meta` table operations with WAL mode and `busy_timeout = 5000` | M3 | survey |
| 15 | F3.3 PowerShell Daemon Runner | `scripts/run_daemon.ps1` with PS 5.1 compatibility, auto-restart, backoff, `-Background`, `-HealthCheck`, `-Status`, `-Stop` | M3 | survey |
| 16 | F4.1 Opaque-Box E2E Tests | Requirement-driven test suite across Tiers 1–4 verifying all bot commands, formats, callbacks, and debounce | E2E Track | survey |
| 17 | F4.2 Final Gate & Hardening | 100% pass on pytest, ruff, mypy, and adversarial coverage hardening (Tier 5) | M4 | survey |
| 18 | F5.1 Universal Message Templates | Standardized 4-part message anatomy, tree connectors (`└`), and semantic emoji chips (`src/formatting/templates.py`) | M5 | spec |
| 19 | F5.2 URL Sanitization & Link Chips | Automatic extraction and formatting of bare links into readable markdown chips (`src/formatting/markdown_safety.py`) | M5 | spec |
| 20 | F5.3 Course Notice Consolidation | Semantic grouping of fragmentary messages (e.g. MOOCS certificates) by course subject | M5 | spec |
| 21 | F5.4 Proactive Assessment Reminders | Automated background worker (`run_reminders`) scanning pending assignments and alerting before classes | M5 | spec |
| 22 | F5.5 Anti-Ban Compliance Rules | Formal implementation of `R-BAN-1` through `R-BAN-5` (leaky-bucket rate limiter, scope boundaries, circuit breaker) | M5 | spec |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Build opaque-box test suite (Tiers 1–4) in `tests/test_e2e_remediation.py` | none | DONE |
| 1 | Schedule Formatting & §0 Operating Rules | F1.1 - F1.7: Unified schedule formatter, `/tomorrow` command, status icons, stats line | none | DONE |
| 2 | Interactive Buttons & Autocomplete | F2.1 - F2.5: Quick-action buttons, `cmd:<action>` callbacks, `setMyCommands`, standalone `/`, fuzzy routing | M1 | DONE |
| 3 | Startup Debounce & Persistence Runner | F3.1 - F3.3: 15-min debounce verification, `meta` table store, `scripts/run_daemon.ps1` overhaul | M2 | DONE |
| 4 | Final Integration & E2E Verification | F4.1 - F4.2: 100% E2E test suite pass (Tiers 1–4) and Tier 5 adversarial coverage hardening | E2E, M3 | DONE |
| 5 | Enterprise Message Design & Proactive Intel | F5.1 - F5.5: Centralized template engine, link safety, deadlines UI redesign, proactive reminder daemon, anti-ban invariants | M4 | DONE |

## Interface Contracts
### `src/formatting/templates.py` ↔ `src/ingestion/handlers.py` & `src/main.py`
- `render_deadlines_card(today_date: date, milestones: list[dict], pending_items: list[dict]) -> str`:
  - Renders consolidated deadlines organized into Overdue, Due Today, Active Deadlines, and Action Items with course attribution and link chips.
- `render_day_schedule(target_date: date, slots: list[dict], active_deadlines: list[str] | None = None, is_today: bool = True, term: str = "T04", section: str = "S-10") -> str`:
  - Standardized 4-slot structure with live status icons, room, faculty, section, type, and stats footer.
- `render_status_card(now_dt: datetime, spark_mode: str, chat_count: int, model_name: str, erp_user: str, owner_chat_id: int | str, uptime_str: str = "Active", extra_metrics: dict | None = None) -> str`:
  - Executive status dashboard with active operational metrics and health status.
- `render_attendance_card(records: list[dict], now_dt: datetime | None = None) -> str`:
  - Visual attendance card with threshold badges (`🟢 Safe`, `🟡 Borderline`, `🔴 Critical`) and margin alerts.
- `render_proactive_reminder(course_name: str, course_code: str, period: int, summary: str, intent: str = "ASSESSMENT") -> str`:
  - Actionable notification card delivered before classes for due quizzes, assignments, or evaluations.
- `get_standard_navigation_buttons() -> list[list[dict[str, str]]]`:
  - Standard 2x2 inline navigation button grid.

### `src/notify/bot.py` ↔ `src/ingestion/handlers.py` & `src/main.py`
- `BotClient.send(text: str, chat_id: int | str | None = None, buttons: list[list[dict[str, str]]] | None = None) -> dict`:
  - Default `buttons=None` injects standard 2x2 quick action buttons.
  - `buttons=[]` suppresses button generation (used for startup notifications).
- `BotClient.answer_callback(callback_query_id: str, text: str | None = None) -> dict`:
  - Dismisses client spinner.
- `BotClient.set_my_commands() -> dict`:
  - Registers slash commands with Telegram Bot API on startup.

### `src/utils/deduplication.py` ↔ `src/main.py` & `scripts/run_daemon.ps1`
- `meta` table schema: `CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)`
- Key `last_startup_notify_ts`: string float timestamp of last startup notification.
- Key `last_heartbeat`: string float timestamp of last daemon heartbeat.

## Code Layout
- `src/main.py`: Main daemon lifecycle, background workers (`briefing`, `heartbeat`, `reminders`, `bot_callback_poll`), debounce check.
- `src/formatting/`: Centralized presentation engine.
  - `templates.py`: Outbound UI card renderers (`deadlines`, `schedule`, `status`, `attendance`, `reminders`).
  - `markdown_safety.py`: URL sanitization, link chips, token balancing.
- `src/notify/bot.py`: Telegram Bot API wrapper, button building, command registration, token redaction.
- `src/ingestion/handlers.py`: Command routing (`handle_bot_command`), callback dispatch (`handle_bot_callback`), menu rendering.
- `src/timetable/__init__.py`: Timetable parsing, schedule formatting, period & course constants.
- `src/utils/deduplication.py`: SQLite `meta` operations, message deduplication, dynamic overrides.
- `src/utils/clock.py`: Centralized IST timezone helpers (`now_ist()`, `today_ist()`).
- `scripts/run_daemon.ps1`: Windows supervisor script.
- `tests/`: Offline test suite (`test_templates.py`, `test_handlers.py`, `test_bot.py`, `test_e2e_remediation.py`, `test_timetable.py`).
