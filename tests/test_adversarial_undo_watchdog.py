"""Adversarial stress harness for Milestone M3: /undo Idempotency & Watchdog Lifecycle.

Empirically challenges:
1. /undo idempotency:
   - Repeated /undo invocations when no writes exist (10 consecutive calls).
   - Double-undo on identical write (marks undone=1, second call reports nothing to undo).
   - External 404 / resource deleted for Google Calendar event, Google Task, and Calendar Patch.
   - Non-404 API exception handling (500/503 errors must preserve undone=0 for retry).
   - Multi-write LIFO stack undo sequence across mixed Calendar & Tasks targets.
2. Watchdog supervision & health checks:
   - run_daemon.ps1 -HealthCheck with daemon stopped -> exit code 1.
   - run_daemon.ps1 -HealthCheck with missing DB -> exit code 1.
   - run_daemon.ps1 -HealthCheck with corrupted DB -> exit code 1.
   - run_daemon.ps1 -HealthCheck with empty meta / missing heartbeat -> exit code 1.
   - run_daemon.ps1 -HealthCheck with stale heartbeat (> 1800s) -> exit code 1.
   - scripts/watchdog.ps1 autonomous resurrection when daemon is stopped.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.handlers import handle_undo_command
from src.utils.deduplication import MessageDeduplicator

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_DAEMON_SCRIPT = REPO_ROOT / "scripts" / "run_daemon.ps1"
WATCHDOG_SCRIPT = REPO_ROOT / "scripts" / "watchdog.ps1"


# ==============================================================================
# SECTION 1: Adversarial /undo Idempotency & Resiliency
# ==============================================================================


@pytest.mark.asyncio
async def test_adversarial_undo_repeated_empty_invocations(tmp_path):
    """Stress-test: 10 consecutive /undo calls on empty writes table.

    Must reliably return '⚠️ Nothing to undo.' every time without crashing.
    """
    db_file = str(tmp_path / "empty_undo_stress.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        for _ in range(10):
            mock_send.reset_mock()
            await handle_undo_command({})
            mock_send.assert_called_once_with("⚠️ Nothing to undo.")


@pytest.mark.asyncio
async def test_adversarial_undo_double_reversion_prevention(tmp_path):
    """Stress-test: Double-undo on identical write.

    First undo must revert and mark undone=1.
    Second undo must NOT re-revert, and must report nothing left to undo.
    """
    db_file = str(tmp_path / "double_undo.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        dedup.record_write("insert", "ev_cal_unique", json.dumps({"source": "calendar"}))
        last = dedup.last_write()
        assert last is not None
        w_id = last[0]

        cal_auth_path = "src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service"
        with (
            patch(cal_auth_path) as mock_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_service = MagicMock()
            mock_auth.return_value = mock_service

            # Call 1
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created calendar event.")
            mock_service.events().delete.assert_called_once_with(
                calendarId="primary", eventId="ev_cal_unique"
            )

            # Verify undone=1
            with dedup._get_conn() as conn:
                row = conn.execute("SELECT undone FROM writes WHERE id = ?", (w_id,)).fetchone()
                assert row[0] == 1

            # Reset mocks and call 2 immediately
            mock_send.reset_mock()
            mock_service.reset_mock()
            await handle_undo_command({})
            mock_send.assert_called_once_with("⚠️ Nothing to undo.")
            mock_service.events().delete.assert_not_called()

            # Ensure row remains undone=1
            with dedup._get_conn() as conn:
                row = conn.execute("SELECT undone FROM writes WHERE id = ?", (w_id,)).fetchone()
                assert row[0] == 1


@pytest.mark.asyncio
async def test_adversarial_undo_external_404_resilience_calendar(tmp_path):
    """Simulate Google Calendar event already deleted externally (404 HttpError).

    Must catch 404, notify owner of deletion, and crucially mark undone=1.
    """
    db_file = str(tmp_path / "undo_404_cal.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        dedup.record_write("insert", "ev_deleted_404", json.dumps({"source": "calendar"}))
        last = dedup.last_write()
        assert last is not None
        w_id = last[0]

        cal_auth_path = "src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service"
        with (
            patch(cal_auth_path) as mock_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_service = MagicMock()
            mock_service.events().delete.side_effect = Exception("HttpError 404: Not found")
            mock_auth.return_value = mock_service

            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created calendar event.")

            with dedup._get_conn() as conn:
                row = conn.execute("SELECT undone FROM writes WHERE id = ?", (w_id,)).fetchone()
                assert row[0] == 1


@pytest.mark.asyncio
async def test_adversarial_undo_external_404_resilience_task(tmp_path):
    """Simulate Google Task already deleted externally (404 / deleted).

    Must catch 404, notify owner, and mark undone=1.
    """
    db_file = str(tmp_path / "undo_404_task.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        dedup.record_write("insert", "task_deleted_404", json.dumps({"source": "tasks"}))
        last = dedup.last_write()
        assert last is not None
        w_id = last[0]

        tasks_auth_path = "src.workspace.tasks_sync.tasks_sync.auth.get_tasks_service"
        with (
            patch(tasks_auth_path) as mock_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_service = MagicMock()
            mock_service.tasks().delete.side_effect = Exception("HttpError 404: deleted")
            mock_auth.return_value = mock_service

            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created task.")

            with dedup._get_conn() as conn:
                row = conn.execute("SELECT undone FROM writes WHERE id = ?", (w_id,)).fetchone()
                assert row[0] == 1


@pytest.mark.asyncio
async def test_adversarial_undo_external_404_resilience_patch(tmp_path):
    """Simulate Calendar Patch where target event was deleted externally (404).

    Must catch 404, notify owner of patch reversal, and mark undone=1.
    """
    db_file = str(tmp_path / "undo_404_patch.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    prior_state = {
        "location": "Old Room",
        "reminders": {"useDefault": True},
        "extendedProperties": {"private": {"spark_override": None}},
        "summary": "Original Course",
    }

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        dedup.record_write("patch", "ev_patched_404", json.dumps(prior_state))
        last = dedup.last_write()
        assert last is not None
        w_id = last[0]

        cal_auth_path = "src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service"
        with (
            patch(cal_auth_path) as mock_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_service = MagicMock()
            mock_service.events().patch.side_effect = Exception("HttpError 404: Not Found")
            mock_auth.return_value = mock_service

            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Undid patch on event `ev_patched_404`.")

            with dedup._get_conn() as conn:
                row = conn.execute("SELECT undone FROM writes WHERE id = ?", (w_id,)).fetchone()
                assert row[0] == 1


@pytest.mark.asyncio
async def test_adversarial_undo_non_404_error_preserves_retryable_state(tmp_path):
    """If API fails with a transient 500 error or network error, /undo must NOT mark undone=1.

    It must report failure and leave undone=0 so the owner can retry /undo.
    """
    db_file = str(tmp_path / "undo_500.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        dedup.record_write("insert", "ev_retryable", json.dumps({"source": "calendar"}))
        last = dedup.last_write()
        assert last is not None
        w_id = last[0]

        cal_auth_path = "src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service"
        with (
            patch(cal_auth_path) as mock_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_service = MagicMock()
            mock_service.events().delete.side_effect = Exception(
                "503 Service Unavailable: Backend timeout"
            )
            mock_auth.return_value = mock_service

            await handle_undo_command({})
            mock_send.assert_called_once_with(
                "❌ Undo failed: 503 Service Unavailable: Backend timeout"
            )

            # CRITICAL: must remain undone=0
            with dedup._get_conn() as conn:
                row = conn.execute("SELECT undone FROM writes WHERE id = ?", (w_id,)).fetchone()
                assert row[0] == 0


@pytest.mark.asyncio
async def test_adversarial_undo_mixed_multi_write_lifo_stack(tmp_path):
    """Stress-test: 5 mixed writes inserted sequentially.

    Consecutive /undo calls must reverse in strict LIFO order:
    W5 -> W4 -> W3 -> W2 -> W1 -> Nothing.
    """
    db_file = str(tmp_path / "lifo_stress.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    writes_spec = [
        ("insert", "ev_1", {"source": "calendar"}),
        ("insert", "task_2", {"source": "tasks"}),
        (
            "patch",
            "ev_3",
            {"location": "R-101", "extendedProperties": {"private": {"spark_override": None}}},
        ),
        ("insert", "task_4", {"source": "tasks"}),
        ("insert", "ev_5", {"source": "calendar"}),
    ]

    with (
        patch("src.utils.deduplication.deduplicator", dedup),
        patch("src.ingestion.handlers.deduplicator", dedup),
    ):
        for kind, eid, prior in writes_spec:
            dedup.record_write(kind, eid, json.dumps(prior))
            await asyncio.sleep(0.01)

        cal_auth_path = "src.workspace.calendar_sync.calendar_sync.auth.get_calendar_service"
        tasks_auth_path = "src.workspace.tasks_sync.tasks_sync.auth.get_tasks_service"

        with (
            patch(cal_auth_path) as mock_cal_auth,
            patch(tasks_auth_path) as mock_tasks_auth,
            patch("src.notify.bot.bot.send") as mock_send,
        ):
            mock_cs = MagicMock()
            mock_ts = MagicMock()
            mock_cal_auth.return_value = mock_cs
            mock_tasks_auth.return_value = mock_ts

            # Undo 1 -> reverts ev_5 (calendar)
            mock_send.reset_mock()
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created calendar event.")
            mock_cs.events().delete.assert_called_once_with(calendarId="primary", eventId="ev_5")

            # Undo 2 -> reverts task_4 (tasks)
            mock_send.reset_mock()
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created task.")
            mock_ts.tasks().delete.assert_called_once_with(tasklist="@default", task="task_4")

            # Undo 3 -> reverts ev_3 (patch)
            mock_send.reset_mock()
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Undid patch on event `ev_3`.")
            mock_cs.events().patch.assert_called_once()

            # Undo 4 -> reverts task_2 (tasks)
            mock_send.reset_mock()
            mock_ts.reset_mock()
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created task.")
            mock_ts.tasks().delete.assert_called_once_with(tasklist="@default", task="task_2")

            # Undo 5 -> reverts ev_1 (calendar)
            mock_send.reset_mock()
            mock_cs.reset_mock()
            await handle_undo_command({})
            mock_send.assert_called_once_with("✅ Deleted created calendar event.")
            mock_cs.events().delete.assert_called_once_with(calendarId="primary", eventId="ev_1")

            # Undo 6 -> empty
            mock_send.reset_mock()
            await handle_undo_command({})
            mock_send.assert_called_once_with("⚠️ Nothing to undo.")


# ==============================================================================
# SECTION 2: Adversarial Watchdog Supervision & HealthCheck
# ==============================================================================


def wait_for_daemon_running(proc: subprocess.Popen, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Child process exited prematurely with code {proc.returncode}")
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_DAEMON_SCRIPT),
            "-Status",
        ]
        res = subprocess.run(  # noqa: S603
            cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10
        )
        if (
            res.returncode == 0
            and "Daemon Process : RUNNING" in res.stdout
            and str(proc.pid) in res.stdout
        ):
            return
        time.sleep(0.1)
    raise TimeoutError(f"Process {proc.pid} did not become visible within {timeout}s.")


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell tests require Windows")
def test_adversarial_healthcheck_rejection_when_daemon_stopped():
    """HealthCheck must cleanly reject with code 1 when daemon process is not running."""
    stop_cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(RUN_DAEMON_SCRIPT),
        "-Stop",
    ]
    subprocess.run(stop_cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15)  # noqa: S603
    time.sleep(0.5)

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(RUN_DAEMON_SCRIPT),
        "-HealthCheck",
    ]
    res = subprocess.run(  # noqa: S603
        cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15
    )
    assert res.returncode == 1
    assert "Health check failed: ChatLens daemon python process is not running" in res.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell tests require Windows")
def test_adversarial_healthcheck_rejection_missing_db(tmp_path):
    """HealthCheck must cleanly reject with code 1 when SQLite DB is missing."""
    missing_db = tmp_path / "does_not_exist.db"
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(25)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        wait_for_daemon_running(proc)
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_DAEMON_SCRIPT),
            "-HealthCheck",
            "-Database",
            str(missing_db),
        ]
        res = subprocess.run(  # noqa: S603
            cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15
        )
        assert res.returncode == 1
        assert "does not exist" in res.stdout
    finally:
        proc.kill()
        proc.wait()


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell tests require Windows")
def test_adversarial_healthcheck_rejection_corrupt_db(tmp_path):
    """HealthCheck must cleanly reject with code 1 when SQLite DB has corrupt header."""
    corrupt_db = tmp_path / "corrupt_header.db"
    corrupt_db.write_bytes(b"INVALID_HEADER_NOT_A_SQLITE_DATABASE_GARBAGE_DATA_12345")

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(25)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        wait_for_daemon_running(proc)
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_DAEMON_SCRIPT),
            "-HealthCheck",
            "-Database",
            str(corrupt_db),
        ]
        res = subprocess.run(  # noqa: S603
            cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15
        )
        assert res.returncode == 1
        assert "integrity check failed" in res.stdout.lower() or "error" in res.stdout.lower()
    finally:
        proc.kill()
        proc.wait()


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell tests require Windows")
def test_adversarial_healthcheck_rejection_stale_heartbeat(tmp_path):
    """HealthCheck must cleanly reject with code 1 when heartbeat is > 1800s old."""
    stale_db = tmp_path / "stale_hb.db"
    stale_ts = str(time.time() - 3600)  # 1 hour ago
    conn = sqlite3.connect(stale_db)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('last_heartbeat', ?)", (stale_ts,))
    conn.commit()
    conn.close()

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(25)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        wait_for_daemon_running(proc)
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_DAEMON_SCRIPT),
            "-HealthCheck",
            "-Database",
            str(stale_db),
        ]
        res = subprocess.run(  # noqa: S603
            cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15
        )
        assert res.returncode == 1
        assert "stale or missing" in res.stdout
        assert "STALE" in res.stdout
    finally:
        proc.kill()
        proc.wait()


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell tests require Windows")
def test_adversarial_healthcheck_rejection_missing_heartbeat_in_meta(tmp_path):
    """HealthCheck must cleanly reject with code 1 when meta has no heartbeat keys."""
    empty_db = tmp_path / "empty_meta.db"
    conn = sqlite3.connect(empty_db)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('some_unrelated_key', '123')")
    conn.commit()
    conn.close()

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(25)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        wait_for_daemon_running(proc)
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_DAEMON_SCRIPT),
            "-HealthCheck",
            "-Database",
            str(empty_db),
        ]
        res = subprocess.run(  # noqa: S603
            cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15
        )
        assert res.returncode == 1
        assert "stale or missing" in res.stdout
        assert "MISSING" in res.stdout
    finally:
        proc.kill()
        proc.wait()


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell tests require Windows")
def test_adversarial_watchdog_resurrection_cycle():
    """Empirically challenge scripts/watchdog.ps1:

    1. Verify daemon is stopped initially.
    2. Execute watchdog.ps1 -> detects unhealthy/stopped daemon (code 1).
    3. Watchdog executes resurrection sequence via run_daemon.ps1 -Background.
    4. Watchdog logs resurrection and completes with code 0.
    5. Clean up by stopping resurrected daemon.
    """
    # 1. Ensure daemon stopped
    stop_cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(RUN_DAEMON_SCRIPT),
        "-Stop",
    ]
    subprocess.run(  # noqa: S603
        stop_cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15
    )

    # 2. Run watchdog.ps1
    watchdog_cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(WATCHDOG_SCRIPT),
    ]
    res = subprocess.run(  # noqa: S603
        watchdog_cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0
    assert "Daemon unhealthy or stopped (code 1). Resurrecting daemon..." in res.stdout
    assert "Daemon resurrected successfully." in res.stdout

    # 3. Clean up by stopping daemon
    cleanup_res = subprocess.run(  # noqa: S603
        stop_cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15
    )
    assert cleanup_res.returncode == 0
