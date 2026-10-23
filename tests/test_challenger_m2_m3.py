"""Adversarial Challenge & Empirical Stress Test Suite for Milestone 2 Remediation & Milestone 3.

Authored by Challenger 1 (Milestone 2 Remediation & Milestone 3).
Mandatory testing mandates:
1. Empirically stress-test fuzzy command routing:
   - Assert /random, /xyz, /a, /b, /1 do NOT match /undo or /.
   - Assert valid typos (/todat, /tomorow, /attandance, /deadlin, /statuss) 100% match.
   - Assert state-mutating /undo cannot be triggered via fuzzy matching.
2. Empirically stress-test scripts/run_daemon.ps1:
   - -Status when stopped vs running.
   - -HealthCheck with healthy DB, missing DB, and corrupt DB.
   - -Stop when PID file exists vs missing.
"""

from __future__ import annotations

import difflib
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.ingestion.handlers import handle_bot_command

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_daemon.ps1"
PID_FILE = REPO_ROOT / "logs" / "spark_daemon.pid"


# ==============================================================================
# SECTION 1: Empirically Stress-Test Fuzzy Routing
# ==============================================================================


@pytest.mark.asyncio
async def test_fuzzy_routing_rejection_mandate(monkeypatch):
    """MANDATE 1: Assert /random, /xyz, /a, /b, /1 do NOT match /undo or /."""
    monkeypatch.setattr(settings, "owner_chat_id", 12345)

    test_unrecognized_commands = ("/random", "/xyz", "/a", "/b", "/1")

    for test_cmd in test_unrecognized_commands:
        msg = {"chat": {"id": 12345}, "text": test_cmd}
        with (
            patch.object(settings.gemini_api_key, "get_secret_value", return_value=""),
            patch("src.notify.bot.bot.send") as mock_send,
            patch("src.ingestion.handlers.handle_undo_command") as mock_undo,
        ):
            await handle_bot_command(msg)

            # 1. Must NEVER invoke handle_undo_command
            mock_undo.assert_not_called()

            # 2. Must respond with standard unhandled fallback
            mock_send.assert_called_once()
            output = mock_send.call_args[0][0]

            assert (
                f'Received: "{test_cmd}"' in output
            ), f"Failed for {test_cmd}: expected Received fallback"
            assert (
                "ChatLens & SPARK PA Menu" not in output
            ), f"Failed for {test_cmd}: erroneously matched '/'"
            assert (
                "Academic & Schedule Commands:" not in output
            ), f"Failed for {test_cmd}: erroneously matched '/'"
            assert (
                "Nothing to undo" not in output
            ), f"Failed for {test_cmd}: erroneously matched '/undo'"
            assert (
                "Reverted room override" not in output
            ), f"Failed for {test_cmd}: erroneously matched '/undo'"


@pytest.mark.asyncio
async def test_fuzzy_routing_additional_invalid_commands(monkeypatch):
    """Stress-test additional random, numeric, and arbitrary strings."""
    monkeypatch.setattr(settings, "owner_chat_id", 12345)

    invalid_inputs = (
        "/pizza",
        "/foobar",
        "/999",
        "/c",
        "/z",
        "/status_unknown",
        "/unknown_cmd",
        "/randomcommand",
    )

    for test_cmd in invalid_inputs:
        msg = {"chat": {"id": 12345}, "text": test_cmd}
        with (
            patch.object(settings.gemini_api_key, "get_secret_value", return_value=""),
            patch("src.notify.bot.bot.send") as mock_send,
            patch("src.ingestion.handlers.handle_undo_command") as mock_undo,
        ):
            await handle_bot_command(msg)
            mock_undo.assert_not_called()
            mock_send.assert_called_once()
            output = mock_send.call_args[0][0]
            assert f'Received: "{test_cmd}"' in output
            assert "ChatLens & SPARK PA Menu" not in output


@pytest.mark.asyncio
async def test_fuzzy_routing_valid_typos_mandate(monkeypatch):
    """MANDATE 1: Assert valid typos match expected target commands."""
    monkeypatch.setattr(settings, "owner_chat_id", 12345)

    # 1. /todat -> /today
    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots", return_value=[]),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        await handle_bot_command({"chat": {"id": 12345}, "text": "/todat"})
        mock_send.assert_called_once()
        output = mock_send.call_args[0][0]
        assert "No scheduled classes for" in output or "Today" in output or "classes" in output
        assert 'Received: "/todat"' not in output

    # 2. /tomorow -> /tomorrow
    with (
        patch("src.timetable.load") as mock_load,
        patch("src.timetable.get_effective_slots", return_value=[]),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        mock_load.return_value = MagicMock()
        await handle_bot_command({"chat": {"id": 12345}, "text": "/tomorow"})
        mock_send.assert_called_once()
        output = mock_send.call_args[0][0]
        assert "Tomorrow" in output or "No scheduled classes for" in output
        assert 'Received: "/tomorow"' not in output

    # 3. /attandance -> /attendance
    with (
        patch("src.erp.klu_erp.get_attendance", return_value=[]),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_command({"chat": {"id": 12345}, "text": "/attandance"})
        assert mock_send.call_count >= 1
        output = mock_send.call_args[0][0]
        output_lower = output.lower()
        assert (
            "attendance" in output_lower
            or "fetching live attendance" in output_lower
            or "kl erp" in output_lower
        )
        assert 'Received: "/attandance"' not in output

    # 4. /deadlin -> /deadlines (or /deadline)
    with (
        patch("src.academic_calendar.load_calendar", return_value=None),
        patch("src.utils.deduplication.deduplicator.list_pending", return_value=[]),
        patch("src.notify.bot.bot.send") as mock_send,
    ):
        await handle_bot_command({"chat": {"id": 12345}, "text": "/deadlin"})
        mock_send.assert_called_once()
        output = mock_send.call_args[0][0]
        assert "Upcoming Deadlines & Milestones" in output
        assert 'Received: "/deadlin"' not in output

    # 5. /statuss -> /status
    with patch("src.notify.bot.bot.send") as mock_send:
        await handle_bot_command({"chat": {"id": 12345}, "text": "/statuss"})
        mock_send.assert_called_once()
        output = mock_send.call_args[0][0]
        assert "ChatLens PA Status" in output
        assert 'Received: "/statuss"' not in output


@pytest.mark.asyncio
async def test_fuzzy_routing_undo_and_slash_safety(monkeypatch):
    """Stress-test safety: /undo must NOT be reachable via typos, only exact command."""
    monkeypatch.setattr(settings, "owner_chat_id", 12345)

    # Exact /undo must invoke handle_undo_command
    with (
        patch("src.ingestion.handlers.handle_undo_command") as mock_undo,
        patch("src.notify.bot.bot.send"),
    ):
        await handle_bot_command({"chat": {"id": 12345}, "text": "/undo"})
        mock_undo.assert_called_once()

    # Incomplete or typo variations of /undo must NOT invoke handle_undo_command
    for near_undo in ("/und", "/un", "/undoo", "/undoo1"):
        msg = {"chat": {"id": 12345}, "text": near_undo}
        with (
            patch.object(settings.gemini_api_key, "get_secret_value", return_value=""),
            patch("src.notify.bot.bot.send") as mock_send,
            patch("src.ingestion.handlers.handle_undo_command") as mock_undo,
        ):
            await handle_bot_command(msg)
            mock_undo.assert_not_called()
            mock_send.assert_called_once()
            assert f'Received: "{near_undo}"' in mock_send.call_args[0][0]


def test_difflib_similarity_ratios_mathematical_oracle():
    """Verify exact difflib similarity ratios against the cutoff=0.75 boundary."""
    fuzzy_candidates = (
        "/start",
        "/help",
        "/today",
        "/tomorrow",
        "/attendance",
        "/deadlines",
        "/deadline",
        "/tasks",
        "/status",
        "/marks",
        "/cgpa",
        "/fee",
        "/rescan",
        "/scan",
    )

    # Non-matching cases: highest match ratio must be strictly < 0.75
    rejected = ["/random", "/xyz", "/a", "/b", "/1", "/pizza"]
    for word in rejected:
        matches = difflib.get_close_matches(word, fuzzy_candidates, n=1, cutoff=0.75)
        assert matches == [], f"{word} should have no matches at cutoff 0.75, got {matches}"

    # Valid typos: must have matches >= 0.75
    accepted_mapping = {
        "/todat": "/today",
        "/tomorow": "/tomorrow",
        "/attandance": "/attendance",
        "/statuss": "/status",
    }
    for typo, target in accepted_mapping.items():
        matches = difflib.get_close_matches(typo, fuzzy_candidates, n=1, cutoff=0.75)
        assert len(matches) == 1, f"{typo} failed to match {target}"
        assert matches[0] == target, f"{typo} matched {matches[0]} instead of {target}"


# ==============================================================================
# SECTION 2: Empirically Stress-Test scripts/run_daemon.ps1
# ==============================================================================

# Skip PowerShell execution tests on non-Windows platforms
pytestmark_win32 = pytest.mark.skipif(
    sys.platform != "win32",
    reason="PowerShell supervisor tests require Windows environment",
)


def run_ps_script(args: list[str], timeout: float = 20.0) -> subprocess.CompletedProcess[str]:
    """Execute run_daemon.ps1 via powershell.exe with specified arguments."""
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT_PATH),
    ] + args
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture(autouse=True)
def clean_daemon_environment():
    """Ensure clean daemon process state before and after supervisor tests."""
    if sys.platform == "win32":
        run_ps_script(["-Stop"])
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)
    yield
    if sys.platform == "win32":
        run_ps_script(["-Stop"])
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)


@pytestmark_win32
def test_supervisor_status_when_stopped():
    """MANDATE 2: Test -Status when stopped."""
    res = run_ps_script(["-Status"])
    assert res.returncode == 0
    assert "ChatLens PA Daemon Status" in res.stdout
    assert "Daemon Process : STOPPED" in res.stdout
    assert "Database Path" in res.stdout


@pytestmark_win32
def test_supervisor_status_when_running():
    """MANDATE 2: Test -Status when running."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(1.0)
        res = run_ps_script(["-Status"])
        assert res.returncode == 0
        assert "Daemon Process : RUNNING" in res.stdout
        assert str(proc.pid) in res.stdout
    finally:
        proc.kill()
        proc.wait()


@pytestmark_win32
def test_supervisor_healthcheck_healthy_db(tmp_path):
    """MANDATE 2: Test -HealthCheck with healthy DB."""
    healthy_db = tmp_path / "healthy.db"
    conn = sqlite3.connect(healthy_db)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('last_heartbeat', ?)", (str(time.time() - 15),))
    conn.commit()
    conn.close()

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(1.0)
        res = run_ps_script(["-HealthCheck", "-Database", str(healthy_db)])
        assert res.returncode == 0
        assert "Health check passed" in res.stdout
        assert "FRESH" in res.stdout
    finally:
        proc.kill()
        proc.wait()


@pytestmark_win32
def test_supervisor_healthcheck_missing_db(tmp_path):
    """MANDATE 2: Test -HealthCheck with missing DB."""
    missing_db = tmp_path / "nonexistent.db"

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(1.0)
        res = run_ps_script(["-HealthCheck", "-Database", str(missing_db)])
        assert res.returncode == 1
        assert "does not exist" in res.stdout
    finally:
        proc.kill()
        proc.wait()


@pytestmark_win32
def test_supervisor_healthcheck_corrupt_db(tmp_path):
    """MANDATE 2: Test -HealthCheck with corrupt DB."""
    corrupt_db = tmp_path / "corrupt.db"
    corrupt_db.write_bytes(b"garbage not a valid sqlite 3 header at all")

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(1.0)
        res = run_ps_script(["-HealthCheck", "-Database", str(corrupt_db)])
        assert res.returncode == 1
        assert "integrity check failed" in res.stdout.lower() or "error" in res.stdout.lower()
    finally:
        proc.kill()
        proc.wait()


@pytestmark_win32
def test_supervisor_stop_when_pid_file_exists(tmp_path):
    """MANDATE 2: Test -Stop when PID file exists."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(1.0)
        PID_FILE.write_text(str(proc.pid), encoding="ascii")

        res = run_ps_script(["-Stop"])
        assert res.returncode == 0
        assert "stopped successfully" in res.stdout or "Terminating" in res.stdout

        # Verify PID file was removed
        assert not PID_FILE.exists(), "PID file was not deleted by -Stop"

        # Verify process is terminated
        for _ in range(20):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        assert proc.poll() is not None, "Process was not killed by -Stop"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)


@pytestmark_win32
def test_supervisor_stop_when_pid_file_missing():
    """MANDATE 2: Test -Stop when PID file is missing."""
    if PID_FILE.exists():
        PID_FILE.unlink(missing_ok=True)

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(1.0)
        assert not PID_FILE.exists()

        res = run_ps_script(["-Stop"])
        assert res.returncode == 0
        assert (
            "stopped successfully" in res.stdout
            or "Terminating python daemon process" in res.stdout
        )

        for _ in range(20):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        assert proc.poll() is not None, "Process was not terminated when PID file was missing"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
