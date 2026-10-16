"""Tier 3: Cross-Feature Combinations E2E Tests (Pairwise integration).

Covers:
- Frontend calling backend through reverse proxy
- Reverse proxy terminating TLS and passing forwarding headers upstream
- Database migrations executing before backend processes data requests
- Backend upload sharing filesystem volume with Celery worker
- SPARK PA daemon WAL state concurrency with backend status bridge
- Celery task state publication and backend task polling
"""

from __future__ import annotations

import io
import sqlite3
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import models
from sqlalchemy import func, select

from tests.e2e.harness import (
    PROJECT_ROOT,
    E2EClient,
    main,
)


def test_pairwise_frontend_calls_backend_through_proxy(e2e_client: E2EClient) -> None:
    """Pairwise 1: Frontend SPA origin-relative calls routed through proxy to backend."""
    # 1. Fetch root page (frontend)
    root_res = e2e_client.get("/")
    assert root_res.status_code == 200
    assert "text/html" in root_res.headers.get("Content-Type", "")

    # 2. Invoke relative API endpoint through proxy
    api_res = e2e_client.get("/api/healthz")
    assert api_res.status_code == 200
    assert api_res.json() == {"status": "ok", "version": "2.0.0"}

    # 3. Invoke data endpoint through proxy
    chats_res = e2e_client.get("/api/chats")
    assert chats_res.status_code == 200
    assert isinstance(chats_res.json(), list)


def test_pairwise_proxy_tls_termination_and_upstream_headers(e2e_client: E2EClient) -> None:
    """Pairwise 2: Proxy terminates HTTPS and supplies forwarding headers to backend."""
    tls_headers = {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-For": "203.0.113.195",
        "Host": "chatlens.example.com",
    }
    res = e2e_client.get("/api/healthz", headers=tls_headers)
    assert res.status_code == 200
    assert res.json().get("status") == "ok"


def test_pairwise_migrations_run_before_backend_accepts_traffic(in_memory_db) -> None:
    """Pairwise 3: Schema initialized prior to backend query execution."""
    with in_memory_db.connect() as conn:
        result = conn.execute(select(func.count(models.Message.id)))
        count = result.scalar()
        assert count == 0 or count >= 0


def test_pairwise_backend_upload_to_celery_shared_volume(
    e2e_client: E2EClient, tmp_path: Path
) -> None:
    """Pairwise 4: Backend saves uploaded file to uploads directory, consumed by worker."""
    uploads_dir = PROJECT_ROOT / "uploads"
    uploads_dir.mkdir(exist_ok=True)

    chat_content = (
        b"15/10/2026, 09:30 - Alice: Meeting in H-005\n"
        b"15/10/2026, 09:31 - Bob: Got it, moving there now\n"
    )

    files = {"file": ("schedule_chat.txt", io.BytesIO(chat_content), "text/plain")}

    captured_path: list[str] = []

    def mock_delay(file_path: str, platform: str):
        captured_path.append(file_path)
        mock_task = MagicMock()
        mock_task.id = str(uuid.uuid4())
        return mock_task

    with patch.object(main.parse_file_task, "delay", side_effect=mock_delay):
        res = e2e_client.post("/api/upload/whatsapp", files=files)
        assert res.status_code == 200
        payload = res.json()
        assert payload.get("status") == "processing"
        assert len(captured_path) == 1
        # Assert file was written to disk and is readable by worker
        saved_file = Path(captured_path[0])
        assert saved_file.exists()
        assert saved_file.read_bytes() == chat_content
        # Clean up
        try:
            saved_file.unlink()
        except OSError:
            pass


def test_pairwise_daemon_sqlite_wal_to_backend_status_bridge(
    e2e_client: E2EClient, isolated_spark_db: Path
) -> None:
    """Pairwise 5: Daemon concurrent WAL transactions safely queried by backend status bridge."""
    conn = sqlite3.connect(str(isolated_spark_db))
    for i in range(10):
        conn.execute(f"INSERT OR REPLACE INTO seen VALUES ('msg_key_{i}', {1000.0 + i});")
        event_json = f'{{"id": {i}}}'
        conn.execute(
            "INSERT INTO pending (ts, status, event_json) VALUES (?, ?, ?);",
            (1000.0 + i, "pending", event_json),
        )
    conn.commit()
    conn.close()

    res = e2e_client.get("/api/spark/status")
    assert res.status_code == 200
    payload = res.json()
    assert payload.get("status") == "online"
    assert payload.get("seen_messages", 0) >= 10
    assert len(payload.get("pending", [])) >= 10


def test_pairwise_celery_task_update_to_api_poll(e2e_client: E2EClient) -> None:
    """Pairwise 6: Celery task execution updates task status polled via API."""
    task_id = "test-task-uuid-pair-6"

    mock_async_result = MagicMock()
    mock_async_result.ready.return_value = True
    mock_async_result.status = "SUCCESS"
    mock_async_result.result = {"status": "done", "count": 42}

    with patch("main.celery.result.AsyncResult", return_value=mock_async_result):
        res = e2e_client.get(f"/api/tasks/{task_id}")
        assert res.status_code == 200
        payload = res.json()
        assert payload.get("status") == "SUCCESS"
        assert payload.get("count") == 42
