#!/usr/bin/env bash
# ChatLens v2 & SPARK PA Deployment Verification Wrapper
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if command -v uv >/dev/null 2>&1; then
    exec uv run python "$SCRIPT_DIR/verify_deployment.py" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT_DIR/verify_deployment.py" "$@"
else
    exec python "$SCRIPT_DIR/verify_deployment.py" "$@"
fi
