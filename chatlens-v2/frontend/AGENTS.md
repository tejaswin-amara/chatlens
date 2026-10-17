# AGENTS.md

This file provides guidance and project context for AI coding agents operating in this repository, including **Antigravity**, **Claude Code**, and **Jules by Google** (jules.google.com).

## 🚀 Project Overview

**KL-Sync** (`kl-sync`) is an unofficial, high-performance, minimalist ERP web client and edge proxy for KL University students.

- **Framework**: Next.js 16 (App Router, Turbopack, React 19)
- **Language**: TypeScript 5.8
- **Architecture**: Edge Proxy (Stateless, no DB). Session tokens encrypted with AES-256-GCM.
- **Styling**: Tailwind CSS v4 + Vanilla CSS tokens (`globals.css`)
- **Icon Engine**: Native zero-runtime SVG library (`src/components/ui/icons.tsx` — 57 primitives)
- **Testing**: Native Node.js Test Runner (`node:test`) + Playwright E2E + Agent-as-Judge AI suite

---

## 🛠️ Build & Test Commands

Before making PRs or committing changes, run the following verification sequence:

```bash
# 1. Typecheck (0 Errors)
npx tsc --noEmit

# 2. Linting (0 Errors)
npm run lint

# 3. Unit & Integration Test Suite (363 tests across 61 suites)
npm test

# 4. Agent-as-Judge AI Verification (9 tests)
npx tsx scripts/agent-as-judge.ts

# 5. Playwright E2E Suite
npx playwright test

# 6. Production Turbopack Build
npm run build
```

---

## 📐 Architecture & Principles

1. **Ponytail Philosophy (YAGNI & Zero Bloat)**:
   - Prefer standard library primitives over third-party dependencies (`lucide-react`, `swr`, `clsx`, `tailwind-merge` have been permanently pruned).
   - Use `@/components/ui/icons` for all icon needs (never install external icon packs).
   - Deletion over addition. Shortest working diff wins.

2. **Security & Session Confidentiality**:
   - Never store plain text passwords in `localStorage`, `sessionStorage`, or commits.
   - All ERP sessions route through `encodeSession()` and `decodeSession()` using Web Crypto API (`AES-256-GCM`).
   - Production mode (`NODE_ENV=production`) strictly requires `SESSION_SECRET` and fails closed on missing secrets.
   - Proxy URLs (e.g. `src/app/api/fetch-photo/route.ts`) must strictly validate target origins against `https://newerp.kluniversity.in` to prevent SSRF vulnerabilities.

3. **Accessibility & Design**:
   - Adhere to **WCAG 2.2 AAA** accessibility standards (contrast ≥ 7.1:1, interactive touch targets ≥ 44px).
   - Use high-visibility focus indicators (`:focus-visible`).

---

## 📁 Directory Structure

```
├── .github/
│   └── workflows/
│       ├── ci.yml            # CI Quality Gates
│       ├── codeql.yml        # CodeQL Security Analysis
│       └── jules.yml         # Jules Automation Workflow
├── scripts/                  # Automated verification & stress testing harnesses
│   ├── agent-as-judge.ts     # AI Tool execution evaluation
│   ├── challenger-browser-stress.ts # Deep browser DOM & touch target audit
│   ├── challenger-icon-stress.ts    # Native SVG icon engine verification
│   └── e2e-browser-audit.ts         # Multi-route browser navigation audit
├── src/
│   ├── app/                  # Next.js App Router (pages, API routes, layout)
│   │   ├── api/              # Edge proxy endpoints (login, captcha, erp-proxy, fetch-photo, ai/chat)
│   │   └── dashboard/        # 11 Dashboard module routes (attendance, timetable, marks, etc.)
│   ├── components/           # React UI components & native SVG icon engine
│   │   ├── ui/icons.tsx      # Native 57-component SVG icon library
│   │   └── ui/LanguageSelector.tsx # i18n language & RTL toggle
│   ├── hooks/                # Custom React data hooks (useAcademicSession, useNativeQuery)
│   ├── lib/                  # Scrapers (attendance, marks, timetable, fee, profile), crypto, captcha
│   │   ├── i18n/             # 3-language zero-dependency translation engine (en, te, hi)
│   │   └── data-prefetcher.ts # Parallel login-time prefetch for all 9 ERP modules
│   └── types/                # TypeScript type definitions & Zod schemas
└── AGENTS.md                 # Agent guidance & project instructions

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
```
