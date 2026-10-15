#!/usr/bin/env python3
"""Awesome Dev Pipeline v2.0.0 Migration Safety Linter.

Enforces expand -> migrate -> contract patterns and prevents destructive DDL:
- Rejects raw DROP TABLE, DROP COLUMN, TRUNCATE.
- Requires ADD COLUMN statements to be idempotent (ADD COLUMN IF NOT EXISTS).
"""

import re
import sys
from pathlib import Path

DESTRUCTIVE_PATTERNS = [
    (
        re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
        "DROP TABLE is prohibited in automated migrations",
    ),
    (
        re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
        "DROP COLUMN violates expand/contract migration safety",
    ),
    (
        re.compile(r"\bTRUNCATE\s+TABLE\b|\bTRUNCATE\b", re.IGNORECASE),
        "TRUNCATE is destructive and prohibited",
    ),
]

ADD_COLUMN_PATTERN = re.compile(
    r"\bALTER\s+TABLE\s+\w+\s+ADD\s+COLUMN\s+(?!IF\s+NOT\s+EXISTS\b)", re.IGNORECASE
)


def lint_migrations(migrations_dir: Path) -> list[str]:
    violations: list[str] = []
    if not migrations_dir.exists():
        return violations

    for sql_file in sorted(migrations_dir.glob("*.sql")):
        content = sql_file.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue

            for pattern, reason in DESTRUCTIVE_PATTERNS:
                if pattern.search(stripped):
                    violations.append(f"{sql_file.name}:{line_num}: {reason} -> '{stripped}'")

            if ADD_COLUMN_PATTERN.search(stripped):
                violations.append(
                    f"{sql_file.name}:{line_num}: ADD COLUMN must use 'IF NOT EXISTS' "
                    f"for idempotency -> '{stripped}'"
                )

    return violations


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    migrations_dir = base_dir / "chatlens-v2" / "backend" / "migrations"

    violations = lint_migrations(migrations_dir)
    if violations:
        print("❌ Migration Safety Violations Detected:", file=sys.stderr)
        for v in violations:
            print(f"  • {v}", file=sys.stderr)
        return 1

    print("✓ All migrations passed expand/contract safety checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
