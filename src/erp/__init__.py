"""KLU ERP integration module for SPARK PA daemon."""

from src.erp.client import KLUERPClient, klu_erp
from src.erp.scrapers import (
    parse_attendance_records,
    parse_fee_records,
    parse_generic_tables,
    parse_marks_records,
)
from src.erp.sync import AcademicERPSyncAgent, erp_sync_agent, next_sync_run, run_erp_sync

__all__ = [
    "KLUERPClient",
    "klu_erp",
    "AcademicERPSyncAgent",
    "erp_sync_agent",
    "next_sync_run",
    "run_erp_sync",
    "parse_attendance_records",
    "parse_marks_records",
    "parse_fee_records",
    "parse_generic_tables",
]
