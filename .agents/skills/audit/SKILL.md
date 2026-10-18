---
name: audit
description: Execute an exhaustive Ponytail Ultra complexity, dead abstraction, and bloat audit across the repository.
---

# Whole-Repo Audit Skill (`audit`)

Use this skill when auditing the codebase for unnecessary complexity, speculative code, dead abstractions, or architectural bloat according to Ponytail Ultra standards.

## Workflow

### 1. Repository Mapping
- Read `README.md`, entry points (`src/main.py`, `chatlens-v2/backend/main.py`, `chatlens-v2/frontend/src/app`), configurations (`src/config.py`, `compose.yaml`), and dependencies (`pyproject.toml`, `package.json`).
- Identify components, data flow, trust boundaries, and expected runtime load.

### 2. Systematic Codebase Scan
Inspect the codebase against five core vectors:
1. **Bugs & Edge Cases**: Timezone mismatches (unlocalized `datetime.now()`), swallowed exceptions, unhandled boundary conditions.
2. **Security & Data Loss**: Secret leakage, prompt injection vulnerabilities, non-transactional database writes.
3. **Scale & Concurrency Risks**: Unbounded memory collections, missing locks, blocking I/O in async loops.
4. **Missing Tests**: Risky business logic or untested branches.
5. **Lean Cuts**: Dead code, duplicate helpers, speculative abstractions, unused dependencies.

### 3. Reporting Format
Structure the audit report with:
- **Repository Summary**: 2-3 sentences describing the repository purpose and operational context.
- **Findings Hierarchy**:
  - **Must Fix**: Critical defects, security vulnerabilities, data loss risks.
  - **Should Fix**: Architectural debt, missing test coverage, scale risks.
  - **Nice to Have**: Cosmetic cleanup, documentation polish.
- **Each Finding Details**:
  - What this is
  - Problem & Risk
  - Minimal Fix
  - Impact if skipped
- **Conclusion**:
  - Final Verdict (`PASS`, `CONDITIONAL PASS`, or `FAIL`)
  - Estimated lean line reductions (`Lean: -<N> lines possible`)
  - Explicit boundaries of uninspected areas (`Not checked:`)
