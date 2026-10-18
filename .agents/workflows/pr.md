# Pull Request Workflow (`/pr`)

Generate the standardized Awesome Dev Pipeline v2.0.0 Pull Request description and evidence report.

## Required Format
The output MUST include the following mandatory sections:

### 1. Changed
Bulleted list of all concrete functional and structural changes across components (`src/`, `tests/`, `chatlens-v2/`, `.github/`, config).

### 2. Decisions
Explicit rationale for architectural and design decisions made, including tradeoffs, fallback choices, and negative invariant enforcements.

### 3. Not done
Explicit boundary definitions of what was intentionally omitted or kept out of scope.

### 4. Verification Evidence
A markdown table summarizing test passes, lint statuses, type-check results, and security scans:
- `pytest` suite execution results
- `ruff check` and `ruff format` results
- `mypy` static type checking results
- Frontend `npm run build` & type checking status
- Security/Secret scan results
