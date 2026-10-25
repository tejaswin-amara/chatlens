"""Scan deliberate code shortcuts and write a local-only technical-debt report."""

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
            match = DEBT_PATTERN.search(line)
            if match:
                rel_path = path.relative_to(repo_root).as_posix()
                entries.append(
                    {
                        "file_line": f"{rel_path}:{idx}",
                        "comment": match.group(1).strip(),
                    }
                )

    return entries


def update_debt_file(entries: list[dict[str, str]], output_path: Path | None = None) -> int:
    if output_path is None:
        # scratch/ is git-ignored; generated reports must not appear in the repository root.
        output_path = Path(__file__).resolve().parent.parent / "scratch" / "PONYTAIL-DEBT.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rot_risk_count = sum(1 for entry in entries if "upgrade" not in entry["comment"].lower())

    rows = []
    for idx, entry in enumerate(entries, 1):
        debt_id = f"DEBT-{idx:02d}"
        file_line = entry["file_line"]
        comment = entry["comment"]
        rot_risk = "no-trigger" if "upgrade" not in comment.lower() else "Tracked"
        rows.append(f"| {debt_id} | `{file_line}` | {comment} | {rot_risk} |")

    table_rows = "\n".join(rows) if rows else "| None | - | No active debt annotations | Clean |"
    content = f"""# Ponytail Technical Debt Ledger

This report is generated locally from code annotations (`shortcut:` / `ponytail:`). It is not a
source file and must not be committed.

| ID | File:Line | Description / Ceiling / Upgrade Path | Status |
|---|---|---|---|
{table_rows}

**Summary**: {len(entries)} total debt markers tracked in ledger.
"""
    output_path.write_text(content, encoding="utf-8")
    print(
        f"Updated local report {output_path} with {len(entries)} entries "
        f"({rot_risk_count} rot-risk markers (no-trigger))."
    )
    return rot_risk_count


def main() -> int:
    entries = harvest_debt()
    rot_risk_count = sum(1 for entry in entries if "upgrade" not in entry["comment"].lower())
    update_debt_file(entries)
    if rot_risk_count > 0:
        print(
            f"ERROR: {rot_risk_count} untracked debt markers lack upgrade triggers!",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
