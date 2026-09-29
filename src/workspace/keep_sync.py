"""Google Keep Adapter for maintaining a pinned live timetable note card."""

from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.utils.logging import get_logger
from src.workspace.auth import workspace_auth

logger = get_logger(__name__)


class KeepSync:
    def __init__(self, note_id: str | None = None, auth_adapter: Any = None) -> None:
        self.note_id = note_id or settings.google_keep_note_id
        self.auth = auth_adapter or workspace_auth

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def update_live_timetable_note(
        self, today_timetable_text: str, title: str = "Today Live Timetable & Room Assignments"
    ) -> dict[str, Any] | None:
        if not self.note_id:
            logger.debug("GOOGLE_KEEP_NOTE_ID not configured; skipping Keep sync")
            return None

        try:
            service = self.auth.get_keep_service()
            is_prefix = self.note_id.startswith("notes/")
            note_name = self.note_id if is_prefix else f"notes/{self.note_id}"
            body = {"title": title, "body": {"text": {"text": today_timetable_text}}}
            updated = (
                service.notes()
                .patch(name=note_name, updateMask="title,body", body=body)
                .execute()
            )
            logger.info("Updated Google Keep live timetable note", note_id=note_name)
            return updated
        except Exception as e:
            logger.warning("Google Keep API update failed; fallback logged", error=str(e))
            return {"status": "fallback", "text": today_timetable_text}


keep_sync = KeepSync()
