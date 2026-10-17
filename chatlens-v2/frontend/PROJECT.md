# Project: KL-Sync System-Wide Verification & Quality Audit

## Architecture
- Framework: Next.js 16 (App Router, Turbopack, React 19)
- Language: TypeScript 5.8
- Architecture: Edge Proxy (Stateless, no DB). Session tokens encrypted with AES-256-GCM.
- Styling: Tailwind CSS v4 + Vanilla CSS tokens (`globals.css`)
- Icons: Native inline SVG components (`src/components/ui/icons.tsx` — 57 primitives), zero external icon dependencies.
- Testing: Native Node.js Test Runner (`node:test`) + Playwright E2E + Agent-as-Judge AI suite + Challenger stress harnesses.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Automated Test Suite (363 tests) | Execute and verify all 363 unit/integration tests across 61 test suites with 0 failures | M1 | ORIGINAL_REQUEST R2 |
| 2 | TypeScript Compilation (0 errors) | Full AST typecheck across all src, test, and script files with `npx tsc --noEmit` | M1 | ORIGINAL_REQUEST R2 / Criteria |
| 3 | ESLint Conformance (0 errors/warnings) | Zero ESLint warnings or errors across the repository with `npm run lint` | M1 | ORIGINAL_REQUEST R2 / Criteria |
| 4 | Agent-as-Judge AI Evaluation | 9/9 AI tool execution and parameter validation tests passing via `scripts/agent-as-judge.ts` | M1 | ORIGINAL_REQUEST R2 / Criteria |
| 5 | Production Turbopack Build | Clean Next.js 16 Turbopack production compilation via `npm run build` | M1 | ORIGINAL_REQUEST R2 / Criteria |
| 6 | 11 Dashboard Routes E2E Verification | Clean navigation, zero console errors, zero React exceptions across all 11 modules in Demo Mode | M2 | ORIGINAL_REQUEST R1 |
| 7 | UI & Accessibility Compliance | WCAG 2.2 AAA contrast (≥7.1:1), 44px min touch targets, rounded corner containment, photo fallbacks | M2 | ORIGINAL_REQUEST R1 |
| 8 | Playwright E2E Test Suite | 13/13 E2E tests passing in Playwright test runner (`npx playwright test`) | M2 | ORIGINAL_REQUEST R2 |
| 9 | Forensic Integrity & Multi-Perspective Audit | Independent verification by Reviewers, Challengers, and Forensic Auditor | M3 | Audit & Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Automated Verification Suites Baseline | TypeScript (0 errors), Lint (0 errors), Unit Tests (363/363), Agent-as-Judge (9/9), Build | none | DONE |
| 2 | End-to-End Browser & UI Module Audit | 11 Dashboard Routes in Demo Mode, zero console errors, zero hydration errors, Playwright E2E | M1 | DONE |
| 3 | Multi-Perspective Review & Forensic Audit | Dual Reviewers, Dual Challengers, and Forensic Auditor verification | M1, M2 | DONE |

## Interface Contracts
### Dashboard Routes Contract (`src/app/dashboard/*`)
- All 11 routes (`attendance`, `timetable`, `marks`, `profile`, `fee`, `exam-seating`, `circulars`, `hostels`, `library`, `tools`, `copilot`) load cleanly with HTTP 200–399 in demo mode.
- 0 unhandled console errors or React hydration warnings emitted.
- All interactive controls respect `min-h-[44px] min-w-[44px]` for WCAG 2.2 AAA.

### Quality Baseline Contract
- `npx tsc --noEmit` exits with 0 errors.
- `npm run lint` exits with 0 errors.
- `npm test` executes 363 tests across 61 suites with 100% pass rate.
- `npx tsx scripts/agent-as-judge.ts` executes 9 AI evaluations with 100% pass rate.
- `npm run build` generates 17 static pages and 8 dynamic endpoints cleanly.
- `npx playwright test` passes 13/13 E2E test specs.

## Code Layout
- `src/app/` — Next.js App Router pages and API routes
- `src/components/ui/icons.tsx` — Native zero-dependency SVG icon system (57 primitives)
- `src/components/` — UI components and widgets
- `src/lib/scrapers/` — ERP web scrapers and data parsers
- `src/lib/fixtures/` — Demo mode mock data fixtures
- `src/lib/session.ts` — AES-256-GCM session encryption
- `tests/` & `src/**/*.test.ts` — Native Node.js test runner unit & integration suites
- `scripts/` — Challenger stress harnesses, agent-as-judge evaluation, browser audit
- `e2e/` — Playwright end-to-end test specifications
