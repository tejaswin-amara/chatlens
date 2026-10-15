#!/usr/bin/env python3
"""Awesome Dev Pipeline v2.0.0 Archetype Classifier.

Classifies repository workspaces into standardized archetypes:
- cli (Python daemon / scripts)
- web-api (FastAPI / backend or Next.js / frontend)
"""

import argparse
import json
import sys
from pathlib import Path


def detect_archetype(target_dir: Path) -> dict[str, str]:
    target_dir = target_dir.resolve()

    workspaces: dict[str, str] = {}

    # Check root workspace
    if (target_dir / "pyproject.toml").exists() or (target_dir / "src" / "main.py").exists():
        workspaces["."] = "cli"
    elif (target_dir / "package.json").exists():
        workspaces["."] = "web-api"
    else:
        workspaces["."] = "unknown"

    # Check backend workspace
    backend_dir = target_dir / "chatlens-v2" / "backend"
    if backend_dir.exists() and (
        (backend_dir / "main.py").exists() or (backend_dir / "models.py").exists()
    ):
        workspaces["chatlens-v2/backend"] = "web-api"

    # Check frontend workspace
    frontend_dir = target_dir / "chatlens-v2" / "frontend"
    if frontend_dir.exists() and (frontend_dir / "package.json").exists():
        workspaces["chatlens-v2/frontend"] = "web-api"

    return workspaces


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect workspace archetypes.")
    parser.add_argument("path", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    results = detect_archetype(Path(args.path))

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        for workspace, archetype in results.items():
            print(f"{workspace}: {archetype}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
