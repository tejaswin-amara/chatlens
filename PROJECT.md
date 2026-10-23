# Project: ChatLens PA Daemon & Telegram Bot Remediation

## Architecture
- **Daemon Ingestion & Bot Loop** (`src/main.py`): Supervises Telethon listener for read-only group messages, runs background `bot_callback_poll()`, sets native bot commands on startup, and manages startup debounce via SQLite `meta` table.
- **Bot Communication** (`src/notify/bot.py`): Minimalist standard library `urllib.request` client for Telegram Bot API with token redaction, exponential backoff, auto Markdown fallback, and default 2x2 quick-action inline keyboard.
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

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Build opaque-box test suite (Tiers 1–4) and publish `TEST_READY.md` | none | DONE |
| 1 | Schedule Formatting & §0 Operating Rules | F1.1 - F1.7: Unified schedule formatter, `/tomorrow` command, status icons, stats line | none | DONE |
| 2 | Interactive Buttons & Autocomplete | F2.1 - F2.5: Quick-action buttons, `cmd:<action>` callbacks, `setMyCommands`, standalone `/`, fuzzy routing | M1 | IN_PROGRESS (Remediation) |
| 3 | Startup Debounce & Persistence Runner | F3.1 - F3.3: 15-min debounce verification, `meta` table store, `scripts/run_daemon.ps1` overhaul | M2 | PLANNED |
| 4 | Final Integration & E2E Verification | F4.2: 100% E2E test suite pass (Tiers 1–4) and Tier 5 adversarial coverage hardening | E2E, M3 | PLANNED |

## Interface Contracts
### `src/timetable/__init__.py` ↔ `src/ingestion/handlers.py`
- `format_day_schedule(target_date: date, now_dt: datetime | None = None, timetable: Timetable | None = None) -> str`:
  - `target_date`: The calendar date to format.
  - `now_dt`: If provided (for today), calculates live status icons (`✅`, `🔴`, `🟡`, `⬡`). If `None` (for tomorrow), all non-cancelled classes receive `⬡`, and cancelled receive `🔴`.
  - Return: The exact 4-slot structured schedule string with metadata lines and stats line.
- `PERIOD_TIMES: dict[int, tuple[str, str, int, int, int, int]]`:
  - Standardized KLEF periods: 1, 2, 3, 4, 5, 7, 8, 9 (No P6).
- `COURSE_INFO: dict[str, tuple[str, str]]`:
  - Canonical subject short code -> `(course_code, full_name)`.

### `src/notify/bot.py` ↔ `src/ingestion/handlers.py` & `src/main.py`
- `BotClient.send(text: str, chat_id: int | str | None = None, buttons: list[list[dict[str, str]]] | None = None) -> dict`:
  - Default `buttons=None` injects standard 2x2 quick action buttons.
  - `buttons=[]` suppresses button generation (used for startup notifications).
- `BotClient.answer_callback(callback_query_id: str, text: str | None = None) -> dict`:
  - Dismisses client spinner.
- `BotClient.set_my_commands() -> dict`:
  - Registers the 10 slash commands with Telegram Bot API on startup.

### `src/utils/deduplication.py` ↔ `src/main.py` & `scripts/run_daemon.ps1`
- `meta` table schema: `CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)`
- Key `last_startup_notify_ts`: string float timestamp of last startup notification.
- Key `last_heartbeat`: string float timestamp of last daemon heartbeat.

## Code Layout
- `src/main.py`: Main daemon lifecycle, debounce check, `bot_callback_poll()`.
- `src/notify/bot.py`: Telegram Bot API wrapper, button building, command registration.
- `src/ingestion/handlers.py`: Command routing (`handle_bot_command`), callback dispatch (`handle_bot_callback`), menu rendering.
- `src/timetable/__init__.py`: Timetable parsing, schedule formatting (`format_day_schedule`), period & course constants.
- `src/utils/deduplication.py`: SQLite `meta` operations, message deduplication, dynamic overrides.
- `scripts/run_daemon.ps1`: Windows supervisor script.
- `tests/`: Offline test suite (unit tests, handlers tests, bot tests, E2E tests).
