# Project: ChatLens v2 & SPARK PA Daemon Production Deployment

## Architecture
- **Reverse Proxy**: Caddy (`caddy:2-alpine`) terminating TLS, routing `/` to `chatlens-frontend:80`, `/api/*` and `/ws*` to `chatlens-backend:8000`.
- **Frontend**: Next.js SPA static export served via lightweight Nginx container, `basePath` clean at root `/`, relative origin API requests.
- **Backend**: FastAPI service (`chatlens-backend:8000`), `/api/healthz`, status bridge to SPARK SQLite.
- **Worker**: Celery worker (`chatlens-celery`) connected to Redis broker & result backend (`redis:6379/0`), shared upload volume with backend.
- **Database**: PostgreSQL with `pgvector` (`pgvector/pgvector:pg16`), extension initialized via `/docker-entrypoint-initdb.d/01-init-pgvector.sql`.
- **Migration Service**: One-shot init container `chatlens-migration` executing `alembic upgrade head` before backend and celery start.
- **Daemon**: SPARK PA Telethon assistant (`chatlens-daemon`), state persisted at named volume `/app/data/spark.db` in SQLite WAL mode.
- **Cache/Broker**: Redis 7 (`redis:7-alpine`) with AOF persistence.
- **Networks & Volumes**: Single bridge network `chatlens-net`, named volumes for `spark_data`, `postgres_data`, `redis_data`, `caddy_data`, `caddy_config`, `uploads_data`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1 | Reverse Proxy (Caddy) TLS termination, routing `/` to frontend and `/api/*`, `/ws*` to backend | M1 | ORIGINAL_REQUEST R1 |
| 2 | F2 | Frontend Next.js `basePath` fix, relative API URL fallback, custom SPA `nginx.conf` | M1 | ORIGINAL_REQUEST R1 |
| 3 | F3 | Backend Dockerfile build fix: create complete production `requirements.txt` | M2 | Survey Explorer 2 |
| 4 | F4 | PostgreSQL pgvector extension auto-initialization via `/docker-entrypoint-initdb.d` | M2 | ORIGINAL_REQUEST R2 |
| 5 | F5 | Alembic setup & automated migration init container (`chatlens-migration`) | M2 | ORIGINAL_REQUEST R2 |
| 6 | F6 | Celery broker/backend URL resolution, upload volume sharing, Redis AOF | M2 | Survey Explorer 2 & 3 |
| 7 | F7 | Validated `.env.production.example` template with strict secret masking | M3 | ORIGINAL_REQUEST R3 |
| 8 | F8 | Safe volume mounts & persistence for SPARK SQLite (`/app/data/spark.db`), Postgres, Redis | M3 | ORIGINAL_REQUEST R3 |
| 9 | F9 | Container healthcheck probes (all services), restart policies, log rotation | M3 | ORIGINAL_REQUEST R4 |
| 10 | F10 | Deployment verification script (`scripts/verify_deployment.py`) with offline/check-config mode | M3 | ORIGINAL_REQUEST R4 |
| 11 | F11 | Final Integration & E2E Test Suite Pass (Tiers 1-4) | M4 | ORIGINAL_REQUEST Acceptance Criteria |
| 12 | F12 | Adversarial Coverage Hardening (Tier 5) | M4 | Project Pattern Phase 2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Reverse Proxy & Frontend Routing | Caddyfile, Next.js basePath, relative API URL, frontend nginx.conf, compose proxy service | none | DONE (Caddyfile, next.config.ts, nginx.conf, Vitest 19/19 pass) |
| M2 | Database Bootstrapping, Migrations & Celery | backend requirements.txt, pgvector init script, Alembic setup, chatlens-migration init container, Celery Redis fix | none | DONE (requirements.txt, 01-init-pgvector.sql, Alembic migrations, 25/25 API tests pass) |
| M3 | Secrets, Persistence & Reliability | .env.production.example, compose.yaml finalization (healthchecks, log rotation, volumes), scripts/verify_deployment.py | M1, M2 | DONE (.env.production.example, compose.yaml, verify_deployment.py, 62/62 E2E pass) |
| M4 | Final Integration, Acceptance & Hardening | Run verify_deployment.py, pass 100% E2E test suite (Tiers 1-4), adversarial test hardening (Tier 5) | M3 | DONE (112/112 E2E Tiers 1-5 pass, 316 repo tests pass, Auditor CLEAN, Reviewers APPROVE) |

## Interface Contracts
### chatlens-proxy ↔ chatlens-frontend
- Ingress: port 80/443 (HTTP/HTTPS) -> `chatlens-frontend:80`
- Routing: Default match `/*` forwards to frontend.
- Static assets: Emitted at `/_next/static/*` at root path (no `/chatlens` prefix).
- Fallback: Any unknown path returns `/index.html` (HTTP 200).

### chatlens-proxy ↔ chatlens-backend
- Routing: Path `/api/*` and `/ws*` forwarded to `chatlens-backend:8000`.
- Headers: Transparent WebSocket upgrade (`Upgrade`, `Connection`).
- Health probe: `GET /api/healthz` returns `{"status": "ok", "version": "2.0.0"}` with HTTP 200.

### postgres ↔ chatlens-migration ↔ chatlens-backend / chatlens-celery
- Database: `postgres:5432/chatlens`.
- pgvector: Extension `vector` initialized by PostgreSQL daemon prior to accepting client connections.
- Migration sequencing: `chatlens-migration` runs `alembic upgrade head` and exits 0 before `chatlens-backend` and `chatlens-celery` start (`condition: service_completed_successfully`).

### chatlens-backend ↔ chatlens-celery ↔ redis
- Broker & Result: `redis://redis:6379/0` passed via both `CELERY_BROKER_URL` and `REDIS_URL`.
- File sharing: Shared Docker volume `uploads_data` mounted at `/app/uploads` in both backend and celery.

### chatlens-daemon ↔ chatlens-backend
- Persistence: `spark_data` volume mounted at `/app/data`.
- DB path: `SPARK_DB=/app/data/spark.db` in SQLite WAL mode.
- Access: `chatlens-backend` mounts `spark_data:/app/data:ro` for read-only status checks at `/api/spark/status`.

## Code Layout
- `Caddyfile`: Root level Caddy configuration.
- `chatlens-v2/frontend/next.config.ts`: Next.js configuration.
- `chatlens-v2/frontend/nginx.conf`: Custom Nginx configuration for frontend SPA.
- `chatlens-v2/frontend/Dockerfile`: Frontend container build.
- `chatlens-v2/frontend/src/hooks/useApi.ts`, `src/app/page.tsx`: Relative origin API calls.
- `chatlens-v2/backend/requirements.txt`: Python package dependencies for backend container.
- `chatlens-v2/backend/alembic.ini`, `migrations/`: Alembic configuration and migration scripts.
- `docker/postgres/01-init-pgvector.sql`: PostgreSQL init script for pgvector.
- `compose.yaml`: Master Docker Compose orchestration definition.
- `.env.production.example`: Production environment variables template.
- `scripts/verify_deployment.py`: Production deployment verification script.
- `tests/e2e/`: Opaque-box E2E test suite.
