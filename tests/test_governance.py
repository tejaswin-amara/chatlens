"""Automated governance and ADR compliance tests."""

from pathlib import Path

from scripts.check_adrs import check_adrs
from scripts.harvest_debt import harvest_debt


def test_adr_compliance() -> None:
    errors = check_adrs()
    assert not errors, f"ADR validation errors found: {errors}"


def test_debt_ledger_sync() -> None:
    entries = harvest_debt()
    debt_file = Path(__file__).resolve().parent.parent / "PONYTAIL-DEBT.md"
    assert debt_file.exists(), "PONYTAIL-DEBT.md does not exist."
    content = debt_file.read_text(encoding="utf-8")
    for e in entries:
        assert e["file_line"] in content, (
            f"Debt entry {e['file_line']} missing from PONYTAIL-DEBT.md. "
            f"Run `uv run python scripts/harvest_debt.py` to synchronize."
        )
