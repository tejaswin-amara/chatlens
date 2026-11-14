# ChatLens Enterprise PA Daemon Supervisor
# Continuous background runner with health recovery & management

[CmdletBinding()]
param(
    [switch]$Background,
    [switch]$HealthCheck,
    [switch]$Status,
    [switch]$Stop,
    [int]$Backoff = 2,
    [string]$Database = "",
    [switch]$LogToFile,
    [switch]$Continuous,
    [int]$GraceTimeout = 8
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
if (-not $RepoRoot) {
    $RepoRoot = (Get-Location).Path
}

$DbPath = if ($Database) {
    $Database
} elseif ($env:SPARK_DB) {
    $env:SPARK_DB
} else {
    "spark.db"
}

$PidFile = "logs/spark_daemon.pid"
$StopFile = "logs/spark_daemon.stop"

function Clean-StalePidFile {
    if (Test-Path $PidFile) {
        $SavedPidStr = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($SavedPidStr -and ($SavedPidStr.Trim() -match '^\d+$')) {
            $SavedPid = [int]$SavedPidStr.Trim()
            $proc = Get-Process -Id $SavedPid -ErrorAction SilentlyContinue
            if (-not $proc) {
                Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
            }
        } else {
            Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
        }
    }
}

function Get-DaemonProcess {
    Get-CimInstance Win32_Process -Filter "Name like '%python%'" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -match "src\.main" -and $_.ProcessId -ne $PID
    } | Where-Object {
        Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
    }
}

function Get-SupervisorProcess {
    Get-CimInstance Win32_Process -Filter "Name like '%powershell%' or Name like '%pwsh%'" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -match "run_daemon\.ps1" -and $_.CommandLine -match "-Continuous" -and $_.ProcessId -ne $PID
    } | Where-Object {
        Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
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

    if (-not (Test-Path "logs")) {
        New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    }

    # 1. Collect target processes (supervisor + daemon)
    $TargetPids = @()
    if (Test-Path $PidFile) {
        $SavedPidStr = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($SavedPidStr -and ($SavedPidStr.Trim() -match '^\d+$')) {
            $SavedPid = [int]$SavedPidStr.Trim()
            $proc = Get-Process -Id $SavedPid -ErrorAction SilentlyContinue
            if ($proc) {
                $TargetPids += $SavedPid
            }
        }
    }

    $PyProcs = Get-DaemonProcess
    if ($PyProcs) {
        foreach ($p in $PyProcs) {
            if ($TargetPids -notcontains $p.ProcessId) {
                $TargetPids += $p.ProcessId
            }
        }
    }

    $Supervisors = Get-SupervisorProcess
    if ($Supervisors) {
        foreach ($s in $Supervisors) {
            if ($TargetPids -notcontains $s.ProcessId) {
                $TargetPids += $s.ProcessId
            }
        }
    }

    if ($TargetPids.Count -eq 0) {
        if (Test-Path $PidFile) { Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue }
        if (Test-Path $StopFile) { Remove-Item -Path $StopFile -Force -ErrorAction SilentlyContinue }
        Write-Host "[!] No running ChatLens daemon process found." -ForegroundColor Yellow
        exit 0
    }

    # 2. Signal graceful shutdown via stop file
    New-Item -ItemType File -Path $StopFile -Force -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[*] Signaled graceful shutdown via $StopFile (waiting up to ${GraceTimeout}s)..." -ForegroundColor Cyan

    $GraceDeadline = (Get-Date).AddSeconds($GraceTimeout)
    $AllGracefullyStopped = $false

    while ((Get-Date) -lt $GraceDeadline) {
        $RemainingPids = @()
        foreach ($tPid in $TargetPids) {
            if (Get-Process -Id $tPid -ErrorAction SilentlyContinue) {
                $RemainingPids += $tPid
            }
        }
        if ($RemainingPids.Count -eq 0) {
            $AllGracefullyStopped = $true
            break
        }
        Start-Sleep -Milliseconds 100
    }

    # 3. Force-terminate any remaining processes if graceful timeout expired
    if (-not $AllGracefullyStopped) {
        Write-Host "[!] Graceful shutdown timeout expired; terminating remaining processes..." -ForegroundColor Yellow
        foreach ($tPid in $TargetPids) {
            $proc = Get-Process -Id $tPid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "[+] Terminating process (PID $tPid)..." -ForegroundColor Yellow
                Stop-Process -Id $tPid -Force -ErrorAction SilentlyContinue
                $StoppedCount++
            }
        }
    } else {
        $StoppedCount = $TargetPids.Count
    }

    # 4. Clean up state artifacts
    if (Test-Path $PidFile) {
        Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $StopFile) {
        Remove-Item -Path $StopFile -Force -ErrorAction SilentlyContinue
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

    Clean-StalePidFile
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

    # 3. Verify meta table last_heartbeat or last_startup_notify_ts freshness (< 180s)
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
    if -60 <= age < 180:
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
    Clean-StalePidFile
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

    $RawScriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Definition }
    $ScriptPath = (Resolve-Path $RawScriptPath).Path
    $ProcArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -LogToFile -Continuous"
    if ($Database) {
        $ProcArgs += " -Database `"$Database`""
    }
    $Proc = Start-Process powershell -ArgumentList $ProcArgs -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru
    $Proc.Id | Out-File -FilePath $PidFile -Encoding ascii -Force
    Write-Host "[+] ChatLens daemon started in background with PID $($Proc.Id)." -ForegroundColor Green
    exit 0
}

# --- Default: Foreground Supervisor Runner ---
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ChatLens Enterprise PA Daemon Runner   " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Clean-StalePidFile
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

if (Test-Path $StopFile) {
    Remove-Item -Path $StopFile -Force -ErrorAction SilentlyContinue
}

try {
    while ($true) {
        if (Test-Path $StopFile) {
            Remove-Item -Path $StopFile -Force -ErrorAction SilentlyContinue
            Write-Host "[+] Graceful stop file detected ($StopFile). Halting supervisor." -ForegroundColor Green
            break
        }
        try {
            if ($LogToFile) {
                if (Get-Command uv -ErrorAction SilentlyContinue) {
                    & uv run python -m src.main *>> logs/spark.log
                } else {
                    & python -m src.main *>> logs/spark.log
                }
            } else {
                if (Get-Command uv -ErrorAction SilentlyContinue) {
                    & uv run python -m src.main
                } else {
                    & python -m src.main
                }
            }
            $ExitCode = $LASTEXITCODE

            if (Test-Path $StopFile) {
                Remove-Item -Path $StopFile -Force -ErrorAction SilentlyContinue
                Write-Host "[+] Graceful stop file detected ($StopFile). Halting supervisor." -ForegroundColor Green
                break
            }

            if ($ExitCode -eq 0) {
                if ($Continuous) {
                    Write-Host "[+] Daemon cycle completed (exit code 0). Continuous mode restarting in $Backoff seconds..." -ForegroundColor Green
                    Start-Sleep -Seconds $Backoff
                } else {
                    Write-Host "[+] Daemon terminated cleanly (exit code 0)." -ForegroundColor Green
                    break
                }
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
    if (Test-Path $StopFile) {
        Remove-Item -Path $StopFile -Force -ErrorAction SilentlyContinue
    }
}
