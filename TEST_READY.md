# TEST READY — Opaque-Box Acceptance Test Suite

**Status**: READY  
**Date**: 2026-10-16  
**Test Suite Path**: `tests/e2e/`  
**Infrastructure Specification**: `TEST_INFRA.md`  

---

## Suite Summary

| Tier | File | Tests Count | Status | Execution Time |
|------|------|:-----------:|:------:|:--------------:|
| **Tier 1: Feature Coverage** | `tests/e2e/test_tier1_features.py` | 26 | PASS | ~0.50s |
| **Tier 2: Boundary & Corner Cases** | `tests/e2e/test_tier2_boundaries.py` | 25 | PASS | ~0.95s |
| **Tier 3: Pairwise Combinations** | `tests/e2e/test_tier3_combinations.py` | 6 | PASS | ~0.37s |
| **Tier 4: Real-World Scenarios** | `tests/e2e/test_tier4_scenarios.py` | 5 | PASS | ~0.51s |
| **Total** | **All 4 Tiers** | **62** | **PASS** | **~2.3s** |

---

## Verification Commands

Run full E2E test suite:
```bash
uv run pytest -q tests/e2e/
```

Verify style and lint compliance:
```bash
uv run ruff check tests/e2e/
```

Run live cluster verification against deployed stack:
```bash
LIVE_E2E=1 BASE_URL=http://localhost uv run pytest -q tests/e2e/
```

---

## Covered Requirements & Acceptance Criteria

- **R1 (Reverse Proxy & Routing)**: Verified HTTP 80/443 ingress, `/` -> frontend, `/api/*` -> backend, `/ws*` -> backend, static asset loading at root without 404s, relative origin API calls.
- **R2 (Database Bootstrapping & Migrations)**: Verified `01-init-pgvector.sql` extension creation idempotency, Alembic configuration, expand/contract linter compliance, Celery broker URL resolution, shared uploads volume.
- **R3 (Persistence & Secrets)**: Verified SPARK SQLite WAL mode persistence, integrity check commands, status bridge read-only connection.
- **R4 (Reliability & Healthchecks)**: Verified container healthcheck contracts (`pg_isready`, `redis-cli ping`, `/api/healthz`), restart policies, and logging drivers.
