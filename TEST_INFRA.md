# Test Infrastructure Specification: ChatLens PA Daemon Remediation

## 1. Overview & Architecture
This test infrastructure defines the opaque-box End-to-End (E2E) acceptance testing suite for the ChatLens PA Daemon and Telegram Bot remediation per `ORIGINAL_REQUEST.md` (2026-10-23T05:12:11Z) and `PROJECT.md`.

The suite operates at the public boundary of the assistant:
- **Telegram Bot Command Ingress** (`handle_bot_command`): Evaluates owner commands, command stripping, autocomplete directory, and fuzzy matching.
- **Inline Callback Interaction** (`handle_bot_callback`): Evaluates callback query interception, spinner dismissal (`answerCallbackQuery`), and synthetic command execution.
- **Native Autocomplete API** (`bot.set_my_commands`): Evaluates Telegram `setMyCommands` payload structure and command definitions.
- **Timetable Engine & §0 Formatter** (`src/timetable`): Evaluates fallback mechanics, zero conversational filler ([R2]), 4-slot layout ([R3]), live status icons ([R4]), and stats line calculation ([R9]).
- **SQLite Concurrency & Startup Debounce** (`src/main.py`, `src/utils/deduplication.py`): Evaluates persistent 15-minute notification cooldown and WAL mode integrity.

All tests operate 100% offline with zero external network dependencies, isolating temporary SQLite databases in WAL mode and mocking network adapter boundaries.

---

## 2. Directory Layout & Artifact Index

```
kind-faraday/
├── TEST_INFRA.md                 # Test infrastructure specification (this document)
├── TEST_READY.md                 # E2E test suite readiness publication
└── tests/
    ├── test_e2e_remediation.py   # Remediation Opaque-Box E2E Suite (Tiers 1–4, 28 tests)
    └── e2e/                      # Deployment & cluster acceptance suites
```

---

## 3. Tier Coverage Matrix (`tests/test_e2e_remediation.py`)

| Tier | Tests | Covered Features & Verification Focus |
|------|:-----:|----------------------------------------|
| **Tier 1: Core Feature Coverage** | 9 | **F1.1**: Timetable fallback to `data/timetable_T04.toml` when configured path is missing.<br>**F1.2 - F1.6**: `/today` 4-slot format (Room, Faculty, Section S-10, Type, Note), zero filler, live status icons (`✅`, `🔴`, `🟡`, `⬡`), and stats line (`📊 Monday \| Wk1: ...`).<br>**F1.7**: `/tomorrow` command with static `⬡` icons (no premature completion icons).<br>**F2.1**: Default 2x2 quick-action buttons injection on outgoing responses.<br>**F2.2**: `cmd:<action>` callback queries answering spinner and executing synthetic commands.<br>**F2.3**: Native `setMyCommands` registering all 10 commands.<br>**F2.4**: Standalone `/` command directory trigger.<br>**F2.5**: Fuzzy routing matching typos (`/todat` -> `/today`, `/tomorow` -> `/tomorrow`).<br>**F3.1 - F3.2**: Startup debounce 15-minute cooldown in SQLite `meta` table. |
| **Tier 2: Boundary & Corner Cases** | 8 | **Empty Schedule**: Sunday clean response with friendly non-error copy.<br>**All Cancelled**: Complete course cancellation showing `🔴` and note `❌ Class cancelled`.<br>**Exact Debounce Bounds**: Cooldown active at 899.9s vs expired at 900.1s.<br>**Unrecognized Commands**: Unmatched command strings gracefully fallback without crashing.<br>**Unauthorized Senders**: Strict isolation ignoring commands and callbacks from stranger chat IDs.<br>**Time Boundary - Morning**: At 07:00 IST before classes, P1 is `🟡` and remainder are `⬡`.<br>**Time Boundary - Evening**: At 21:00 IST after instruction, all 8 periods show `✅`.<br>**SQLite Concurrency**: Verifies WAL journal mode and concurrency-safe transactions. |
| **Tier 3: Cross-Feature Combinations** | 6 | **Pairwise 1**: Callback query `cmd:today` driving schedule formatting and attaching buttons.<br>**Pairwise 2**: Callback query `cmd:tomorrow` driving tomorrow schedule with static icons.<br>**Pairwise 3**: Startup debounce active during daemon restart combined with immediate `/status` command.<br>**Pairwise 4**: Fuzzy routing (`/todat`) resolving when SQLite dynamic room overrides are active.<br>**Pairwise 5**: Standalone `/` menu trigger followed by `cmd:deadlines` callback query.<br>**Pairwise 6**: Resilient recovery when `meta` table holds corrupt non-numeric timestamps. |
| **Tier 4: Real-World User Journeys** | 5 | **Scenario 1**: Student morning boot journey (daemon start -> `/` menu -> `cmd:today` schedule -> `cmd:status` telemetry).<br>**Scenario 2**: Room override notice -> student typo `/todat` -> override reflected in Lab slot -> student checks `/tomorrow`.<br>**Scenario 3**: Progressive status calculation throughout day (morning `🟡` -> in-progress `🔴` -> evening `✅`).<br>**Scenario 4**: Daemon power failure, 18-minute reboot (notified), rapid reboot (debounced), and deadlines check.<br>**Scenario 5**: 2x2 interactive button consistency verified across every command reply. |
| **Total** | **28** | **100% Pass Rate Across All 4 Tiers** |

---

## 4. Execution & Verification Commands

### Running the Remediation Acceptance Suite
```bash
uv run pytest tests/test_e2e_remediation.py -v
```

### Running Specific Tiers
```bash
uv run pytest tests/test_e2e_remediation.py -k "test_tier1"
uv run pytest tests/test_e2e_remediation.py -k "test_tier2"
uv run pytest tests/test_e2e_remediation.py -k "test_tier3"
uv run pytest tests/test_e2e_remediation.py -k "test_tier4"
```

### Static Analysis & Linter Verification
```bash
uv run ruff check tests/test_e2e_remediation.py
uv run mypy tests/test_e2e_remediation.py
```

---

## 5. Invariant Gates & Quality Enforcements
1. **Zero Network Egress**: Telegram Bot API and Telethon calls are strictly mocked at adapter boundaries.
2. **Deterministic Time Control**: Current time is controlled via `src.utils.clock` to verify period calculations reliably.
3. **Isolated Persistence**: Tests execute against ephemeral SQLite databases, validating WAL mode and `PRAGMA busy_timeout = 5000`.
4. **Style & Hygiene**: 100% compliant with PEP 8 and project `ruff` configuration (line length <= 100, clean imports).
