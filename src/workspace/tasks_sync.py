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

        existing = service.tasks().list(
            tasklist="@default", showCompleted=False, showHidden=False
        ).execute()
        for item in existing.get("items", []):
            item_due = item.get("due", "")
            if item.get("title") == clean_title:
                if due_date and item_due.startswith(due_date):
                    return item
                elif not due_date and not item_due:
                    return item

        created = service.tasks().insert(tasklist="@default", body=task_body).execute()
        import json
        import sqlite3
        import time

        from src.config import settings
        with sqlite3.connect(settings.spark_db, isolation_level=None) as conn:
            conn.execute(
                "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
                (
                    time.time(), "insert", created["id"],
                    json.dumps({"action": "delete", "source": "tasks"})
                )
            )
        logger.info(
            "Created Google Task", task_id=created.get("id"), title=clean_title
        )
        return created



    def list_open_tasks(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        service = self.auth.get_tasks_service()
        # showCompleted false, showHidden false
        try:
            results = service.tasks().list(
                tasklist="@default", showCompleted=False, showHidden=False
            ).execute()
        except Exception:
            return []

        items = results.get("items", [])
        filtered = []
        for item in items:
            due_str = item.get("due", "")
            if due_str:
                # Compare on the date part
                # due is RFC3339 timestamp string
                due_dt = due_str[:10]
                if start_date <= due_dt <= end_date:
                    filtered.append(item)

        return filtered

tasks_sync = TasksSync()
