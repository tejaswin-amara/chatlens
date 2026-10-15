# Technical Debt Command (`/debt`)

Harvest, inspect, and synchronize the repository's deliberate technical shortcuts and deferrals:

1. **Scan**:
   Run the debt harvester script:
   ```bash
   uv run python scripts/harvest_debt.py
   ```
2. **Review Ledger**:
   - Inspect `PONYTAIL-DEBT.md` for any entries marked `no-trigger` (rot risk).
   - Flag any entries where the current load or requirements cross the stated ceiling.
3. **Report**:
   Output the total count of debt items, items with missing triggers, and action items for immediate remediation.
