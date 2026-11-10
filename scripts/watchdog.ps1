# ChatLens SPARK 24/7 Autonomous Watchdog & Health Guardian
# Periodically executed by Windows Task Scheduler (every 2 minutes)
# Inspects daemon process, database integrity, and heartbeat freshness.
# Automatically resurrects the daemon if terminated, crashed, or missing.

[CmdletBinding()]
param(
    [switch]$ForceRestart,
    [switch]$Quiet
)

$ScriptDir = Split-Path -Parent $PSCommandPath
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
}
$RepoRoot = if ($ScriptDir) { Split-Path -Parent $ScriptDir } else { (Get-Location).Path }
Set-Location $RepoRoot

$DaemonScript = Join-Path $RepoRoot "scripts\run_daemon.ps1"
$LogFile = Join-Path $RepoRoot "logs\watchdog.log"
$Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
}

# 1. Run official HealthCheck
$HealthOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File "$DaemonScript" -HealthCheck 2>&1
$HealthExit = $LASTEXITCODE

if ($HealthExit -eq 0 -and (-not $ForceRestart)) {
    if (-not $Quiet) {
        Write-Host "[$Timestamp] [WATCHDOG] OK: $HealthOutput" -ForegroundColor Green
    }
    exit 0
}

# 2. HealthCheck failed or ForceRestart requested - Resurrect daemon!
$LogMsg = "[$Timestamp] [WATCHDOG] Daemon unhealthy or stopped (code $HealthExit). Resurrecting daemon..."
Write-Host $LogMsg -ForegroundColor Yellow
$LogMsg | Out-File -FilePath $LogFile -Append -Encoding utf8

# Ensure stale PID file or dead processes are cleaned
& powershell -NoProfile -ExecutionPolicy Bypass -File "$DaemonScript" -Stop 2>&1 | Out-Null
Start-Sleep -Seconds 1

# Relaunch in background with continuous supervisor
& powershell -NoProfile -ExecutionPolicy Bypass -File "$DaemonScript" -Background

Start-Sleep -Seconds 3
$VerifyOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File "$DaemonScript" -Status
"[$Timestamp] [WATCHDOG] Resurrected: $VerifyOutput" | Out-File -FilePath $LogFile -Append -Encoding utf8
Write-Host "[$Timestamp] [WATCHDOG] Daemon resurrected successfully." -ForegroundColor Green
exit 0
