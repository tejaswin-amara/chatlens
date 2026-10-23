# ChatLens Enterprise PA Daemon Supervisor
# Continuous background runner with health recovery & management

[CmdletBinding()]
param(
    [switch]$Background,
    [switch]$HealthCheck,
    [switch]$Status,
    [switch]$Stop,
    [int]$Backoff = 2,
    [string]$Database = ""
)

# Ensure script executes from repository root
$ScriptDir = Split-Path -Parent $PSCommandPath
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
}
if ($ScriptDir) {
    $RepoRoot = Split-Path -Parent $ScriptDir
    if (Test-Path (Join-Path $RepoRoot "pyproject.toml")) {
        Set-Location $RepoRoot
    }
}

$DbPath = if ($Database) {
    $Database
} elseif ($env:SPARK_DB) {
    $env:SPARK_DB
} else {
    "spark.db"
}

$PidFile = "logs/spark_daemon.pid"

function Get-DaemonProcess {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -like "*python*" -and $_.CommandLine -match "src\.main"
    }
}

function Invoke-SparkPython {
    param([string[]]$PythonArgs)
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv run python @PythonArgs
    } elseif (Test-Path ".\.venv\Scripts\python.exe") {
        & ".\.venv\Scripts\python.exe" @PythonArgs
    } else {
        & python @PythonArgs
    }
}

# --- Action: -Stop ---
if ($Stop) {
    Write-Host "[*] Stopping ChatLens PA Daemon..." -ForegroundColor Cyan
    $StoppedCount = 0

    if (Test-Path $PidFile) {
        $SavedPidStr = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($SavedPidStr -and ($SavedPidStr.Trim() -match '^\d+$')) {
            $SavedPid = [int]$SavedPidStr.Trim()
            $proc = Get-Process -Id $SavedPid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "[+] Terminating supervisor process (PID $SavedPid)..." -ForegroundColor Yellow
                Stop-Process -Id $SavedPid -Force -ErrorAction SilentlyContinue
                $StoppedCount++
            }
        }
        Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
    }

    $PyProcs = Get-DaemonProcess
    if ($PyProcs) {
        foreach ($p in $PyProcs) {
            Write-Host "[+] Terminating python daemon process (PID $($p.ProcessId))..." -ForegroundColor Yellow
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            $StoppedCount++
        }
    }

    if ($StoppedCount -gt 0) {
        Write-Host "[+] ChatLens PA Daemon stopped successfully ($StoppedCount process(es) terminated)." -ForegroundColor Green
    } else {
        Write-Host "[!] No running ChatLens daemon process found." -ForegroundColor Yellow
    }
    exit 0
}

# --- Action: -Status ---
if ($Status) {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "     ChatLens PA Daemon Status            " -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan

    $PyProcs = Get-DaemonProcess
    $SavedPid = if (Test-Path $PidFile) {
        $content = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($content) { $content.Trim() } else { $null }
    } else { $null }

    if ($PyProcs) {
        $ProcIds = ($PyProcs | ForEach-Object { $_.ProcessId }) -join ", "
        Write-Host "  Daemon Process : RUNNING (PID: $ProcIds)" -ForegroundColor Green
    } else {
        Write-Host "  Daemon Process : STOPPED" -ForegroundColor Yellow
    }

    if ($SavedPid) {
        Write-Host "  PID File       : $PidFile (PID: $SavedPid)" -ForegroundColor Gray
    }

    Write-Host "  Database Path  : $DbPath (Exists: $(Test-Path $DbPath))" -ForegroundColor Gray

    $HbInfo = $null
    if (Test-Path $DbPath) {
        $statusPy = @'
import sys, sqlite3, time
try:
    c = sqlite3.connect(sys.argv[1])
    rows = dict(c.execute('SELECT key, value FROM meta').fetchall())
    hb = rows.get('last_heartbeat')
    st = rows.get('last_startup_notify_ts')
    val = hb or st
    label = 'last_heartbeat' if hb else ('last_startup_notify_ts' if st else 'none')
    if val:
        age = time.time() - float(val)
        print(label + ' = ' + str(val) + ' (age: ' + str(round(age, 1)) + 's)')
    else:
        print('none')
except Exception as e:
    print('error: ' + str(e))
'@
        $HbInfo = (Invoke-SparkPython @("-c", $statusPy, $DbPath) | Out-String).Trim()
    }

    if ($HbInfo) {
        Write-Host "  Recent Heartbeat: $HbInfo" -ForegroundColor Gray
    } else {
        Write-Host "  Recent Heartbeat: None recorded" -ForegroundColor Gray
    }
    exit 0
}

# --- Action: -HealthCheck ---
if ($HealthCheck) {
    # 1. Verify python daemon process is running
    $PyProcs = Get-DaemonProcess
    if (-not $PyProcs) {
        Write-Host "[-] Health check failed: ChatLens daemon python process is not running." -ForegroundColor Red
        exit 1
    }

    # 2. Verify SQLite DB exists and PRAGMA integrity_check passes
    if (-not (Test-Path $DbPath)) {
        Write-Host "[-] Health check failed: SQLite database '$DbPath' does not exist." -ForegroundColor Red
        exit 1
    }

    $integrityPy = @'
import sys, sqlite3
try:
    c = sqlite3.connect(sys.argv[1])
    res = c.execute('PRAGMA integrity_check;').fetchone()
    if res and str(res[0]).lower() == 'ok':
        print('ok')
        sys.exit(0)
    else:
        print('corrupt: ' + str(res))
        sys.exit(1)
except Exception as e:
    print('error: ' + str(e))
    sys.exit(1)
'@
    $Integrity = (Invoke-SparkPython @("-c", $integrityPy, $DbPath) | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $Integrity -ne "ok") {
        Write-Host "[-] Health check failed: SQLite integrity check failed ($Integrity)." -ForegroundColor Red
        exit 1
    }

    # 3. Verify meta table last_heartbeat or last_startup_notify_ts freshness (< 1800s)
    $freshnessPy = @'
import sys, sqlite3, time
try:
    c = sqlite3.connect(sys.argv[1])
    rows = dict(c.execute('SELECT key, value FROM meta').fetchall())
    valid_ts = []
    for k in ('last_heartbeat', 'last_startup_notify_ts'):
        v = rows.get(k)
        if v:
            try:
                valid_ts.append((float(v), k))
            except (ValueError, TypeError):
                pass
    if not valid_ts:
        print('MISSING')
        sys.exit(1)
    ts, source = max(valid_ts, key=lambda x: x[0])
    age = time.time() - ts
    if -60 <= age < 1800:
        print('FRESH: age=' + str(round(age, 1)) + 's (' + source + ')')
        sys.exit(0)
    else:
        print('STALE: age=' + str(round(age, 1)) + 's (' + source + ')')
        sys.exit(1)
except Exception as e:
    print('ERROR: ' + str(e))
    sys.exit(1)
'@
    $FreshResult = (Invoke-SparkPython @("-c", $freshnessPy, $DbPath) | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Health check failed: Heartbeat is stale or missing ($FreshResult)." -ForegroundColor Red
        exit 1
    }

    $DaemonPid = ($PyProcs | Select-Object -ExpandProperty ProcessId -First 1)
    Write-Host "[+] Health check passed: Daemon running (PID $DaemonPid), DB intact, $FreshResult." -ForegroundColor Green
    exit 0
}

# --- Action: -Background ---
if ($Background) {
    # Check duplicate
    $Existing = Get-DaemonProcess
    if ($Existing) {
        $ProcId = ($Existing | Select-Object -ExpandProperty ProcessId -First 1)
        Write-Host "[!] ChatLens daemon is already running with PID $ProcId. Exiting duplicate." -ForegroundColor Yellow
        exit 0
    }

    if (-not (Test-Path "logs")) {
        New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    }

    $ScriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Definition }
    $ProcArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
    if ($Database) {
        $ProcArgs += " -Database `"$Database`""
    }
    $Proc = Start-Process powershell -ArgumentList $ProcArgs -WindowStyle Hidden -PassThru
    $Proc.Id | Out-File -FilePath $PidFile -Encoding ascii -Force
    Write-Host "[+] ChatLens daemon started in background with PID $($Proc.Id)." -ForegroundColor Green
    exit 0
}

# --- Default: Foreground Supervisor Runner ---
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ChatLens Enterprise PA Daemon Runner   " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$Existing = Get-DaemonProcess
if ($Existing) {
    $ProcId = ($Existing | Select-Object -ExpandProperty ProcessId -First 1)
    Write-Host "[!] ChatLens daemon is already running with PID $ProcId. Exiting duplicate." -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
}
$PID | Out-File -FilePath $PidFile -Encoding ascii -Force

Write-Host "[+] Starting ChatLens PA background daemon..." -ForegroundColor Green
$CurrentBackoff = $Backoff

try {
    while ($true) {
        try {
            if (Get-Command uv -ErrorAction SilentlyContinue) {
                & uv run python -m src.main
            } else {
                & python -m src.main
            }
            $ExitCode = $LASTEXITCODE

            if ($ExitCode -eq 0) {
                Write-Host "[+] Daemon terminated cleanly (exit code 0)." -ForegroundColor Green
                break
            } elseif ($ExitCode -eq 2) {
                Write-Host "[-] Unrecoverable configuration or auth error (exit code 2). Halting supervisor." -ForegroundColor Red
                break
            } else {
                Write-Host "[!] Daemon crashed with exit code $ExitCode. Restarting in $CurrentBackoff seconds..." -ForegroundColor Yellow
                Start-Sleep -Seconds $CurrentBackoff
                $CurrentBackoff = [Math]::Min($CurrentBackoff * 2, 60)
            }
        } catch {
            Write-Host "[-] Execution exception: $_" -ForegroundColor Red
            Start-Sleep -Seconds $CurrentBackoff
            $CurrentBackoff = [Math]::Min($CurrentBackoff * 2, 60)
        }
    }
} finally {
    if (Test-Path $PidFile) {
        Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
    }
}
