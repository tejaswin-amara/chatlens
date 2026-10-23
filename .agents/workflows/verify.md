# Verify Workflow (`/verify`)

Execute the complete Awesome Dev Pipeline v2.2.0 local verification suite across Python and TypeScript stacks:

1. **Python Linter**:
   ```bash
   uv run ruff check src tests scripts chatlens-v2/backend
   ```
2. **Python Code Formatter**:
   ```bash
   uv run ruff format --check src tests scripts chatlens-v2/backend
   ```
3. **Python Static Type Checking**:
   ```bash
   uv run mypy src scripts benchmarks chatlens-v2/backend
   ```
4. **Python Test Suite (Runtime Warnings Treated as Errors)**:
   ```bash
   uv run pytest -q -W error::RuntimeWarning
   ```
5. **Prompt Drift Verification**:
   ```bash
   uv run pytest -q tests/test_prompt_drift.py
   ```
6. **Frontend Static Checks & Production Build**:
   ```bash
   cd chatlens-v2/frontend && npm run lint && npx tsc --noEmit && npm run build
   ```
7. **Negative Invariant Audits**:
   - Verify zero un-bracketed `datetime.now()` occurrences in `src/` outside `src.utils.clock`:
     `git grep "datetime.now" src/`
   - Verify zero `temperature`, `top_p`, or `top_k` references in `src/parsing/ai_extractor.py`:
     `git grep -E "temperature|top_p|top_k" src/parsing/ai_extractor.py`
