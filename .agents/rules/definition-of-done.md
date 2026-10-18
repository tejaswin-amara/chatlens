# Definition of Done (Addy Osmani agent-skills Alignment)

> Standard: `addyosmani/agent-skills` Definition of Done & Awesome Dev Pipeline Standing Gate  
> Scope: Standing quality bar for every code modification across ChatLens Monorepo & Spark PA.

---

## 1. Correctness
- [ ] **Acceptance Criteria**: All acceptance criteria for the task are met.
- [ ] **Runtime Verification**: Code runs and behaves as intended, verified at runtime (never self-certify on code inspection alone).
- [ ] **Test Coverage**: New behavior is covered by tests that fail without the change and pass with it.
- [ ] **No Regressions**: All 333+ pytest tests and 363+ frontend tests pass 100% offline.
- [ ] **Edge Cases**: Network timeouts, expired sessions, missing configs, and rate limits are safely handled.

## 2. Code Quality & Minimalism (Ponytail Ultra)
- [ ] **Ladder of Abstraction**: YAGNI -> Codebase reuse -> Stdlib first -> Installed dependencies -> One readable line.
- [ ] **Shortest Working Diff**: Surgical edits over rewrites. Unrelated code or formatting is never touched.
- [ ] **Zero Dead Code**: No debug printouts, orphaned imports, or commented-out blocks left behind.
- [ ] **Type & Lint Cleanliness**: `mypy` 0 errors across 58 source files; `ruff check` 0 errors; `npx tsc --noEmit` and `npm run lint` 0 errors.

## 3. Integration & Persistence
- [ ] **System Invariants**: Telegram remains strictly read-only for public groups/channels. Output goes only to `OWNER_CHAT_ID` or `"me"`.
- [ ] **Immutable Calendar**: Telegram messages never mutate academic-calendar dates (`data/calendar_2026_27.toml`).
- [ ] **Database & Migrations**: SQLite WAL mode enforced; Alembic migrations strictly follow expand/contract patterns.

## 4. Security & Guardrails (AgentShield)
- [ ] **Zero Plaintext Secrets**: Secrets, tokens, session strings, and passwords never appear in git history, code, or logs.
- [ ] **PII Masking**: Aadhaar, RRN, and phone numbers are scrubbed before logging or LLM prompting.
- [ ] **AI / LLM Ingress Fencing**: External Telegram messages and chat transcripts are fenced in XML tags (`<untrusted_..._message>`).
- [ ] **Output Boundaries**: Model output is treated as untrusted; never passed into `eval`, raw SQL, shell execution, or arbitrary file writes.

## 5. Technical Debt & Documentation
- [ ] **PONYTAIL-DEBT.md**: All deliberate shortcuts carry explicit upgrade triggers. 0 rot-risk entries (`no-trigger`).
- [ ] **ADR Integrity**: Architectural decisions are recorded under `docs/architecture/adr/` in MADR 3.0 format.
