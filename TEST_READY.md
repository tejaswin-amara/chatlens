# TEST READY — Remediation Acceptance Test Suite

**Status**: READY  
**Date**: 2026-10-23  
**Test Suite Path**: `tests/test_e2e_remediation.py`  
**Infrastructure Specification**: `TEST_INFRA.md`  

---

## Suite Summary

| Tier | File | Tests Count | Status | Execution Time |
|------|------|:-----------:|:------:|:--------------:|
| **Tier 1: Feature Coverage** | `tests/test_e2e_remediation.py` | 9 | PASS | ~1.40s |
| **Tier 2: Boundary & Corner Cases** | `tests/test_e2e_remediation.py` | 8 | PASS | ~1.15s |
| **Tier 3: Pairwise Combinations** | `tests/test_e2e_remediation.py` | 6 | PASS | ~1.10s |
| **Tier 4: Real-World Scenarios** | `tests/test_e2e_remediation.py` | 5 | PASS | ~1.82s |
| **Total** | **All 4 Tiers** | **28** | **PASS** | **~5.47s** |

---

## Verification Commands

Run full remediation E2E test suite:
```bash
uv run pytest tests/test_e2e_remediation.py -v
```

Verify style, lint, and type compliance:
```bash
uv run ruff check tests/test_e2e_remediation.py
uv run mypy tests/test_e2e_remediation.py
```

---

## Covered Requirements & Acceptance Criteria

- **R1 (Output Format & Greeting Behaviour - §0 Operating Rules)**:
  - Verified zero filler ([R2]) across `/today` and `/tomorrow` responses.
  - Verified standard 4-slot structure ([R3]) with Room, Faculty, Section S-10, Type, Note.
  - Verified status icons today only ([R4]) with progressive live calculation (`✅`, `🔴`, `🟡`, `⬡`) and static `⬡` on `/tomorrow`.
  - Verified stats line ([R9]) format: `📊 [Day] | Wk[N]: [N] academic · [N] lab(s) · [N] non-ERP · Regular instruction`.
  - Verified automatic fallback to `data/timetable_T04.toml` when configured timetable is missing ([R1] No excuses).
- **R2 (Interactive Options & Command Autocomplete)**:
  - Verified automatic injection of default 2x2 quick-action buttons (`[ 📅 Today ] [ 📊 Attendance ] [ ⏰ Deadlines ] [ 🟢 Status ]`) on outgoing replies.
  - Verified inline callback queries (`cmd:<action>`) answer spinner and synthesize command execution.
  - Verified native `setMyCommands` registration of 10 commands on bot startup.
  - Verified standalone `/` command directory trigger.
  - Verified fuzzy command routing with `difflib` routing typos (`/todat` -> `/today`, `/tomorow` -> `/tomorrow`).
- **R3 (Startup Debounce & Background Persistence)**:
  - Verified 15-minute startup notification cooldown in SQLite `meta` table.
  - Verified WAL journal mode and concurrency-safe transactions with `PRAGMA busy_timeout = 5000`.
