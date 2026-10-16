# Test Infrastructure Specification: ChatLens v2 & SPARK PA Daemon

## 1. Overview & Architecture
This test infrastructure defines an opaque-box End-to-End (E2E) acceptance testing suite for the ChatLens v2 and SPARK PA Daemon production deployment.

The suite adheres to the 4-Tier testing taxonomy:
1. **Tier 1 — Core Feature Coverage**: Direct verification of primary interface contracts (>=5 tests per feature area).
2. **Tier 2 — Boundary & Corner Cases**: Stressing edge conditions, malformed payloads, rate boundaries, and fault fallbacks (>=5 tests per feature area).
3. **Tier 3 — Cross-Feature Combinations**: Pairwise validation across subsystem boundaries (reverse proxy, static assets, database, worker queue, persistence volume).
4. **Tier 4 — Real-World Application Scenarios**: Multi-step user journeys and operational lifecycles from ingress to persistence.

### Dual Execution Architecture
The test harness (`tests/e2e/harness.py`) supports dual operational modes:
- **Offline / Staging Simulation Mode (Default)**: Executes instantly in developer environments or CI pipelines without requiring live external network access, Telegram credentials, or a running Docker daemon. Emulates the reverse proxy layer (Caddy routing), frontend static asset distribution (Nginx rules), in-memory async database transactions, and SPARK SQLite WAL mode isolation.
- **Live Cluster Mode (`LIVE_E2E=1`)**: When enabled via environment variable, redirects the opaque-box HTTP client to the live reverse proxy ingress (`BASE_URL`, defaulting to `http://localhost`), issuing live network requests across running containers.

---

## 2. Directory Layout & Artifact Index

```
kind-faraday/
├── TEST_INFRA.md                   # This infrastructure specification
├── TEST_READY.md                   # E2E test suite readiness publication
└── tests/
    └── e2e/
        ├── __init__.py             # Package marker
        ├── conftest.py             # Pytest fixtures & lifecycle hooks
        ├── harness.py              # Dual-mode HTTP client, proxy/asset simulator & parsers
        ├── test_tier1_features.py  # Tier 1: Core Feature Coverage (26 tests)
        ├── test_tier2_boundaries.py# Tier 2: Boundary & Corner Cases (25 tests)
        ├── test_tier3_combinations.py # Tier 3: Pairwise Subsystem Combinations (6 tests)
        └── test_tier4_scenarios.py # Tier 4: Real-World User Scenarios (5 tests)
```

---

## 3. Tier Coverage Matrix

| Tier | File | Tests | Covered Areas / Scenarios |
|------|------|:-----:|---------------------------|
| **Tier 1** | `test_tier1_features.py` | 26 | **F1**: Reverse proxy routing (`/` to frontend, `/api/*` to backend, `/ws*`, Caddyfile syntax, TLS/compression).<br>**F2**: Frontend static assets (`/_next/static/*` 200s, SPA route fallback, relative origin API calls, cache headers).<br>**F4/F5**: Database & Alembic (pgvector SQL init, Alembic config, schema linting, content_hash unique constraint, 768-dim vector type).<br>**F6**: Celery & Redis (broker URL resolution, result backend, Redis ping healthcheck, shared volume, task status polling).<br>**F8/F9**: Persistence & Healthchecks (SQLite WAL journal mode, integrity checks, status bridge `/api/spark/status`, container healthchecks, restart policies). |
| **Tier 2** | `test_tier2_boundaries.py` | 25 | **Proxy**: Percent-encoding, method not allowed (405), 404 JSON handling, URI >2048 chars, slash normalization.<br>**Static Assets**: Traversal blocking (`..`), missing asset 404, query string cache busting, nested SPA paths, HEAD method.<br>**Database**: Rerun idempotency, metadata existing resilience, null embedding vectors, hash collision rejection, destructive DDL linter fence.<br>**Worker**: Empty task ID, broker connection loss fallback, payload >50MB (413), 0-byte upload, invalid platform parameter.<br>**Persistence**: Missing DB offline status, corrupt DB integrity failure detection, read-only mode enforcement, empty tables handling, 50 rapid healthcheck requests (<5s). |
| **Tier 3** | `test_tier3_combinations.py` | 6 | **Pairwise 1**: Frontend SPA calling backend API through reverse proxy.<br>**Pairwise 2**: Proxy TLS termination forwarding upstream headers (`X-Forwarded-Proto`, `X-Forwarded-For`).<br>**Pairwise 3**: Schema migrations executing prior to backend processing data requests.<br>**Pairwise 4**: Backend chat upload saving to shared volume consumed by Celery worker.<br>**Pairwise 5**: SPARK daemon SQLite WAL concurrency with backend status bridge.<br>**Pairwise 6**: Celery background task state publication reflected in API poll endpoint. |
| **Tier 4** | `test_tier4_scenarios.py` | 5 | **Scenario 1**: Initial cold boot and stack health probe convergence.<br>**Scenario 2**: Complete web browser user journey (root load, asset chunks, API telemetry, chat sidebar, deep route refresh).<br>**Scenario 3**: Chat upload, asynchronous task polling, and data query lifecycle.<br>**Scenario 4**: SPARK PA assistant message ingestion, container restart, and state persistence.<br>**Scenario 5**: Reverse proxy dynamic domain failover, TLS termination, and error boundary isolation. |
| **Total** | | **62** | **100% Pass Rate Across All Tiers** |

---

## 4. Execution Instructions

### Running the E2E Test Suite (Offline Simulation)
```bash
uv run pytest -q tests/e2e/
```

### Running Specific Tiers
```bash
uv run pytest -q tests/e2e/test_tier1_features.py
uv run pytest -q tests/e2e/test_tier2_boundaries.py
uv run pytest -q tests/e2e/test_tier3_combinations.py
uv run pytest -q tests/e2e/test_tier4_scenarios.py
```

### Running Live Cluster Verification
Once the container stack is booted via `docker compose up -d`:
```bash
LIVE_E2E=1 BASE_URL=http://localhost uv run pytest -q tests/e2e/
```

### Linting & Code Hygiene
```bash
uv run ruff check tests/e2e/
```

---

## 5. Invariant Gates & Quality Enforcements
1. **Network Boundary**: Tests never initiate external network calls to Telegram, Google, or Gemini during automated suite runs (mocked at adapter boundaries).
2. **Persistence Integrity**: State files are tested against SQLite WAL mode and verified with `PRAGMA integrity_check`.
3. **Case-Insensitive HTTP Headers**: `E2EResponse` uses RFC 7230 compliant `CaseInsensitiveHeaderDict` ensuring cross-platform stability.
4. **Zero Extra Dependencies**: The test harness relies strictly on standard library, `httpx`, `fastapi.testclient`, `sqlalchemy`, and existing project modules without introducing external YAML or testing dependencies.
