# ChatLens Enterprise SPARK PA Daemon Permanent 24/7 Autostart & Watchdog Manager
# Ensures the daemon runs silently in the background, starts on Windows boot/logon,
# and automatically recovers via scheduled watchdog if terminated or crashed.

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Status,
    [switch]$StartNow
)

$ScriptDir = Split-Path -Parent $PSCommandPath
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
}
$RepoRoot = if ($ScriptDir) { Split-Path -Parent $ScriptDir } else { "C:\Users\speed\Documents\antigravity\kind-faraday" }
$ScriptPath = Join-Path $RepoRoot "scripts\run_daemon.ps1"
$WatchdogPath = Join-Path $RepoRoot "scripts\watchdog.ps1"
$StartupFolder = [Environment]::GetFolderPath("Startup")
$VbsLauncherPath = Join-Path $StartupFolder "ChatLens-SPARK-Daemon.vbs"
$RegistryKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RegistryValueName = "ChatLens-SPARK-Daemon"
$TaskName = "ChatLens-SPARK-Watchdog"

if ($Status) {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  ChatLens SPARK Daemon Autostart Status  " -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    $VbsExists = Test-Path $VbsLauncherPath
    Write-Host "  Startup Folder Link : $VbsExists ($VbsLauncherPath)" -ForegroundColor $(if ($VbsExists) { "Green" } else { "Gray" })

    $RegEntry = (Get-ItemProperty -Path $RegistryKey -Name $RegistryValueName -ErrorAction SilentlyContinue).$RegistryValueName
    $RegExists = [bool]$RegEntry
    Write-Host "  HKCU Run Registry   : $RegExists" -ForegroundColor $(if ($RegExists) { "Green" } else { "Gray" })

    $TaskObj = Get-ScheduledTask -TaskName "$TaskName" -ErrorAction SilentlyContinue
    $TaskActive = [bool]($TaskObj -and $TaskObj.State -ne "Disabled")
    Write-Host "  Windows Watchdog    : $TaskActive (Every 2 min self-heal, State: $($TaskObj.State))" -ForegroundColor $(if ($TaskActive) { "Green" } else { "Red" })

    & powershell -NoProfile -ExecutionPolicy Bypass -File "$ScriptPath" -Status
    exit 0
}

if ($Uninstall) {
    Write-Host "[*] Removing ChatLens SPARK Daemon autostart..." -ForegroundColor Cyan
    if (Test-Path $VbsLauncherPath) {
        Remove-Item $VbsLauncherPath -Force -ErrorAction SilentlyContinue
        Write-Host "[+] Removed Startup folder shortcut." -ForegroundColor Green
    }
    Remove-ItemProperty -Path $RegistryKey -Name $RegistryValueName -ErrorAction SilentlyContinue
    Write-Host "[+] Removed HKCU Run registry entry." -ForegroundColor Green

    schtasks.exe /delete /tn "$TaskName" /f 2>&1 | Out-Null
    Write-Host "[+] Removed Windows Scheduled Watchdog Task." -ForegroundColor Green

    # Also stop running daemon
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$ScriptPath" -Stop
    Write-Host "[+] Daemon autostart uninstalled successfully." -ForegroundColor Green
    exit 0
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Configuring ChatLens SPARK Daemon 24/7 Autostart & Watchdog" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Create completely silent VBScript background launcher in Startup folder
$VbsContent = @"
' ChatLens SPARK Daemon 24/7 Autostart Launcher
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""$ScriptPath"" -LogToFile -Continuous", 0, False
"@
$VbsContent | Out-File -FilePath $VbsLauncherPath -Encoding ascii -Force
Write-Host "[+] Installed silent launcher in Windows Startup folder:" -ForegroundColor Green
Write-Host "    $VbsLauncherPath" -ForegroundColor Gray

# 2. Register in HKCU CurrentVersion\Run as secondary redundancy
$LaunchCmd = "wscript.exe `"$VbsLauncherPath`""
Set-ItemProperty -Path $RegistryKey -Name $RegistryValueName -Value $LaunchCmd -Force
Write-Host "[+] Registered in HKCU CurrentVersion\Run registry key." -ForegroundColor Green

# 3. Register persistent Windows Scheduled Task Watchdog (Every 2 minutes, runs on battery & AC)
$TaskRegistered = $false
try {
    $Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatchdogPath`" -Quiet"
    $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2)
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName "$TaskName" -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
    $TaskRegistered = $true
} catch {
    $TaskCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $WatchdogPath -Quiet"
    schtasks.exe /create /tn "$TaskName" /tr "$TaskCmd" /sc MINUTE /mo 2 /f 2>&1 | Out-Null
    $TaskRegistered = ($LASTEXITCODE -eq 0)
}
if ($TaskRegistered) {
    Write-Host "[+] Registered Windows Scheduled Task Watchdog ($TaskName, every 2 min, battery-safe)." -ForegroundColor Green
} else {
    Write-Host "[!] Note: Could not register Windows Task Scheduler entry." -ForegroundColor Yellow
}

# 4. Start the daemon right now if requested or not already running
Write-Host "[*] Launching SPARK background daemon now..." -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File "$ScriptPath" -Background

Start-Sleep -Seconds 3
& powershell -NoProfile -ExecutionPolicy Bypass -File "$ScriptPath" -Status
