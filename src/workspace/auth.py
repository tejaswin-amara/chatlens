"""Google OAuth / Service Account credential resolver and API service factory."""

import base64
import json
from typing import Any

from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import Resource, build

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/tasks", "https://www.googleapis.com/auth/spreadsheets"]


class GoogleWorkspaceAuth:
    def __init__(self, b64_creds: str | None = None) -> None:
        self.b64_creds = b64_creds or settings.google_credentials_base64
        self._creds: Any | None = None

    def get_credentials(self) -> Any:
        if self._creds:
            return self._creds

        if not self.b64_creds:
            raise ValueError("GOOGLE_CREDENTIALS_BASE64 environment variable is not set.")

        try:
            decoded = base64.b64decode(self.b64_creds).decode("utf-8")
            cred_dict = json.loads(decoded)
        except Exception as e:
            raise ValueError(f"Failed to decode GOOGLE_CREDENTIALS_BASE64 JSON: {e}") from e

        if cred_dict.get("type") == "service_account":
            self._creds = ServiceAccountCredentials.from_service_account_info(
                cred_dict, scopes=SCOPES
            )
        else:
            self._creds = Credentials.from_authorized_user_info(cred_dict, scopes=SCOPES)

        return self._creds

    def get_calendar_service(self) -> Resource:
        return build("calendar", "v3", credentials=self.get_credentials())

    def get_tasks_service(self) -> Resource:
        return build("tasks", "v1", credentials=self.get_credentials())

    def get_sheets_service(self) -> Resource:
        return build("sheets", "v4", credentials=self.get_credentials())




workspace_auth = GoogleWorkspaceAuth()
