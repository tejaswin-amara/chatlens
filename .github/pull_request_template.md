<!-- Awesome Dev Pipeline v2.2.0 Pull Request Template -->

## Changed
<!-- Bulleted list of all concrete functional and structural changes across components -->
- 

## Decisions
<!-- Explicit rationale for architectural decisions made, fallbacks, tradeoffs, and negative invariant enforcements -->
- 

## Not done
<!-- Explicit boundary definitions of what was intentionally omitted or kept out of scope -->
- 

## Verification Evidence
<!-- Document test run outputs, lint checks, static type checks, and security scans -->

| Check | Tool / Command | Result |
|---|---|---|
| Python Linting | `uv run ruff check src tests scripts chatlens-v2/backend` | PASS |
| Python Formatting | `uv run ruff format --check src tests scripts chatlens-v2/backend` | PASS |
| Static Type Checking | `uv run mypy src scripts benchmarks chatlens-v2/backend` | PASS |
| Python Test Suite | `uv run pytest -q -W error::RuntimeWarning` | PASS |
| Integration Tests | `uv run pytest -q -m integration -W error::RuntimeWarning` | PASS |
| Prompt Drift Test | `uv run pytest -q tests/test_prompt_drift.py` | PASS |
| Architecture & Debt Gates | `check_adrs.py && harvest_debt.py && lint_migration.py && scan_motion.py` | PASS |
| Frontend Quality Gate | `npm test -- --run && npm run lint && npx tsc --noEmit && npm run build` | PASS |
| Secret Scanning | `gitleaks git --redact --no-banner` | PASS |
| Container Build Check | `docker compose build` | PASS |
