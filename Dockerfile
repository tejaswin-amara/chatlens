# Multi-stage production Dockerfile for SPARK PA Daemon
# Target Runtime: Python 3.12-slim + uv
# Timezone: Asia/Kolkata (IST)

FROM python:3.12-slim AS builder

# Install uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Cache dependencies
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Runtime stage
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    TZ="Asia/Kolkata"

WORKDIR /app

# Create unprivileged user (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/false -m appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source and data
COPY --chown=appuser:appgroup src /app/src
COPY --chown=appuser:appgroup data /app/data
COPY --chown=appuser:appgroup pyproject.toml /app/

# Ensure workspace writable for SQLite WAL mode
RUN chown -R appuser:appgroup /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import sqlite3; conn = sqlite3.connect('spark.db'); conn.execute('PRAGMA integrity_check'); conn.close()" || exit 1

CMD ["python", "-m", "src.main"]
