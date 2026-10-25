# ADR 0007: ChatLens Frontend Restoration and Student Portal Isolation

* Status: accepted
* Deciders: Principal Software Engineer, Repository Maintainer
* Date: 2026-10-23

## Context and Problem Statement
In commit `4b3170e`, an external student ERP portal project (`kl-sync`) was directly committed into `chatlens-v2/frontend/`. This replaced all ChatLens components (chat ingestion modal, message list, pagination, chat stats dashboard, in-chat search, AI analyzer, Q&A ask bar, and SPARK status modal) with a login screen and dashboard for `newerp.kluniversity.in`.

Furthermore, `output: 'export'` was removed from `next.config.ts`, breaking the Nginx container build in `Dockerfile` and causing a routing deadlock with Caddy reverse proxy rules that forward all `/api/*` traffic to FastAPI (`chatlens-backend:8000`).

We need an architectural decision on how to restore the ChatLens platform to working order while handling the student ERP portal work.

## Decision Drivers
* Restore the ChatLens analytics platform in accordance with ADR 0005 and the root README.
* Preserve all verified student ERP portal work without data or feature loss.
* Maintain clean separation of concerns, container contracts, and reverse proxy routing.
* Adhere to Ponytail minimalism, YAGNI, and the Universal Engineering Pipeline Standard v2.2.0.

## Considered Options
* **Option 1 (Primary / Recommended): Clean Restoration of ChatLens SPA & Extraction of Portal.**
  Restore `chatlens-v2/frontend/` to the verified ChatLens SPA from commit `37102e6` with `output: 'export'`. Extract the `kl-sync` student portal into a dedicated standalone repository (`tejaswin-amara/kl-sync`) or dedicated directory (`portal/`).
* **Option 2 (Multi-Zone Hybrid Monorepo): Dual-Subpath Routing.**
  Retain both applications within Next.js: root `/` routes to ChatLens analytics, and `/portal/*` routes to the KL Sync ERP portal.
* **Option 3 (Next.js Dynamic Server Replacement):**
  Abandon static Nginx export and run a Node.js server (`next start`), reconfiguring Caddy to split `/api/chatlens/*` to FastAPI and `/api/erp/*` to Next.js.

## Decision Outcome
Accepted Option: **Option 1 (Clean Restoration of ChatLens SPA & Extraction of Portal)**.

### Rationale & Comparison
* **Option 1:**
  - *Pros:* Fully restores ChatLens platform with zero architectural regressions; retains lightweight Nginx container (~25MB); adheres strictly to ADR 0005; completely resolves Docker build failure and Caddy reverse proxy deadlock.
  - *Reversal Cost:* Low. `kl-sync` history is preserved in git commits `4b3170e` through `a1952e4` and can be branched or submoduled at any time.
* **Option 2:**
  - *Choose when:* The maintainer strictly requires student attendance/marks and chat analytics to be served from the exact same domain and Docker container.
  - *Excluded because:* Introduces massive complexity: static export cannot support Next.js Edge API routes (`/api/login`, `/api/captcha`), forcing a Node.js runtime and dual backend dependencies.
* **Option 3:**
  - *Choose when:* Server-side dynamic React rendering is strictly required for chat analytics.
  - *Excluded because:* Violates ADR 0005; increases container image footprint 5x; breaks the clean Caddy `/api/*` contract.

## Positive Consequences
* ChatLens web application is restored end-to-end (ingest, view, search, analyze, export, SPARK bridge).
* Static export generates cleanly into `/app/out`, unblocking Docker builds.
* Reverse proxy Caddyfile routing remains simple and robust.

## Negative Consequences
* Student portal features are separated from ChatLens analytics until deployed as an independent service.
