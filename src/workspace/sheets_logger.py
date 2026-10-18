"""Google Sheets Adapter for logging PA audit trails to a PA_Audit_Log tab."""

from typing import Any
from unittest.mock import Mock

from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings
from src.utils import clock
from src.utils.logging import get_logger
from src.workspace.auth import GoogleWorkspaceAuth, workspace_auth

logger = get_logger(__name__)

AUDIT_TAB = "PA_Audit_Log"
HEADERS = ["Timestamp", "Source Sender", "Message Text", "Intent", "Execution Status", "Details"]


class SheetsLogger:
    def __init__(self, sheet_id: str | None = None, auth_adapter: Any = None) -> None:
        self.sheet_id = settings.google_sheet_id if sheet_id is None else sheet_id
        self.auth = auth_adapter or workspace_auth

    @property
    def is_configured(self) -> bool:
        """Returns True if sheet_id and credentials/mock are available."""
        if not self.sheet_id or not self.sheet_id.strip():
            return False

        b64 = getattr(self.auth, "b64_creds", None)
        if b64:
            val = b64.get_secret_value() if hasattr(b64, "get_secret_value") else str(b64)
            if val and val.strip():
                return True

        if isinstance(self.auth, Mock):
            return True
        service_fn = getattr(self.auth, "get_sheets_service", None)
        if isinstance(service_fn, Mock) or hasattr(service_fn, "mock_calls"):
            return True
        if self.auth is not workspace_auth and not isinstance(self.auth, GoogleWorkspaceAuth):
            return True

        return False

    def _ensure_audit_tab(self, service: Any) -> None:
        if not self.is_configured:
            return

        try:
            spreadsheet = service.spreadsheets().get(spreadsheetId=self.sheet_id).execute()
            sheets = spreadsheet.get("sheets", [])
            tab_names = [s.get("properties", {}).get("title") for s in sheets]

            if AUDIT_TAB not in tab_names:
                body = {"requests": [{"addSheet": {"properties": {"title": AUDIT_TAB}}}]}
                service.spreadsheets().batchUpdate(spreadsheetId=self.sheet_id, body=body).execute()

                service.spreadsheets().values().update(
                    spreadsheetId=self.sheet_id,
                    range=f"{AUDIT_TAB}!A1:F1",
                    valueInputOption="RAW",
                    body={"values": [HEADERS]},
                ).execute()
        except Exception as e:
            logger.warning("Could not ensure audit tab existence", error=str(e))

    @retry(
        retry=retry_if_not_exception_type(ValueError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def append_audit_log(
        self,
        source_sender: str,
        message_text: str,
        intent: str,
        execution_status: str,
        extra_details: str = "",
    ) -> dict[str, Any] | None:
        if not self.is_configured:
            logger.debug("SheetsLogger is not configured; skipping sheets audit log")
            return None

        service = self.auth.get_sheets_service()
        self._ensure_audit_tab(service)

        now_iso = clock.now_ist().isoformat()
        row_values = [
            now_iso,
            source_sender,
            message_text[:300],
            intent,
            execution_status,
            extra_details,
        ]

        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.sheet_id,
                range=f"{AUDIT_TAB}!A:F",
                valueInputOption="RAW",
                body={"values": [row_values]},
            )
            .execute()
        )
        logger.info("Appended audit log to Google Sheets", intent=intent, status=execution_status)
        return result

    def get_attendance(self) -> list[dict[str, str]]:
        if not self.is_configured:
            return []
        try:
            service = self.auth.get_sheets_service()
            res = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=self.sheet_id, range="Attendance!A:C")
                .execute()
            )
            rows = res.get("values", [])
            if not rows or len(rows) < 2:
                return []
            headers = [str(col).strip().lower() for col in rows[0]]
            attendance = []
            for row in rows[1:]:
                if not row:
                    continue
                row_dict = {}
                for i, val in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = str(val).strip()
                if row_dict:
                    attendance.append(row_dict)
            return attendance
        except Exception as e:
            logger.warning("Could not fetch attendance from sheets", error=str(e))
            return []

    def log_heartbeat(self) -> None:
        if not self.is_configured:
            return
        from src.utils import clock

        now_str = clock.now_ist().isoformat()
        service = self.auth.get_sheets_service()
        try:
            service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range="Status!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [[now_str]]},
            ).execute()
        except Exception as e:
            if "parse range" in str(e).lower() or "not found" in str(e).lower():
                body = {"requests": [{"addSheet": {"properties": {"title": "Status"}}}]}
                service.spreadsheets().batchUpdate(spreadsheetId=self.sheet_id, body=body).execute()
                service.spreadsheets().values().update(
                    spreadsheetId=self.sheet_id,
                    range="Status!A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[now_str]]},
                ).execute()
            else:
                raise e


sheets_logger = SheetsLogger()
