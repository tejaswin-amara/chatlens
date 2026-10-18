---
name: verify
description: Execute the complete Awesome Dev Pipeline v2.0.0 offline verification suite across Python and TypeScript stacks.
---

# Complete Pipeline Verification Skill (`verify`)

Use this skill to run the full quality gate matrix for ChatLens and the SPARK PA daemon before committing or releasing changes.

## Verification Matrix

### 1. Python Linting & Formatting
Run fast static checks:
```bash
uv run ruff check src tests scripts chatlens chatlens-v2/backend
uv run ruff format --check src tests scripts chatlens chatlens-v2/backend
```

### 2. Python Type Checking
Ensure strict type compliance with zero untyped definitions:
```bash
uv run mypy src
```

### 3. Python Test Execution
Run test suites treating runtime warnings as immediate failures:
```bash
uv run pytest -q -W error::RuntimeWarning
```

### 4. Prompt Drift Verification
Ensure Gemini prompt templates in code match baseline evals:
```bash
uv run pytest -q tests/test_prompt_drift.py
```

### 5. Frontend Static Checks & Production Build
Validate TypeScript, linting, and Next.js static export:
```bash
cd chatlens-v2/frontend && npm run lint && npx tsc --noEmit && npm run build
```

### 6. Negative Invariant Checks
Verify adherence to non-negotiable codebase invariants:
- **Timezone Invariant**: No raw unlocalized `datetime.now()` in `src/`:
  ```bash
  git grep "datetime.now" src/
  ```
- **Gemini Invariant**: No deprecated sampling parameters (`temperature`, `top_p`, `top_k`):
  ```bash
  git grep -E "temperature|top_p|top_k" src/parsing/ai_extractor.py
  ```
