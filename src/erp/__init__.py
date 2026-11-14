"""KLU ERP integration module for SPARK PA daemon."""

from src.erp.client import KLUERPClient, klu_erp
from src.erp.scrapers import (
    compute_remaining_classes,
    parse_attendance_records,
    parse_fee_records,
    parse_generic_tables,
    parse_hall_ticket_records,
    parse_marks_records,
)
from src.erp.sync import (
    AcademicERPSyncAgent,
    erp_keep_alive_ping,
    erp_sync_agent,
    is_daytime_academic_hours,
    next_sync_run,
    run_erp_keep_alive,
    run_erp_sync,
)

__all__ = [
    "KLUERPClient",
    "klu_erp",
    "AcademicERPSyncAgent",
    "erp_sync_agent",
    "next_sync_run",
    "run_erp_sync",
    "run_erp_keep_alive",
    "erp_keep_alive_ping",
    "is_daytime_academic_hours",
    "compute_remaining_classes",
    "parse_attendance_records",
    "parse_marks_records",
    "parse_fee_records",
    "parse_hall_ticket_records",
    "parse_generic_tables",
]
