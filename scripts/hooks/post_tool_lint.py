"""Lightweight PostToolUse lint interceptor for agent harnesses."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    changed_files = [f for f in sys.argv[1:] if f.endswith(".py") and Path(f).exists()]
    if not changed_files:
        return 0

    res = subprocess.run(
        ["uv", "run", "ruff", "check", *changed_files],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print(f"[ECC Hook] Ruff lint feedback:\n{res.stdout or res.stderr}", file=sys.stderr)
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
