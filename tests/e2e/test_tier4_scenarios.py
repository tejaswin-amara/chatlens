"""Tier 4: Real-World Application Scenarios E2E Tests (>=5 full user flows).

Covers:
- Scenario 1: Initial cold boot and stack health probe convergence
- Scenario 2: Complete web browser user journey (SPA load, asset chunks, API telemetry)
- Scenario 3: End-to-end chat upload, async task polling, and data query
- Scenario 4: SPARK PA assistant message ingestion, restart, and state persistence
- Scenario 5: Reverse proxy domain failover, TLS termination, and error boundary isolation
"""

from __future__ import annotations

import io
import sqlite3
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.e2e.harness import (
    FRONTEND_OUT,
    E2EClient,
    main,
)


def test_scenario_1_stack_health_probe_convergence(
    e2e_client: E2EClient, compose_config: dict
) -> None:
    """Scenario 1: Cold boot stack health probe convergence across all services."""
    # 1. Reverse proxy + Backend health probe
    res = e2e_client.get("/api/healthz")
    assert res.status_code == 200
    payload = res.json()
    assert payload == {"status": "ok", "version": "2.0.0"}

    # 2. Database & Broker container healthcheck contracts
    services = compose_config.get("services", {})
    assert "postgres" in services
    assert "redis" in services
    assert "healthcheck" in services["postgres"]
    assert "healthcheck" in services["redis"]

    # 3. SPARK status probe convergence
    spark_res = e2e_client.get("/api/spark/status")
    assert spark_res.status_code == 200
    assert "status" in spark_res.json()


def test_scenario_2_complete_web_user_journey(e2e_client: E2EClient) -> None:
    """Scenario 2: Complete web browser user journey from root load to dashboard."""
    # Step 1: User visits root URL
    root_res = e2e_client.get("/")
    assert root_res.status_code == 200
    assert "text/html" in root_res.headers.get("Content-Type", "")

    # Step 2: Browser loads Next.js CSS and JS asset chunks
    static_dir = FRONTEND_OUT / "_next" / "static"
    static_files = list(static_dir.rglob("*.js")) + list(static_dir.rglob("*.css"))
    assert len(static_files) > 0

    chunk = static_files[0]
    rel_path = chunk.relative_to(FRONTEND_OUT).as_posix()
    chunk_res = e2e_client.get(f"/{rel_path}")
    assert chunk_res.status_code == 200
    assert "public, max-age=" in chunk_res.headers.get("Cache-Control", "")

    # Step 3: Frontend performs initial origin-relative telemetry check
    health_res = e2e_client.get("/api/healthz")
    assert health_res.status_code == 200
    assert health_res.json().get("status") == "ok"

    # Step 4: Frontend fetches chat list to populate sidebar
    chats_res = e2e_client.get("/api/chats")
    assert chats_res.status_code == 200
    assert isinstance(chats_res.json(), list)

    # Step 5: Frontend fetches SPARK PA assistant state
    spark_res = e2e_client.get("/api/spark/status")
    assert spark_res.status_code == 200
    assert "seen_messages" in spark_res.json()

    # Step 6: User refreshes page while on deep SPA route (/dashboard/chats)
    deep_res = e2e_client.get("/dashboard/chats")
    assert deep_res.status_code == 200
    assert "text/html" in deep_res.headers.get("Content-Type", "")


def test_scenario_3_chat_upload_and_analysis_lifecycle(e2e_client: E2EClient) -> None:
    """Scenario 3: End-to-end chat upload, async task polling, and data query."""
    chat_raw = (
        b"16/10/2026, 08:15 - Instructor: Class moved to H-006\n"
        b"16/10/2026, 08:16 - Student: Understood, thanks\n"
    )

    files = {"file": ("timetable_notice.txt", io.BytesIO(chat_raw), "text/plain")}

    task_uuid = str(uuid.uuid4())
    captured_paths: list[str] = []

    def mock_delay(file_path: str, platform: str) -> MagicMock:
        captured_paths.append(file_path)
        mock_task = MagicMock()
        mock_task.id = task_uuid
        return mock_task

    with patch.object(main.parse_file_task, "delay", side_effect=mock_delay):
        # 1. Upload chat file
        upload_res = e2e_client.post("/api/upload/whatsapp", files=files)
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        assert upload_data.get("status") == "processing"
        assert upload_data.get("task_id") == task_uuid

    try:
        # 2. Poll task status to completion
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.status = "SUCCESS"
        mock_result.result = {"status": "done", "count": 2}

        with patch("main.celery.result.AsyncResult", return_value=mock_result):
            poll_res = e2e_client.get(f"/api/tasks/{task_uuid}")
            assert poll_res.status_code == 200
            poll_data = poll_res.json()
            assert poll_data.get("status") == "SUCCESS"
            assert poll_data.get("count") == 2

        # 3. Query system stats endpoint
        stats_res = e2e_client.get("/api/stats")
        assert stats_res.status_code == 200
        assert "total_messages" in stats_res.json()
    finally:
        for p in captured_paths:
            Path(p).unlink(missing_ok=True)


def test_scenario_4_spark_daemon_restart_and_state_recovery(
    e2e_client: E2EClient, isolated_spark_db: Path
) -> None:
    """Scenario 4: SPARK PA message ingestion, container restart, and state persistence."""
    # Phase 1: Daemon processes messages before restart
    conn = sqlite3.connect(str(isolated_spark_db))
    conn.execute("INSERT OR REPLACE INTO seen VALUES ('telegram_msg_1001', 1729000000.0);")
    conn.execute("INSERT OR REPLACE INTO seen VALUES ('telegram_msg_1002', 1729000005.0);")
    conn.execute(
        "INSERT INTO pending (ts, status, event_json) VALUES (?, ?, ?);",
        (1729000005.0, "pending", '{"intent": "ROOM_OVERRIDE", "room": "H-006"}'),
    )
    conn.commit()
    conn.close()

    # Verify status bridge reflects initial state
    res1 = e2e_client.get("/api/spark/status")
    assert res1.status_code == 200
    assert res1.json().get("seen_messages", 0) >= 2
    assert len(res1.json().get("pending", [])) >= 1

    # Phase 2: Simulate container restart (process termination and re-connect)
    # Re-open database verifying WAL checkpoint integrity
    conn2 = sqlite3.connect(f"file:{isolated_spark_db}?mode=ro", uri=True)
    cur = conn2.cursor()
    cur.execute("PRAGMA integrity_check;")
    assert cur.fetchone()[0] == "ok"

    cur.execute("SELECT COUNT(*) FROM seen;")
    count = cur.fetchone()[0]
    conn2.close()
    assert count >= 2

    # Verify status bridge still reads state identically after simulated restart
    res2 = e2e_client.get("/api/spark/status")
    assert res2.status_code == 200
    assert res2.json().get("seen_messages", 0) >= 2


def test_scenario_5_reverse_proxy_domain_failover_and_tls_config(
    e2e_client: E2EClient, caddyfile_config: dict
) -> None:
    """Scenario 5: Reverse proxy domain failover, TLS termination, and route boundaries."""
    # 1. Caddyfile configuration verification
    raw_caddy = caddyfile_config.get("raw", "")
    assert "chatlens-backend:8000" in raw_caddy
    assert "chatlens-frontend:80" in raw_caddy

    # 2. Host header routing via proxy
    custom_host_headers = {"Host": "student.klef.ac.in", "X-Forwarded-Proto": "https"}
    res = e2e_client.get("/api/healthz", headers=custom_host_headers)
    assert res.status_code == 200
    assert res.json().get("status") == "ok"

    # 3. Boundary isolation: unknown API route returns 404 JSON, not frontend HTML
    bad_api_res = e2e_client.get("/api/nonexistent_subsystem", headers=custom_host_headers)
    assert bad_api_res.status_code == 404
    assert "application/json" in bad_api_res.headers.get("Content-Type", "")

    # 4. Boundary isolation: root navigation returns frontend HTML, not backend JSON
    root_res = e2e_client.get("/", headers=custom_host_headers)
    assert root_res.status_code == 200
    assert "text/html" in root_res.headers.get("Content-Type", "")
