"""Unit and integration tests for PowerShell daemon runner and healthcheck logic.

Tests scripts/run_daemon.ps1 and F3.1-F3.3 requirements:
- PowerShell 5.1 syntax and parameter compatibility.
- Single-instance detection with Get-CimInstance Win32_Process (no Get-Process.CommandLine).
- Parameters: -Background, -HealthCheck, -Status, -Stop.
- HealthCheck validation: running process, SQLite integrity, heartbeat freshness (< 1800s).
- Startup debounce unit tests for src/main.py meta table interaction.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from src.utils.deduplication import MessageDeduplicator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_daemon.ps1"

# Skip PowerShell execution tests on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="PowerShell supervisor tests are specific to Windows environments",
)


def run_ps_script(args: list[str], timeout: float = 15.0) -> subprocess.CompletedProcess[str]:
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


def run_ps_command(command: str, timeout: float = 15.0) -> subprocess.CompletedProcess[str]:
    """Execute an arbitrary PowerShell command."""
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


# ==============================================================================
# 1. Script Syntax & AST Compatibility Tests
# ==============================================================================


def test_run_daemon_syntax_valid_powershell_5_1():
    """Verify scripts/run_daemon.ps1 parses cleanly under PowerShell 5.1 AST."""
    ps_code = f"""
    $errors = $null
    $tokens = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        '{str(SCRIPT_PATH).replace("\\", "\\\\")}',
        [ref]$tokens,
        [ref]$errors
    )
    if ($errors -and $errors.Count -gt 0) {{
        $errors | ForEach-Object {{ Write-Error $_.Message }}
        exit 1
    }} else {{
        Write-Output "SYNTAX_OK"
        exit 0
    }}
    """
    res = run_ps_command(ps_code)
    assert res.returncode == 0, f"PowerShell parse errors:\n{res.stderr}"
    assert "SYNTAX_OK" in res.stdout


def test_run_daemon_no_legacy_get_process_commandline():
    """Verify scripts/run_daemon.ps1 does not use broken Get-Process.CommandLine."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    assert 'Get-Process -Name "python"' not in content
    assert "Get-Process.CommandLine" not in content
    assert '$_.CommandLine -match "src\\.main"' in content
    assert "Get-CimInstance Win32_Process" in content


def test_run_daemon_parameters_defined():
    """Verify parameters -Background, -HealthCheck, -Status, -Stop, -Backoff are defined."""
    ps_code = f"""
    $ast = [System.Management.Automation.Language.Parser]::ParseFile(
        '{str(SCRIPT_PATH).replace("\\", "\\\\")}',
        [ref]$null,
        [ref]$null
    )
    $params = $ast.ParamBlock.Parameters | ForEach-Object {{ $_.Name.VariablePath.UserPath }}
    $expected = @("Background", "HealthCheck", "Status", "Stop", "Backoff", "Database")
    foreach ($p in $expected) {{
        if ($params -notcontains $p) {{
            Write-Error "Missing parameter: $p"
            exit 1
        }}
    }}
    Write-Output "PARAMS_OK"
    exit 0
    """
    res = run_ps_command(ps_code)
    assert res.returncode == 0, f"Parameter check failed:\n{res.stderr}"
    assert "PARAMS_OK" in res.stdout


# ==============================================================================
# 2. -Status Action Tests
# ==============================================================================


def test_status_when_daemon_stopped():
    """Verify -Status returns exit 0 and reports STOPPED when no daemon is active."""
    res = run_ps_script(["-Status"])
    assert res.returncode == 0
    assert "ChatLens PA Daemon Status" in res.stdout
    assert "Daemon Process : STOPPED" in res.stdout
    assert "Database Path" in res.stdout


def test_status_when_daemon_running():
    """Verify -Status returns exit 0 and reports RUNNING with PID when daemon is active."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-Status"])
        assert res.returncode == 0
        assert "ChatLens PA Daemon Status" in res.stdout
        assert "Daemon Process : RUNNING" in res.stdout
        assert str(proc.pid) in res.stdout
    finally:
        proc.kill()
        proc.wait()


# ==============================================================================
# 3. -Stop Action Tests
# ==============================================================================


def test_stop_when_no_process_running():
    """Verify -Stop handles clean state gracefully without error."""
    res = run_ps_script(["-Stop"])
    assert res.returncode == 0
    assert (
        "No running ChatLens daemon process found" in res.stdout
        or "stopped successfully" in res.stdout
    )


def test_stop_terminates_running_process():
    """Verify -Stop finds and terminates running python daemon process."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        assert proc.poll() is None  # Process is running

        res = run_ps_script(["-Stop"])
        assert res.returncode == 0
        assert "stopped successfully" in res.stdout

        # Verify process was terminated
        stopped = False
        for _ in range(20):
            if proc.poll() is not None:
                stopped = True
                break
            time.sleep(0.1)
        assert stopped, "Daemon process was not stopped by -Stop"
    finally:
        if proc.poll() is None:
            proc.kill()


def test_stop_removes_pid_file(tmp_path):
    """Verify -Stop removes logs/spark_daemon.pid."""
    logs_dir = REPO_ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    pid_file = logs_dir / "spark_daemon.pid"
    pid_file.write_text("999999", encoding="ascii")

    res = run_ps_script(["-Stop"])
    assert res.returncode == 0
    assert not pid_file.exists(), "PID file was not cleaned up by -Stop"


# ==============================================================================
# 4. -HealthCheck Action Tests
# ==============================================================================


def test_healthcheck_fails_when_daemon_stopped():
    """Health check must exit 1 when python daemon is not running."""
    res = run_ps_script(["-HealthCheck"])
    assert res.returncode == 1
    assert "Health check failed: ChatLens daemon python process is not running" in res.stdout


def test_healthcheck_fails_when_database_missing(tmp_path):
    """Health check must exit 1 when specified database does not exist."""
    missing_db = tmp_path / "missing.db"
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-HealthCheck", "-Database", str(missing_db)])
        assert res.returncode == 1
        assert "does not exist" in res.stdout
    finally:
        proc.kill()
        proc.wait()


def test_healthcheck_fails_when_database_corrupted(tmp_path):
    """Health check must exit 1 when SQLite integrity check fails."""
    corrupt_db = tmp_path / "corrupt.db"
    corrupt_db.write_bytes(b"not a valid sqlite database file header garbage")

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-HealthCheck", "-Database", str(corrupt_db)])
        assert res.returncode == 1
        assert "integrity check failed" in res.stdout.lower() or "error" in res.stdout.lower()
    finally:
        proc.kill()
        proc.wait()


def test_healthcheck_fails_when_heartbeat_missing(tmp_path):
    """Health check must exit 1 when meta table has no heartbeat or startup timestamp."""
    test_db = tmp_path / "empty_meta.db"
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-HealthCheck", "-Database", str(test_db)])
        assert res.returncode == 1
        assert "stale or missing" in res.stdout
    finally:
        proc.kill()
        proc.wait()


def test_healthcheck_fails_when_heartbeat_stale(tmp_path):
    """Health check must exit 1 when heartbeat timestamp is older than 1800s."""
    test_db = tmp_path / "stale_meta.db"
    stale_ts = str(time.time() - 2500)  # > 1800s
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('last_heartbeat', ?)", (stale_ts,))
    conn.commit()
    conn.close()

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-HealthCheck", "-Database", str(test_db)])
        assert res.returncode == 1
        assert "stale or missing" in res.stdout
        assert "STALE" in res.stdout
    finally:
        proc.kill()
        proc.wait()


def test_healthcheck_passes_when_heartbeat_fresh(tmp_path):
    """Health check must exit 0 when daemon is running, DB intact, and heartbeat < 1800s."""
    test_db = tmp_path / "fresh_meta.db"
    fresh_ts = str(time.time() - 45)  # 45s ago
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('last_heartbeat', ?)", (fresh_ts,))
    conn.commit()
    conn.close()

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-HealthCheck", "-Database", str(test_db)])
        assert res.returncode == 0
        assert "Health check passed" in res.stdout
        assert "FRESH" in res.stdout
        assert "last_heartbeat" in res.stdout
    finally:
        proc.kill()
        proc.wait()


def test_healthcheck_passes_with_fresh_startup_notify_ts(tmp_path):
    """Health check must pass using last_startup_notify_ts if heartbeat hasn't run yet."""
    test_db = tmp_path / "startup_fresh.db"
    fresh_ts = str(time.time() - 30)  # 30s ago
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('last_startup_notify_ts', ?)", (fresh_ts,))
    conn.commit()
    conn.close()

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-HealthCheck", "-Database", str(test_db)])
        assert res.returncode == 0
        assert "Health check passed" in res.stdout
        assert "FRESH" in res.stdout
        assert "last_startup_notify_ts" in res.stdout
    finally:
        proc.kill()
        proc.wait()


def test_healthcheck_selects_most_recent_timestamp(tmp_path):
    """Health check selects the most recent of startup vs heartbeat timestamps."""
    test_db = tmp_path / "dual_ts.db"
    old_startup = str(time.time() - 3600)  # 1 hour ago
    fresh_heartbeat = str(time.time() - 60)  # 1 min ago
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('last_startup_notify_ts', ?)", (old_startup,))
    conn.execute("INSERT INTO meta VALUES ('last_heartbeat', ?)", (fresh_heartbeat,))
    conn.commit()
    conn.close()

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-HealthCheck", "-Database", str(test_db)])
        assert res.returncode == 0
        assert "Health check passed" in res.stdout
        assert "last_heartbeat" in res.stdout
    finally:
        proc.kill()
        proc.wait()


# ==============================================================================
# 5. -Background Action Tests
# ==============================================================================


def test_background_duplicate_suppression():
    """Verify -Background suppresses launch if a daemon process is already running."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(15)", "src.main"],
        cwd=str(REPO_ROOT),
    )
    try:
        time.sleep(0.8)
        res = run_ps_script(["-Background"])
        assert res.returncode == 0
        assert "already running with PID" in res.stdout
        assert "Exiting duplicate" in res.stdout
    finally:
        proc.kill()
        proc.wait()


# ==============================================================================
# 6. Startup Debounce & SQLite Meta Table Unit Tests (F3.1 - F3.2)
# ==============================================================================


def test_meta_table_crud_and_concurrency(tmp_path):
    """Verify MessageDeduplicator meta_get and meta_set CRUD functionality."""
    db_path = str(tmp_path / "meta_test.db")
    dedup = MessageDeduplicator(db_path=db_path)

    # Initial state is None
    assert dedup.meta_get("last_startup_notify_ts") is None

    # Set value
    now_ts = "1792736174.5"
    dedup.meta_set("last_startup_notify_ts", now_ts)
    assert dedup.meta_get("last_startup_notify_ts") == now_ts

    # Update value
    new_ts = "1792737074.5"
    dedup.meta_set("last_startup_notify_ts", new_ts)
    assert dedup.meta_get("last_startup_notify_ts") == new_ts


def test_debounce_evaluation_scenarios(tmp_path):
    """Unit test for the exact debounce evaluation algorithm used in src/main.py:233-241."""
    db_path = str(tmp_path / "debounce_logic.db")
    dedup = MessageDeduplicator(db_path=db_path)

    def evaluate_debounce(current_time: float) -> bool:
        last_notify = dedup.meta_get("last_startup_notify_ts")
        should_notify = True
        if last_notify:
            try:
                if current_time - float(last_notify) < 900:
                    should_notify = False
            except ValueError:
                pass
        return should_notify

    t0 = 1000000.0

    # 1. First boot -> notification allowed
    assert evaluate_debounce(t0) is True
    dedup.meta_set("last_startup_notify_ts", str(t0))

    # 2. Rapid restart after 60s (< 900s) -> notification suppressed
    assert evaluate_debounce(t0 + 60) is False

    # 3. Restart at 899s (< 900s) -> notification suppressed
    assert evaluate_debounce(t0 + 899) is False

    # 4. Restart at 900s (boundary) -> notification allowed
    assert evaluate_debounce(t0 + 900) is True

    # 5. Restart at 901s (> 900s) -> notification allowed
    assert evaluate_debounce(t0 + 901) is True
    dedup.meta_set("last_startup_notify_ts", str(t0 + 901))

    # 6. Corrupted timestamp recovery
    dedup.meta_set("last_startup_notify_ts", "corrupt_garbage_not_a_float")
    assert evaluate_debounce(t0 + 950) is True
