<!-- Awesome Dev Pipeline v2.0.0 Pull Request Template -->

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
| Python Linting | `uv run ruff check ...` | PASS |
| Python Formatting | `uv run ruff format --check ...` | PASS |
| Static Type Checking | `uv run mypy src` | PASS |
| Python Test Suite | `uv run pytest -q -W error::RuntimeWarning` | PASS |
| Prompt Drift Test | `uv run pytest -q tests/test_prompt_drift.py` | PASS |
| Frontend Lint & Build | `npm run lint && npx tsc --noEmit && npm run build` | PASS |
| Secret Scanning | `gitleaks git --redact --no-banner` | PASS |
