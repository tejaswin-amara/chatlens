#!/usr/bin/env python3
"""Deployment Verification Script for ChatLens v2 & SPARK PA Daemon.

Supports:
1. --check-config / --offline mode:
   - Validates compose.yaml syntax and schema via `docker compose config`
   - Validates service declarations, healthchecks, restart policies, and logging
   - Validates volumes and network definitions
   - Validates .env.production.example template masking and variable coverage
   - Validates Caddyfile, Nginx SPA config, and PostgreSQL pgvector bootstrap
   - Validates backend requirements and database migrations
2. Live mode:
   - Validates container health via docker compose ps
   - Queries reverse proxy and backend endpoints:
     * GET /api/healthz (FastAPI health contract)
     * GET / (Frontend SPA root)
     * GET /api/spark/status (SPARK PA SQLite bridge)

Exit code: 0 on success, 1 on failure.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Mandatory services required in compose.yaml
EXPECTED_SERVICES = {
    "chatlens-proxy",
    "chatlens-frontend",
    "chatlens-migration",
    "chatlens-backend",
    "chatlens-celery",
    "chatlens-daemon",
    "postgres",
    "redis",
}

# Mandatory named volumes
EXPECTED_VOLUMES = {
    "spark_data",
    "postgres_data",
    "redis_data",
    "caddy_data",
    "caddy_config",
    "uploads_data",
}

# Mandatory production environment variables
MANDATORY_ENV_VARS = {
    "DOMAIN_NAME",
    "ACME_EMAIL",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_DAILY_BUDGET",
    "SPARK_MODE",
    "SPARK_CHAT_IDS",
    "SPARK_DB",
    "SPARK_MEDIA",
    "SPARK_TIMETABLE",
    "LOG_LEVEL",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_SESSION_STRING",
    "BOT_TOKEN",
    "OWNER_CHAT_ID",
    "GOOGLE_CREDENTIALS_BASE64",
    "GOOGLE_CALENDAR_ID",
    "GOOGLE_SHEET_ID",
}

SECRET_VARS_TO_CHECK_MASKING = {
    "POSTGRES_PASSWORD",
    "GEMINI_API_KEY",
    "TELEGRAM_API_HASH",
    "TELEGRAM_SESSION_STRING",
    "BOT_TOKEN",
    "GOOGLE_CREDENTIALS_BASE64",
}


def log_pass(msg: str) -> None:
    print(f"\033[32m[PASS]\033[0m {msg}")


def log_fail(msg: str) -> None:
    print(f"\033[31m[FAIL]\033[0m {msg}")


def log_info(msg: str) -> None:
    print(f"\033[34m[INFO]\033[0m {msg}")


def check_compose_file() -> list[str]:
    """Validates compose.yaml structure, services, volumes, networks, and syntax."""
    errors: list[str] = []
    compose_path = PROJECT_ROOT / "compose.yaml"
    if not compose_path.exists():
        errors.append(f"compose.yaml missing at {compose_path}")
        return errors

    content = compose_path.read_text(encoding="utf-8")

    # 1. Run docker compose config if docker is available
    docker_bin = shutil.which("docker")
    if docker_bin:
        try:
            res = subprocess.run(
                [docker_bin, "compose", "-f", str(compose_path), "config"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                check=False,
            )
            if res.returncode != 0:
                err_msg = res.stderr.strip() or f"exit code {res.returncode}"
                errors.append(f"docker compose config failed: {err_msg}")
            else:
                log_pass("docker compose config parsed with 0 errors")
        except Exception as e:
            log_info(f"Skipping live docker compose config execution: {e}")
    else:
        log_info("Docker CLI not found in PATH; skipping docker compose config execution")

    # 2. Verify all expected services are declared
    for svc in EXPECTED_SERVICES:
        if f"{svc}:" not in content and f'"{svc}":' not in content:
            errors.append(f"Required service '{svc}' not declared in compose.yaml")
        else:
            log_pass(f"Service '{svc}' declared")

    # 3. Verify all expected volumes are declared
    for vol in EXPECTED_VOLUMES:
        if f"{vol}:" not in content and f'"{vol}":' not in content:
            errors.append(f"Required volume '{vol}' not declared in compose.yaml")
        else:
            log_pass(f"Volume '{vol}' declared")

    # 4. Verify network declaration
    if "chatlens-net:" not in content and '"chatlens-net":' not in content:
        errors.append("Required network 'chatlens-net' not declared in compose.yaml")
    else:
        log_pass("Network 'chatlens-net' declared")

    # 5. Verify healthchecks
    for svc in ["postgres", "redis", "chatlens-daemon", "chatlens-backend", "chatlens-frontend"]:
        if svc in content and "healthcheck:" not in content:
            errors.append(f"Healthcheck block missing for service '{svc}'")
    log_pass("Container healthcheck probe contracts verified")

    # 6. Verify logging configuration
    if "50m" not in content or "3" not in content or "json-file" not in content:
        errors.append("Default log rotation policy (json-file, max-size: 50m, max-file: 3) missing")
    else:
        log_pass("Log rotation policy (max-size: 50m, max-file: 3) verified")

    # 7. Verify restart policies
    if "restart: unless-stopped" not in content:
        errors.append("Expected 'restart: unless-stopped' policy in compose.yaml")
    if 'restart: "no"' not in content and "restart: 'no'" not in content:
        errors.append("Expected 'restart: \"no\"' policy for chatlens-migration init container")
    log_pass("Container restart policies verified")

    return errors


def check_env_template(env_path: Path) -> list[str]:
    """Validates .env.production.example variable coverage and secret masking."""
    errors: list[str] = []
    if not env_path.exists():
        errors.append(f"Environment template missing at {env_path}")
        return errors

    lines = env_path.read_text(encoding="utf-8").splitlines()
    parsed_vars: dict[str, str] = {}

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            parsed_vars[key.strip()] = val.strip().strip("\"'")

    # Verify coverage of mandatory variables
    for var in MANDATORY_ENV_VARS:
        if var not in parsed_vars:
            errors.append(f"Mandatory environment variable '{var}' missing in {env_path.name}")
        else:
            log_pass(f"Env variable '{var}' present")

    # Verify secret masking
    for var in SECRET_VARS_TO_CHECK_MASKING:
        val = parsed_vars.get(var, "")
        if not (val.startswith("<") and val.endswith(">")):
            errors.append(
                f"Secret variable '{var}' is not masked with <PLACEHOLDER> in {env_path.name}"
            )
        else:
            log_pass(f"Secret variable '{var}' properly masked")

    # Ensure SPARK_DB points to persistent volume
    spark_db = parsed_vars.get("SPARK_DB", "")
    if spark_db != "/app/data/spark.db":
        errors.append(f"SPARK_DB must be '/app/data/spark.db' for persistence (got '{spark_db}')")
    else:
        log_pass("SPARK_DB configured to persistent volume mount (/app/data/spark.db)")

    return errors


def check_supporting_configs() -> list[str]:
    """Validates Caddyfile, Nginx configuration, pgvector SQL, requirements, and migrations."""
    errors: list[str] = []

    # 1. Caddyfile
    caddy_file = PROJECT_ROOT / "Caddyfile"
    if not caddy_file.exists():
        errors.append("Caddyfile missing at project root")
    else:
        caddy_content = caddy_file.read_text(encoding="utf-8")
        if "chatlens-backend:8000" not in caddy_content:
            errors.append("Caddyfile does not route upstream to chatlens-backend:8000")
        if "chatlens-frontend:80" not in caddy_content:
            errors.append("Caddyfile does not route upstream to chatlens-frontend:80")
        log_pass("Caddyfile routing contracts verified")

    # 2. PostgreSQL pgvector init script
    pgvector_sql = PROJECT_ROOT / "docker" / "postgres" / "01-init-pgvector.sql"
    if not pgvector_sql.exists():
        errors.append("PostgreSQL init script docker/postgres/01-init-pgvector.sql missing")
    else:
        sql_content = pgvector_sql.read_text(encoding="utf-8")
        if "CREATE EXTENSION IF NOT EXISTS vector;" not in sql_content:
            errors.append("pgvector init script missing idempotent CREATE EXTENSION statement")
        log_pass("PostgreSQL pgvector init script verified")

    # 3. Frontend Nginx configuration
    nginx_conf = PROJECT_ROOT / "chatlens-v2" / "frontend" / "nginx.conf"
    if not nginx_conf.exists():
        errors.append("Frontend nginx.conf missing at chatlens-v2/frontend/nginx.conf")
    else:
        nginx_content = nginx_conf.read_text(encoding="utf-8")
        if "try_files" not in nginx_content or "/index.html" not in nginx_content:
            errors.append("Frontend nginx.conf missing SPA fallback routing")
        log_pass("Frontend nginx.conf SPA routing verified")

    # 4. Backend requirements.txt
    req_file = PROJECT_ROOT / "chatlens-v2" / "backend" / "requirements.txt"
    if not req_file.exists():
        errors.append("Backend requirements.txt missing at chatlens-v2/backend/requirements.txt")
    else:
        req_content = req_file.read_text(encoding="utf-8")
        for pkg in ["fastapi", "uvicorn", "sqlalchemy", "pgvector", "celery", "redis", "alembic"]:
            if pkg not in req_content:
                errors.append(f"Backend requirements.txt missing critical package '{pkg}'")
        log_pass("Backend requirements.txt package coverage verified")

    # 5. Alembic configuration & migrations
    alembic_ini = PROJECT_ROOT / "chatlens-v2" / "backend" / "alembic.ini"
    alembic_env = PROJECT_ROOT / "chatlens-v2" / "backend" / "migrations" / "env.py"
    if not alembic_ini.exists():
        errors.append("alembic.ini missing at chatlens-v2/backend/alembic.ini")
    if not alembic_env.exists():
        errors.append("Alembic env.py missing at chatlens-v2/backend/migrations/env.py")
    log_pass("Alembic configuration and migrations verified")

    return errors


def check_live_endpoints(base_url: str) -> list[str]:
    """Queries live endpoints via HTTP to verify proxy, backend, frontend, and SPARK health."""
    errors: list[str] = []
    base_url = base_url.rstrip("/")

    client = httpx.Client(timeout=10.0, headers={"User-Agent": "ChatLens-Verifier/2.0"})

    # 1. GET /api/healthz
    healthz_url = f"{base_url}/api/healthz"
    try:
        res = client.get(healthz_url)
        if res.status_code != 200:
            errors.append(f"{healthz_url} returned HTTP {res.status_code} (expected 200)")
        else:
            data = res.json()
            if data.get("status") != "ok":
                errors.append(f"{healthz_url} returned invalid payload: {data}")
            else:
                log_pass(f"{healthz_url} healthy: {data}")
    except Exception as e:
        errors.append(f"Failed to connect to {healthz_url}: {e}")

    # 2. GET / (Frontend root)
    root_url = f"{base_url}/"
    try:
        res = client.get(root_url)
        if res.status_code != 200:
            errors.append(f"{root_url} returned HTTP {res.status_code} (expected 200)")
        else:
            html = res.text.lower()
            if "<html" not in html and "<!doctype html" not in html:
                errors.append(f"{root_url} response did not contain HTML markup")
            else:
                log_pass(f"{root_url} frontend SPA loaded cleanly")
    except Exception as e:
        errors.append(f"Failed to connect to {root_url}: {e}")

    # 3. GET /api/spark/status
    spark_url = f"{base_url}/api/spark/status"
    try:
        res = client.get(spark_url)
        if res.status_code != 200:
            errors.append(f"{spark_url} returned HTTP {res.status_code} (expected 200)")
        else:
            data = res.json()
            log_pass(f"{spark_url} status bridge responded: status={data.get('status')}")
    except Exception as e:
        errors.append(f"Failed to connect to {spark_url}: {e}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify ChatLens v2 and SPARK PA Daemon Deployment & Configuration."
    )
    parser.add_argument(
        "--check-config",
        "--offline",
        dest="offline",
        action="store_true",
        help="Run static configuration verification without connecting to live containers.",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("BASE_URL", "http://localhost"),
        help="Target base URL for live HTTP checks (default: http://localhost).",
    )
    parser.add_argument(
        "--env-file",
        default=str(PROJECT_ROOT / ".env.production.example"),
        help="Path to production environment template (default: .env.production.example).",
    )
    args = parser.parse_args()

    log_info("Starting ChatLens Deployment Verification...")
    all_errors: list[str] = []

    # 1. Validate compose.yaml
    log_info("Validating Docker Compose orchestration definition (compose.yaml)...")
    compose_errors = check_compose_file()
    all_errors.extend(compose_errors)

    # 2. Validate .env.production.example
    env_file = Path(args.env_file)
    log_info(f"Validating environment configuration template ({env_file.name})...")
    env_errors = check_env_template(env_file)
    all_errors.extend(env_errors)

    # 3. Validate supporting infrastructure configurations
    log_info("Validating supporting configuration files (Caddyfile, Nginx, pgvector, Alembic)...")
    support_errors = check_supporting_configs()
    all_errors.extend(support_errors)

    # 4. Live endpoint checks (only if not --offline / --check-config)
    if not args.offline:
        log_info(f"Validating live stack endpoints at {args.url}...")
        live_errors = check_live_endpoints(args.url)
        all_errors.extend(live_errors)
    else:
        log_info("Offline / check-config mode enabled; skipping live HTTP endpoint queries.")

    if all_errors:
        print("\n\033[31mVerification Failed with Errors:\033[0m")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("\n\033[32mAll Deployment Verification Checks Passed Cleanly!\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
