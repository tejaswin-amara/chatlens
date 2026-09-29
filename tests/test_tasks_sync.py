"""Unit tests for Google Tasks sync adapter."""

from unittest.mock import MagicMock

from src.workspace.tasks_sync import TasksSync


def test_create_task_with_course_code_tag() -> None:
    mock_auth = MagicMock()
    mock_service = MagicMock()
    mock_auth.get_tasks_service.return_value = mock_service

    mock_service.tasks().insert().execute.return_value = {
        "id": "task_789",
        "title": "[25CS2103E] Lab Record Submission",
    }

    adapter = TasksSync(auth_adapter=mock_auth)
    res = adapter.create_task(
        title="Lab Record Submission",
        due_date="2026-04-05",
        course_code="25CS2103E",
    )

    assert res["id"] == "task_789"
    call_args = mock_service.tasks().insert.call_args
    body = call_args[1]["body"]
    assert body["title"] == "[25CS2103E] Lab Record Submission"
    assert "due" in body
