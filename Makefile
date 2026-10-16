.PHONY: check lint format typecheck test security frontend-check

check: lint typecheck test security frontend-check

lint:
	uv run ruff check src tests scripts chatlens-v2/backend
	uv run ruff format --check src tests scripts chatlens-v2/backend
	uv run python scripts/lint_migration.py
	uv run python scripts/scan_motion.py

format:
	uv run ruff format src tests scripts chatlens-v2/backend

typecheck:
	uv run mypy src scripts benchmarks chatlens-v2/backend

test:
	uv run pytest -q -W error::RuntimeWarning

security:
	uv run python scripts/detect_archetype.py . --format text

frontend-check:
	cd chatlens-v2/frontend && npm run lint && npx tsc --noEmit && npm run build
