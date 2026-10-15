# ADR 0001: Adoption of Awesome Dev Pipeline v2.0.0

* Status: accepted
* Deciders: Autonomous Engineering Team, Principal Software Engineer
* Date: 2026-10-15

## Context and Problem Statement
The `tejaswin-amara/chatlens` repository previously suffered from architectural drift, legacy artifacts (v1 Flask app in `chatlens/`, static Next export dumps in root and `docs/`), loose dependencies (`requirements.txt`, unpinned GitHub Actions), and inconsistent runtime behavior between the headless Telegram daemon (`src/`), the FastAPI backend (`chatlens-v2/backend`), and the Next.js frontend (`chatlens-v2/frontend`).

We need a standardized, deterministic, and secure engineering framework that guarantees fast feedback loops, strict type safety, zero secret leaks, reproducible containerized execution, and robust CI supply-chain security.

## Decision Drivers
* Strict isolation of operational environments (headless daemon vs web application).
* Deterministic dependency resolution across Python (`uv`) and Node.js (`npm`).
* Supply chain hardening against CI compromise (pinning GitHub Actions to 40-character commit SHAs).
* Prevention of runtime regressions and secret leakage across all logging and error reporting systems.

## Considered Options
* Option 1: Ad-hoc maintenance of existing scripts, loose constraints, and mixed runtime structures.
* Option 2: Full adoption of Awesome Dev Pipeline v2.0.0 with standardized directory layout, lockfiles, strict linting (`ruff`), static typing (`mypy`), containerization, and automated quality gates.

## Decision Outcome
Chosen option: **Option 2 (Awesome Dev Pipeline v2.0.0)**.

### Positive Consequences
* Python ecosystem unified under `uv` with Python 3.12, strict `ruff` rules, and `mypy` type checking.
* Frontend modernized under Next.js 16 App Router with standardized `@/...` import paths.
* All third-party GitHub Actions pinned to immutable 40-character commit SHAs.
* Comprehensive test coverage running with `-W error::RuntimeWarning` to eliminate async leaks and event loop warnings.

### Negative Consequences / Tradeoffs
* Stricter pre-commit and CI gates require clean linting and formatting on all touched files before merge.

## Confirmation & Verification
* Full test suite runs green via `uv run pytest -q -W error::RuntimeWarning`.
* Static analysis passes via `uv run ruff check` and `uv run mypy src`.
* Frontend builds cleanly via `npm run build` with zero TypeScript or ESLint errors.
