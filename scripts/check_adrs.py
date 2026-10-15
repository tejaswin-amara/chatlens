"""Linter and integrity checker for Architecture Decision Records (ADRs)."""

import re
import sys
from pathlib import Path

VALID_STATUSES = {"proposed", "accepted", "rejected", "deprecated", "superseded"}


def check_adrs(adr_dir: Path | None = None) -> list[str]:
    if adr_dir is None:
        adr_dir = Path(__file__).resolve().parent.parent / "adr"

    if not adr_dir.exists():
        return ["ADR directory not found."]

    errors = []
    adr_files = list(adr_dir.glob("*.md"))

    for path in adr_files:
        if path.name == "threat-model.md":
            # STRIDE threat model has its own format
            continue

        # Check naming convention: 0001-slug.md
        if not re.match(r"^\d{4}-[a-z0-9-]+\.md$", path.name):
            errors.append(f"{path.name}: Invalid filename format. Must be NNNN-slug.md")
            continue

        content = path.read_text(encoding="utf-8")

        # Check required sections
        if "## Context" not in content:
            errors.append(f"{path.name}: Missing '## Context' section.")
        if "## Decision" not in content:
            errors.append(f"{path.name}: Missing '## Decision' section.")

        # Check status
        status_match = re.search(r"\* Status:\s*([a-zA-Z]+)", content, re.IGNORECASE)
        if not status_match:
            errors.append(f"{path.name}: Missing '* Status:' declaration.")
        else:
            status = status_match.group(1).lower()
            if status not in VALID_STATUSES:
                errors.append(
                    f"{path.name}: Invalid status '{status}'. Must be one of {VALID_STATUSES}."
                )

    return errors


def main() -> int:
    errors = check_adrs()
    if errors:
        print("ADR validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  ❌ {err}", file=sys.stderr)
        return 1

    print("✓ All ADRs conform to MADR standard and naming conventions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
