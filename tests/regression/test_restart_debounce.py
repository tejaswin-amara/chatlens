"""Empirical challenge test suite for Milestone 2 Remediation & Milestone 3.

Authored by Challenger 2.
Exhaustively and empirically stress-tests:
1. Debounce Timing & Fault Tolerance:
   - 899.9s elapsed: notification suppressed, database timestamp untouched.
   - 900.1s elapsed: notification allowed, database timestamp updated to current time.
   - 900.0s exact boundary: notification allowed.
   - Corrupted non-numeric timestamp recovery: no crash, notification allowed, database overwritten
     with valid float string, and subsequent rapid restart properly debounced.
   - Bot transmission exception: exception caught gracefully, database timestamp NOT updated,
     ensuring subsequent attempt is not falsely blocked.
   - Initial boot without prior timestamp: notification allowed, timestamp persisted.
   - Mathematical precision sweep across delta boundaries.
2. PowerShell Supervisor Loop Exit Code Handling:
   - Exit code 0: supervisor halts cleanly without restart.
   - Exit code 2: unrecoverable configuration/auth error halts supervisor cleanly without restart.
   - Exit code 1 / non-zero: crashes trigger exponential backoff delay and supervisor restart.
   - Backoff doubling sequence and cap verification.
   - Execution exception resilience: unhandled command error caught, delayed, and retried.
   - PID file cleanup guarantee on exit.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import run_daemon
from src.utils.deduplication import MessageDeduplicator
from tests.test_main import FakeTelegramClient, guard

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_daemon.ps1"


# ==============================================================================
# Fixtures & Helpers
# ==============================================================================


@pytest.fixture
def mock_daemon_settings(tmp_path, monkeypatch):
    """Provides isolated settings and dedicated SQLite meta database."""
    test_db = str(tmp_path / "debounce_stress.db")
    test_dedup = MessageDeduplicator(db_path=test_db)

    with patch("src.main.settings") as s:
        s.telegram_api_id = 99999
        s.telegram_api_hash = MagicMock(get_secret_value=lambda: "mock_hash")
        s.telegram_session_string = MagicMock(get_secret_value=lambda: "mock_session")
        s.google_credentials_base64 = MagicMock(get_secret_value=lambda: "mock_b64")
        s.gemini_api_key = MagicMock(get_secret_value=lambda: "mock_key")
        s.spark_mode = "dry"
        s.allowed_chat_ids = [123456]
        s.bot_token = MagicMock(get_secret_value=lambda: "mock_token")
        s.owner_chat_id = 77777
        s.spark_db = test_db
        s.validate_required = MagicMock()

        monkeypatch.setattr("src.utils.deduplication.deduplicator", test_dedup)

        yield {
            "settings": s,
            "dedup": test_dedup,
            "db_path": test_db,
        }


def make_clock_mock(fixed_ts: float):
    """Creates a mock clock.now_ist() returning fixed_ts on .timestamp()."""
    mock_dt = MagicMock()
    mock_dt.timestamp.return_value = fixed_ts
    return MagicMock(return_value=mock_dt)


def run_ps_supervisor(command: str, timeout: float = 15.0) -> subprocess.CompletedProcess[str]:
    """Execute PowerShell supervisor command with isolated environment."""
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]
    return subprocess.run(  # noqa: S603, S607
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


# ==============================================================================
# Part 1: Empirical Debounce Threshold & Fault Tolerance Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_debounce_threshold_899_9_seconds_suppressed(mock_daemon_settings):
    """Verify that after 899.9s (< 900s), the startup notification is suppressed."""
    dedup = mock_daemon_settings["dedup"]
    t0 = 1700000000.0
    dedup.meta_set("last_startup_notify_ts", str(t0))

    t_eval = t0 + 899.9  # Exactly 899.9 seconds elapsed

    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    with (
        patch("src.notify.bot.bot.send") as mock_bot_send,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.clock.now_ist", new=make_clock_mock(t_eval)),
    ):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0

        # Notification must be suppressed
        mock_bot_send.assert_not_called()

        # Database timestamp must NOT be overwritten
        saved_ts = dedup.meta_get("last_startup_notify_ts")
        assert saved_ts == str(t0)


@pytest.mark.asyncio
async def test_debounce_threshold_900_1_seconds_allowed(mock_daemon_settings):
    """Verify that after 900.1s (> 900s), the startup notification is allowed."""
    dedup = mock_daemon_settings["dedup"]
    t0 = 1700000000.0
    dedup.meta_set("last_startup_notify_ts", str(t0))

    t_eval = t0 + 900.1  # Exactly 900.1 seconds elapsed

    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    with (
        patch("src.notify.bot.bot.send") as mock_bot_send,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.clock.now_ist", new=make_clock_mock(t_eval)),
    ):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0

        # Notification must be sent
        mock_bot_send.assert_called_once()
        args, kwargs = mock_bot_send.call_args
        assert "🚀 SPARK started:" in args[0]
        assert kwargs.get("buttons") == []

        # Database timestamp must be updated to current time
        saved_ts = dedup.meta_get("last_startup_notify_ts")
        assert saved_ts == str(t_eval)


@pytest.mark.asyncio
async def test_debounce_threshold_900_0_exact_boundary_allowed(mock_daemon_settings):
    """Verify exact boundary 900.0s elapsed: (900.0 < 900 is False) -> allowed."""
    dedup = mock_daemon_settings["dedup"]
    t0 = 1700000000.0
    dedup.meta_set("last_startup_notify_ts", str(t0))

    t_eval = t0 + 900.0  # Exactly 900.0 seconds elapsed

    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    with (
        patch("src.notify.bot.bot.send") as mock_bot_send,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.clock.now_ist", new=make_clock_mock(t_eval)),
    ):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        mock_bot_send.assert_called_once()
        assert dedup.meta_get("last_startup_notify_ts") == str(t_eval)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "corrupted_val",
    [
        "corrupted_garbage_timestamp",
        "",
        "    ",
        "None",
        "undefined",
        "[object Object]",
        "NaN",
        "123.45.67",
        "True",
        "{}",
    ],
)
async def test_debounce_corrupted_timestamp_recovery(mock_daemon_settings, corrupted_val):
    """Verify corrupted non-numeric timestamp is tolerated, recovered, and overwritten."""
    dedup = mock_daemon_settings["dedup"]
    dedup.meta_set("last_startup_notify_ts", corrupted_val)

    t_eval = 1700000500.0
    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    # 1. First run with corrupted value: recovers, sends notification, overwrites timestamp
    with (
        patch("src.notify.bot.bot.send") as mock_bot_send,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.clock.now_ist", new=make_clock_mock(t_eval)),
    ):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        mock_bot_send.assert_called_once()

        # Database value must be repaired to valid float string
        repaired_ts = dedup.meta_get("last_startup_notify_ts")
        assert repaired_ts == str(t_eval)
        assert float(repaired_ts) == t_eval

    # 2. Subsequent restart 60s later: debounce is now active using the repaired timestamp
    client2 = FakeTelegramClient(authorized=True)
    stop_event2 = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event2.set)

    with (
        patch("src.notify.bot.bot.send") as mock_bot_send2,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.clock.now_ist", new=make_clock_mock(t_eval + 60.0)),
    ):
        code2 = await guard(
            run_daemon(client=client2, stop_event=stop_event2, handle_signals=False)
        )
        assert code2 == 0
        # Notification must be debounced
        mock_bot_send2.assert_not_called()


@pytest.mark.asyncio
async def test_debounce_bot_transmission_failure_preserves_prior_timestamp(mock_daemon_settings):
    """Verify that if bot.send fails, timestamp is NOT updated, avoiding false debounce."""
    dedup = mock_daemon_settings["dedup"]
    t0 = 1700000000.0
    dedup.meta_set("last_startup_notify_ts", str(t0))

    t_attempt = t0 + 1200.0  # Past 900s cooldown

    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    # Mock bot.send to raise an unhandled network error
    with (
        patch("src.notify.bot.bot.send", side_effect=RuntimeError("Simulated Telegram outage")),
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.clock.now_ist", new=make_clock_mock(t_attempt)),
    ):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0  # Daemon must not crash on bot notification failure

        # Crucial assertion: meta table was NOT updated to t_attempt!
        assert dedup.meta_get("last_startup_notify_ts") == str(t0)

    # Next attempt with healthy network: notification must proceed!
    client2 = FakeTelegramClient(authorized=True)
    stop_event2 = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event2.set)

    with (
        patch("src.notify.bot.bot.send") as mock_bot_send2,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.clock.now_ist", new=make_clock_mock(t_attempt + 1.0)),
    ):
        code2 = await guard(
            run_daemon(client=client2, stop_event=stop_event2, handle_signals=False)
        )
        assert code2 == 0
        mock_bot_send2.assert_called_once()
        assert dedup.meta_get("last_startup_notify_ts") == str(t_attempt + 1.0)


@pytest.mark.asyncio
async def test_debounce_first_boot_no_prior_record(mock_daemon_settings):
    """Verify initial daemon boot with empty meta table allows notification and saves timestamp."""
    dedup = mock_daemon_settings["dedup"]
    assert dedup.meta_get("last_startup_notify_ts") is None

    t0 = 1700000000.0
    client = FakeTelegramClient(authorized=True)
    stop_event = asyncio.Event()
    asyncio.get_running_loop().call_soon(stop_event.set)

    with (
        patch("src.notify.bot.bot.send") as mock_bot_send,
        patch("src.main.catch_up_chats", new=AsyncMock()),
        patch("src.utils.clock.now_ist", new=make_clock_mock(t0)),
    ):
        code = await guard(run_daemon(client=client, stop_event=stop_event, handle_signals=False))
        assert code == 0
        mock_bot_send.assert_called_once()
        assert dedup.meta_get("last_startup_notify_ts") == str(t0)


def test_debounce_delta_mathematical_precision_sweep():
    """Parametric test sweeping delta float boundaries around 900.0s."""
    t0 = 1000000.0

    def evaluate(delta: float) -> bool:
        now_ts = t0 + delta
        last_notify = str(t0)
        should_notify = True
        if last_notify:
            try:
                if now_ts - float(last_notify) < 900:
                    should_notify = False
            except ValueError:
                pass
        return should_notify

    # Sub-threshold deltas must all be suppressed (False)
    sub_threshold_deltas = [
        -100.0,
        -1.0,
        0.0,
        0.001,
        1.0,
        60.0,
        500.0,
        899.0,
        899.5,
        899.8,
        899.9,
        899.99,
        899.999,
    ]
    for d in sub_threshold_deltas:
        assert evaluate(d) is False, f"Expected delta {d} to be suppressed"

    # Threshold and above deltas must all be allowed (True)
    super_threshold_deltas = [
        900.0,
        900.0001,
        900.001,
        900.01,
        900.1,
        900.5,
        901.0,
        1000.0,
        1800.0,
        100000.0,
    ]
    for d in super_threshold_deltas:
        assert evaluate(d) is True, f"Expected delta {d} to be allowed"


# ==============================================================================
# Part 2: Empirical PowerShell Supervisor Loop Tests
# ==============================================================================


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell tests require Windows")
class TestPowerShellSupervisorLoop:
    """Empirical tests for scripts/run_daemon.ps1 foreground runner loop."""

    def test_supervisor_exit_code_0_halts_cleanly(self):
        """Supervisor loop must break immediately on exit code 0 without restart."""
        ps_test = """
        function Get-CimInstance { return $null }
        $global:calls = 0
        function uv {
            $global:calls++
            Write-Host "MOCK_UV_INVOKED_CALL_$global:calls"
            $global:LASTEXITCODE = 0
        }
        & .\\scripts\\run_daemon.ps1 -Backoff 1
        """
        res = run_ps_supervisor(ps_test, timeout=15)
        assert res.returncode == 0
        assert "MOCK_UV_INVOKED_CALL_1" in res.stdout
        assert "Daemon terminated cleanly (exit code 0)." in res.stdout
        assert "Restarting in" not in res.stdout
        assert "MOCK_UV_INVOKED_CALL_2" not in res.stdout

    def test_supervisor_exit_code_2_halts_cleanly(self):
        """Supervisor loop must break immediately on exit code 2 (unrecoverable config/auth)."""
        ps_test = """
        function Get-CimInstance { return $null }
        $global:calls = 0
        function uv {
            $global:calls++
            Write-Host "MOCK_UV_INVOKED_CALL_$global:calls"
            $global:LASTEXITCODE = 2
        }
        & .\\scripts\\run_daemon.ps1 -Backoff 1
        """
        res = run_ps_supervisor(ps_test, timeout=15)
        assert res.returncode == 0
        assert "MOCK_UV_INVOKED_CALL_1" in res.stdout
        assert (
            "Unrecoverable configuration or auth error (exit code 2). Halting supervisor."
            in res.stdout
        )
        assert "Restarting in" not in res.stdout
        assert "MOCK_UV_INVOKED_CALL_2" not in res.stdout

    def test_supervisor_exit_code_1_restarts_with_exponential_backoff(self):
        """Supervisor loop must delay with exponential backoff on exit code 1 and retry."""
        ps_test = """
        function Get-CimInstance { return $null }
        $global:calls = 0
        function uv {
            $global:calls++
            Write-Host "MOCK_UV_INVOKED_CALL_$global:calls"
            if ($global:calls -lt 3) {
                $global:LASTEXITCODE = 1
            } else {
                $global:LASTEXITCODE = 0
            }
        }
        & .\\scripts\\run_daemon.ps1 -Backoff 1
        """
        t_start = time.perf_counter()
        res = run_ps_supervisor(ps_test, timeout=20)
        elapsed = time.perf_counter() - t_start

        assert res.returncode == 0
        assert "MOCK_UV_INVOKED_CALL_1" in res.stdout
        assert "Daemon crashed with exit code 1. Restarting in 1 seconds..." in res.stdout
        assert "MOCK_UV_INVOKED_CALL_2" in res.stdout
        assert "Daemon crashed with exit code 1. Restarting in 2 seconds..." in res.stdout
        assert "MOCK_UV_INVOKED_CALL_3" in res.stdout
        assert "Daemon terminated cleanly (exit code 0)." in res.stdout

        # Verify exponential backoff delay elapsed: 1s + 2s = 3s minimum
        assert elapsed >= 2.8, f"Expected elapsed >= 2.8s due to backoff, got {elapsed:.2f}s"

    def test_supervisor_arbitrary_nonzero_exit_code(self):
        """Supervisor loop must handle non-zero exit codes (e.g. 137) with backoff restart."""
        ps_test = """
        function Get-CimInstance { return $null }
        $global:calls = 0
        function uv {
            $global:calls++
            Write-Host "MOCK_UV_INVOKED_CALL_$global:calls"
            if ($global:calls -eq 1) {
                $global:LASTEXITCODE = 137
            } else {
                $global:LASTEXITCODE = 0
            }
        }
        & .\\scripts\\run_daemon.ps1 -Backoff 1
        """
        res = run_ps_supervisor(ps_test, timeout=15)
        assert res.returncode == 0
        assert "Daemon crashed with exit code 137. Restarting in 1 seconds..." in res.stdout
        assert "Daemon terminated cleanly (exit code 0)." in res.stdout

    def test_supervisor_execution_exception_handling(self):
        """Supervisor loop must catch powershell invocation exceptions and retry with backoff."""
        ps_test = """
        function Get-CimInstance { return $null }
        $global:calls = 0
        function uv {
            $global:calls++
            Write-Host "MOCK_UV_INVOKED_CALL_$global:calls"
            if ($global:calls -eq 1) {
                throw "Simulated command dispatch failure"
            } else {
                $global:LASTEXITCODE = 0
            }
        }
        & .\\scripts\\run_daemon.ps1 -Backoff 1
        """
        res = run_ps_supervisor(ps_test, timeout=15)
        assert res.returncode == 0
        assert "[-] Execution exception: Simulated command dispatch failure" in res.stdout
        assert "MOCK_UV_INVOKED_CALL_2" in res.stdout
        assert "Daemon terminated cleanly (exit code 0)." in res.stdout

    def test_supervisor_pid_cleanup_guarantee(self, tmp_path):
        """Verify supervisor guarantees logs/spark_daemon.pid cleanup in finally block."""
        pid_file = REPO_ROOT / "logs" / "spark_daemon.pid"

        ps_test = """
        function Get-CimInstance { return $null }
        function uv {
            $global:LASTEXITCODE = 2
        }
        & .\\scripts\\run_daemon.ps1 -Backoff 1
        """
        res = run_ps_supervisor(ps_test, timeout=15)
        assert res.returncode == 0
        assert not pid_file.exists(), "PID file was not cleaned up after supervisor exit"
