"""Harvester script to scan codebase shortcuts and update PONYTAIL-DEBT.md."""

import re
import sys
from pathlib import Path

DEBT_PATTERN = re.compile(r"(?:#|//|/\*)\s*(?:shortcut|ponytail):\s*(.*)", re.IGNORECASE)
EXCLUDE_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}


def harvest_debt(repo_root: Path | None = None) -> list[dict[str, str]]:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    entries = []
    for path in repo_root.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.is_dir() or path.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
            continue

        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for idx, line in enumerate(lines, 1):
            m = DEBT_PATTERN.search(line)
            if m:
                text = m.group(1).strip()
                rel_path = path.relative_to(repo_root).as_posix()
                entries.append(
                    {
                        "file_line": f"{rel_path}:{idx}",
                        "comment": text,
                    }
                )

    return entries


def update_debt_file(entries: list[dict[str, str]], output_path: Path | None = None) -> None:
    if output_path is None:
        output_path = Path(__file__).resolve().parent.parent / "PONYTAIL-DEBT.md"

    rows = []
    for idx, e in enumerate(entries, 1):
        debt_id = f"DEBT-{idx:02d}"
        file_line = e["file_line"]
        comment = e["comment"]
        rot_risk = "no-trigger" if "upgrade" not in comment.lower() else "Tracked"
        rows.append(f"| {debt_id} | `{file_line}` | {comment} | {rot_risk} |")

    table_rows = "\n".join(rows) if rows else "| None | - | No active debt annotations | Clean |"

    content = f"""# Ponytail Technical Debt Ledger

Tracked deferrals and shortcuts harvested from codebase annotations (`shortcut:` / `ponytail:`).

| ID | File:Line | Description / Ceiling / Upgrade Path | Status |
|---|---|---|---|
{table_rows}

**Summary**: {len(entries)} total debt markers tracked in ledger.
"""
    output_path.write_text(content, encoding="utf-8")
    print(f"Updated {output_path} with {len(entries)} entries.")


def main() -> int:
    entries = harvest_debt()
    update_debt_file(entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
