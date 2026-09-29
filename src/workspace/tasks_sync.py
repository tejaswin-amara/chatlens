"""Google Tasks Adapter for creating tasks with course code tags and due dates."""

from datetime import datetime
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.logging import get_logger
from src.workspace.auth import workspace_auth

logger = get_logger(__name__)


class TasksSync:
    def __init__(self, auth_adapter: Any = None) -> None:
        self.auth = auth_adapter or workspace_auth

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def create_task(
        self,
        title: str,
        notes: str | None = None,
        due_date: str | None = None,
        course_code: str | None = None,
    ) -> dict[str, Any]:
        service = self.auth.get_tasks_service()

        clean_title = title.strip()
        if course_code and not clean_title.startswith(f"[{course_code}]"):
            clean_title = f"[{course_code}] {clean_title}"

        task_body: dict[str, Any] = {
            "title": clean_title,
            "notes": notes or "Created by ChatLens PA Bot",
        }

        if due_date:
            try:
                dt = datetime.strptime(due_date, "%Y-%m-%d")
                task_body["due"] = dt.strftime("%Y-%m-%dT23:59:59.000Z")
            except ValueError:
                task_body["due"] = due_date

        created = service.tasks().insert(tasklist="@default", body=task_body).execute()
        logger.info("Created Google Task", task_id=created.get("id"), title=clean_title)
        return created


tasks_sync = TasksSync()
