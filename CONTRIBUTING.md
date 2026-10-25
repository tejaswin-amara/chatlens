# Contributing to ChatLens

This repository contains the SPARK Telegram-to-Google-Workspace daemon and the ChatLens web platform. Keep changes focused, preserve the daemon/web-stack boundary, and run the checks relevant to your change before opening a pull request.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 24.12+ and npm
- Docker Compose for local PostgreSQL/Redis services or a full-stack run
- `make`, `gitleaks`, and `osv-scanner` for the full quality gate

## Set up

From the repository root:

```bash
git clone https://github.com/tejaswin-amara/chatlens.git
cd chatlens
uv sync --all-extras --dev
cd chatlens-v2/frontend
npm ci
cd ../..
```

For local development, configure `.env` from [`.env.example`](.env.example). For the full Compose stack, use [`.env.production.example`](.env.production.example) and replace every placeholder before starting services. Never commit real environment files or credentials.

Start only the database and queue for local development:

```bash
docker compose up -d postgres redis
```

The root `compose.yaml` is the canonical Compose definition. To run the full stack, follow the deployment and authentication instructions in the root [README](README.md); do not use a second Compose file from a subdirectory.

## Verification

Run the complete repository gate when possible:

```bash
make check
```

For focused checks:

```bash
uv run pytest -q -W error::RuntimeWarning
uv run ruff check src tests scripts chatlens-v2/backend
uv run ruff format --check src tests scripts chatlens-v2/backend
uv run mypy src scripts benchmarks chatlens-v2/backend
```

For frontend changes, from `chatlens-v2/frontend/`:

```bash
npm test -- --run
npm run lint
npx tsc --noEmit
npm run build
```

Do not claim checks passed unless they were actually run. Tests should be deterministic and must not contact Telegram, Google, or Gemini; mock external services at their adapter boundaries.

## Pull requests

1. Create a focused branch and keep the diff limited to the requested change.
2. Add or update tests and relevant documentation.
3. Use a clear Conventional Commit message.
4. Complete the repository's pull-request template, including any remaining limitations or checks not run.
