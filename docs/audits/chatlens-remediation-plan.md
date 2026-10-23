# ChatLens Remediation Plan: Implementation Roadmap

**Date:** 2026-10-23  
**Status:** PROPOSED (Awaiting Maintainer Approval)  
**Governing Standard:** Universal Engineering Pipeline Standard & Brief v2.2.0  
**Target Subsystems:** `chatlens-v2/frontend`, `chatlens-v2/backend`, `compose.yaml`, `Dockerfile`  

---

## 1. Prioritization & Sequencing Strategy

Remediation is structured into six strictly sequenced, reversible phases following the dependency chain:

```mermaid
flowchart TD
    P1["Phase 1: Security Hardening (P0)<br/>Wire Auth & Pin Dependencies"]
    P2["Phase 2: Frontend Restoration (P1)<br/>Restore ChatLens UI & Static Export"]
    P3["Phase 3: Container & Ingress (P1)<br/>Fix Healthcheck & Docker Build"]
    P4["Phase 4: Database Alignment (P2)<br/>Harmonize Config & Clean Migrations"]
    P5["Phase 5: Reliability & Retrieval (P2)<br/>Embeddings & Celery Retry Safety"]
    P6["Phase 6: Full Quality Gate (P3)<br/>E2E Verification & Audit Approval"]

    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6
```

* **P0 — Security Emergency:** Unauthenticated backend endpoints, missing `firebase-admin`, hardcoded mock token bypass.
* **P1 — Restore Core Functionality:** Restore the genuine ChatLens user interface, re-enable Next.js static export (`output: 'export'`), align Caddy reverse proxy routing, and fix Dockerfile healthcheck.
* **P2 — Reliability & Integrity:** Harmonize PostgreSQL credentials between compose files and `database.py`, streamline triple migrations to Alembic authority, preserve Celery upload files for retries, and pass embedding `task_type`.
* **P3 — Hardening & Operational Polish:** Dynamic CORS origin allowlist, DoS protection against SQL ILIKE wildcard injection, and comprehensive browser E2E test passes.

---

## 2. Phase-by-Phase Implementation Specifications

### Phase 1: Security Hardening & Authentication Enforcement (P0)

**Objectives:**
1. Eliminate universal unauthenticated access to the backend API (DEF-04).
2. Wire `get_current_user` into all non-probe FastAPI endpoints.
3. Install `firebase-admin` in `requirements.txt` and ensure mock token bypass is strictly gated to `ENVIRONMENT=test`.

**Exact Files to Modify:**
- `chatlens-v2/backend/requirements.txt`
- `chatlens-v2/backend/firebase_auth.py`
- `chatlens-v2/backend/main.py`
- `tests/test_backend_api.py`

**Implementation Actions:**
1. Add `firebase-admin>=6.5.0` and `aiosqlite>=0.20.0` to `chatlens-v2/backend/requirements.txt`.
2. In `chatlens-v2/backend/firebase_auth.py`:
   - Enforce that `mock-test-token` is only accepted when `os.getenv("ENVIRONMENT") == "test"` or `os.getenv("TESTING") == "1"`. In production, reject it with HTTP 401.
3. In `chatlens-v2/backend/main.py`:
   - Import `get_current_user` from `firebase_auth`.
   - Protect all business endpoints using `Depends(get_current_user)`:
     - `/api/chats` (GET, DELETE)
     - `/api/messages` (GET, search)
     - `/api/chats/{chat_id}/export` (GET)
     - `/api/upload/*` and `/api/chats/import` (POST)
     - `/api/analyze`, `/api/ask`, `/api/chats/{chat_name}/insights`, `/api/global_summarize` (POST/GET)
     - `/api/telegram/auth/*` (GET/POST)
   - Keep public probe endpoints open: `/api/healthz`, `/api/status`, `/api/spark/status` (read-only system bridge).
4. Update `tests/test_backend_api.py` to include authorization headers (`Bearer mock-test-token`) across all fixture requests.

**Validation Command:**
```bash
uv run pytest tests/test_backend_api.py -k test_firebase_auth -v
uv run pytest tests/test_backend_api.py -v
```
*Expected Result:* 21/21 tests pass; unauthenticated requests receive HTTP 401 Unauthorized.

**Rollback Procedure:**
`git checkout HEAD -- chatlens-v2/backend/main.py chatlens-v2/backend/firebase_auth.py chatlens-v2/backend/requirements.txt`

---

### Phase 2: Frontend Restoration & Static Export Configuration (P1)

**Objectives:**
1. Resolve DEF-01 (UI substitution) by restoring the verified ChatLens web application.
2. Resolve DEF-02 (Docker build failure) by restoring `output: 'export'` in `next.config.ts`.
3. Provide a clear architectural disposition for the KL Sync student portal.

**Architecture Decision on Frontend Disposition:**
* **Primary Path (Recommended):** Restore the ChatLens single-page application from git history (`37102e6`) as the root application (`/`). If the maintainer wishes to retain the KL Sync student portal, move it to a dedicated subpath (e.g., `chatlens-v2/frontend/src/app/portal/` or a separate repository `kl-sync/`) rather than overwriting the ChatLens core product.
* **Alternative Path:** Multi-zone application where `/` serves ChatLens analytics and `/portal` serves the ERP client.

**Exact Files to Restore / Modify:**
- `chatlens-v2/frontend/package.json` (Restore name `chatlens-frontend`, scripts, and dependencies: `@lucide/react`, `recharts`, `tailwindcss`)
- `chatlens-v2/frontend/next.config.ts` (Restore `output: 'export'`, `trailingSlash: true`, `images: { unoptimized: true }`)
- `chatlens-v2/frontend/src/app/page.tsx` (Restore ChatLens home dashboard, sidebar, message list, chat header, ask bar)
- `chatlens-v2/frontend/src/components/` (Restore `AiCard.tsx`, `AskBar.tsx`, `ChatHeader.tsx`, `Dashboard.tsx`, `FormatAi.tsx`, `ImportModal.tsx`, `MessageList.tsx`, `Sidebar.tsx`, `SparkStatusModal.tsx`, `Toast.tsx`, `WelcomePage.tsx`)
- `chatlens-v2/frontend/src/hooks/useApi.ts` (Restore relative-origin API caller interfacing with FastAPI `/api/*`)
- `chatlens-v2/frontend/src/types.ts` (Restore `Chat`, `Message`, `ChatStats`, `GlobalStats`, `AiCardData` interfaces)

**Implementation Actions:**
1. Extract the verified ChatLens frontend source tree from commit `37102e6:chatlens-v2/frontend/src/`.
2. In `next.config.ts`, ensure:
   ```typescript
   import type { NextConfig } from 'next';

   const nextConfig: NextConfig = {
     output: 'export',
     images: { unoptimized: true },
     trailingSlash: true,
   };

   export default nextConfig;
   ```
3. Run `npm install` inside `chatlens-v2/frontend` to ensure exact lockfile reconciliation.
4. Run `npm run build` to verify that Next.js produces a clean, complete `/app/out` static artifact containing `index.html` and `_next/static/`.

**Validation Commands:**
```bash
cd chatlens-v2/frontend
npm run typecheck
npm run lint
npm run build
test -f out/index.html && echo "Static export confirmed"
cd ../..
```
*Expected Result:* `npm run build` writes static assets into `out/`, with zero server-side rendering errors.

**Rollback Procedure:**
`git checkout HEAD -- chatlens-v2/frontend`

---

### Phase 3: Container Orchestration & Healthcheck Repair (P1)

**Objectives:**
1. Resolve DEF-05: Fix backend Dockerfile healthcheck target URL.
2. Resolve DEF-02: Validate end-to-end container build of `chatlens-frontend` and `chatlens-backend`.
3. Resolve DEF-03: Validate Caddy reverse proxy routing contract.

**Exact Files to Modify:**
- `chatlens-v2/backend/Dockerfile`
- `chatlens-v2/frontend/Dockerfile`
- `compose.yaml`
- `Caddyfile`

**Implementation Actions:**
1. In `chatlens-v2/backend/Dockerfile` line 23:
   Change healthcheck URL from `/api/health` to `/api/healthz`:
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
       CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/healthz')" || exit 1
   ```
2. In `chatlens-v2/frontend/Dockerfile`:
   Verify that `COPY --from=builder /app/out /usr/share/nginx/html` succeeds now that `output: 'export'` is active.
   Ensure SPA fallback configuration in `nginx.conf`:
   ```nginx
   location / {
       try_files $uri $uri/ /index.html;
   }
   ```
3. In `compose.yaml`:
   Ensure `chatlens-frontend` depends on `chatlens-backend` condition `service_healthy`.
4. Validate offline config via `python scripts/verify_deployment.py --check-config`.

**Validation Commands:**
```bash
docker build -t chatlens-backend:test chatlens-v2/backend
docker build -t chatlens-frontend:test chatlens-v2/frontend
uv run python scripts/verify_deployment.py --check-config
```
*Expected Result:* Both Docker images build with exit code 0; `verify_deployment.py` reports 12/12 groups passing.

**Rollback Procedure:**
`git checkout HEAD -- chatlens-v2/backend/Dockerfile chatlens-v2/frontend/Dockerfile compose.yaml Caddyfile`

---

### Phase 4: Database Harmonization & Migration Lifecycle Cleanup (P2)

**Objectives:**
1. Resolve DEF-06: Harmonize PostgreSQL database names, users, and passwords across all compose files, configs, and default connection strings.
2. Resolve DEF-07: Remove redundant raw SQL execution and bare exception swallowing from `main.py` lifespan, establishing Alembic as the single source of truth for schema migrations.

**Exact Files to Modify:**
- `chatlens-v2/docker-compose.yml`
- `chatlens-v2/backend/database.py`
- `chatlens-v2/backend/alembic.ini`
- `chatlens-v2/backend/main.py`

**Implementation Actions:**
1. Standardize canonical default credentials across the repository:
   - Database name: `chatlens`
   - User: `postgres`
   - Default URL: `postgresql+asyncpg://postgres:postgres@localhost:5432/chatlens`
   - Update `chatlens-v2/docker-compose.yml` and `chatlens-v2/backend/database.py` to use these defaults.
2. In `chatlens-v2/backend/main.py`:
   - Refactor `lifespan`:
     ```python
     @asynccontextmanager
     async def lifespan(app: FastAPI):
         # Startup: verify connectivity
         try:
             async with engine.begin() as conn:
                 await conn.execute(text("SELECT 1"))
         except Exception as exc:
             logger.warning(f"Database readiness probe warning: {exc}")
         yield
         # Shutdown: clean engine disposal
         try:
             await engine.dispose()
         except Exception as exc:
             logger.warning(f"Engine dispose warning: {exc}")
     ```
   - Delete the raw `.sql` file loop. Schema migrations are executed exclusively by the `chatlens-migration` init container via `alembic upgrade head`.

**Validation Commands:**
```bash
uv run pytest tests/e2e/test_tier5_adversarial.py -k test_alembic -v
uv run pytest tests/test_backend_api.py -v
```
*Expected Result:* Alembic migrations test cleanly; backend starts with zero startup overhead or swallowed exceptions.

**Rollback Procedure:**
`git checkout HEAD -- chatlens-v2/docker-compose.yml chatlens-v2/backend/database.py chatlens-v2/backend/main.py`

---

### Phase 5: Reliability & Retrieval Enhancements (P2)

**Objectives:**
1. Resolve DEF-08: Forward `task_type` in `embeddings.py` to ensure high-quality asymmetric vector retrieval for `/api/ask`.
2. Resolve DEF-09: Refactor `celery_worker.py` to preserve uploaded files on retryable failures.
3. Resolve DEF-10: Escape `%` and `_` wildcards in SQL ILIKE queries to prevent DoS.

**Exact Files to Modify:**
- `chatlens-v2/backend/embeddings.py`
- `chatlens-v2/backend/celery_worker.py`
- `chatlens-v2/backend/main.py`

**Implementation Actions:**
1. In `chatlens-v2/backend/embeddings.py`:
   Update `generate_embedding` to pass `task_type`:
   ```python
   result = client.models.embed_content(
       model=model,
       contents=text,
       config={"task_type": task_type} if task_type else None,
   )
   ```
2. In `chatlens-v2/backend/celery_worker.py`:
   Only remove `file_path` on successful completion (`status: "done"`) or fatal non-retryable errors. In case of unexpected exceptions that Celery will retry, do not delete the file.
3. In `chatlens-v2/backend/main.py`:
   Sanitize search queries:
   ```python
   def _escape_like(val: str) -> str:
       return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
   ```
   Apply `_escape_like` in `search_messages`:
   ```python
   if sender:
       stmt = stmt.where(Message.sender.ilike(f"%{_escape_like(sender)}%"))
   if effective_query:
       stmt = stmt.where(Message.text.ilike(f"%{_escape_like(effective_query)}%"))
   ```

**Validation Commands:**
```bash
uv run pytest tests/test_v2_backend.py -v
uv run pytest tests/test_backend_api.py -k test_security_sql_injection -v
```
*Expected Result:* Wildcard searches and embeddings tests execute cleanly without degradation.

**Rollback Procedure:**
`git checkout HEAD -- chatlens-v2/backend/embeddings.py chatlens-v2/backend/celery_worker.py chatlens-v2/backend/main.py`

---

### Phase 6: Operational Polish & Verification Gate (P3)

**Objectives:**
1. Resolve DEF-11: Enable configurable CORS origins via `CORS_ORIGINS` environment variable.
2. Execute the complete repository verification suite across Python and Frontend.

**Exact Files to Modify:**
- `chatlens-v2/backend/main.py`
- `.env.example`
- `.env.production.example`

**Implementation Actions:**
1. In `chatlens-v2/backend/main.py`:
   ```python
   origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
   allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

   app.add_middleware(
       CORSMiddleware,
       allow_origins=allowed_origins,
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
2. Update `.env.example` and `.env.production.example` to document `CORS_ORIGINS`.

---

## 3. End-to-End Verification Matrix

| Gate | Command | Environment | Expected Pass Condition |
|---|---|---|---|
| **Python Lint** | `uv run ruff check src tests scripts chatlens-v2/backend` | Local / CI | Clean exit 0, zero lint violations |
| **Python Formatting** | `uv run ruff format --check src tests scripts chatlens-v2/backend` | Local / CI | Clean exit 0, all files formatted |
| **Type Checking** | `uv run mypy src scripts benchmarks chatlens-v2/backend` | Local / CI | Clean exit 0, zero type errors |
| **Backend Unit Tests** | `uv run pytest -q -W error::RuntimeWarning` | Local / CI | Clean exit 0, 350+ tests passed |
| **Prompt Drift** | `uv run pytest -q tests/test_prompt_drift.py` | Local / CI | Clean exit 0, prompt in sync with evals |
| **Frontend Lint** | `cd chatlens-v2/frontend && npm run lint` | Local / CI | Clean exit 0, zero ESLint errors |
| **Frontend Typecheck** | `cd chatlens-v2/frontend && npm run typecheck` | Local / CI | Clean exit 0, zero TypeScript errors |
| **Frontend Build** | `cd chatlens-v2/frontend && npm run build` | Local / CI | Clean exit 0, static output written to `out/` |
| **Deployment Config** | `uv run python scripts/verify_deployment.py --check-config` | Local / CI | Clean exit 0, 12/12 check groups PASS |
| **Container Build** | `docker compose build` | Local with Docker | Clean exit 0 for all 6 container images |

---

## 4. Risks, Dependencies & Rollback Strategy

| Phase | Primary Risk | Mitigation | Rollback Command |
|---|---|---|---|
| **Phase 1 (Auth)** | Frontend unable to authenticate if token missing | Provide mock token support for local development (`mock-test-token`); document login flow | `git checkout HEAD -- chatlens-v2/backend/` |
| **Phase 2 (Frontend)** | Loss of KL Sync portal features | KL Sync portal files are safely tracked in git history (commit `4b3170e`) and can be exported to a dedicated repository or sub-route | `git checkout HEAD -- chatlens-v2/frontend/` |
| **Phase 3 (Docker)** | Nginx SPA routing 404 on deep links | Verify `try_files $uri $uri/ /index.html` in `nginx.conf` | `git checkout HEAD -- chatlens-v2/frontend/Dockerfile` |
| **Phase 4 (Database)** | Existing local databases with old user `chatlens` | Add fallback credential detection or migration note in documentation | `git checkout HEAD -- chatlens-v2/backend/database.py` |
| **Phase 5 (Embeddings)**| Gemini API quota limits | Batch embeddings are strictly capped at first 200 messages per import | `git checkout HEAD -- chatlens-v2/backend/embeddings.py` |
