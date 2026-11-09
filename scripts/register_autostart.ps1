# ChatLens Enterprise SPARK PA Daemon Permanent 24/7 Autostart Manager
# Ensures the daemon runs silently in the background, starts on Windows boot/logon,
# and automatically recovers if terminated.

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Status,
    [switch]$StartNow
)

$RepoRoot = "C:\Users\speed\Documents\antigravity\kind-faraday"
$ScriptPath = Join-Path $RepoRoot "scripts\run_daemon.ps1"
$StartupFolder = [Environment]::GetFolderPath("Startup")
$VbsLauncherPath = Join-Path $StartupFolder "ChatLens-SPARK-Daemon.vbs"
$RegistryKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RegistryValueName = "ChatLens-SPARK-Daemon"

if ($Status) {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  ChatLens SPARK Daemon Autostart Status  " -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    $VbsExists = Test-Path $VbsLauncherPath
    Write-Host "  Startup Folder Link : $VbsExists ($VbsLauncherPath)" -ForegroundColor $(if ($VbsExists) { "Green" } else { "Gray" })

    $RegEntry = (Get-ItemProperty -Path $RegistryKey -Name $RegistryValueName -ErrorAction SilentlyContinue).$RegistryValueName
    $RegExists = [bool]$RegEntry
    Write-Host "  HKCU Run Registry   : $RegExists" -ForegroundColor $(if ($RegExists) { "Green" } else { "Gray" })

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
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`" -LogToFile -Continuous", 0, False
"@
$VbsContent | Out-File -FilePath $VbsLauncherPath -Encoding ascii -Force
Write-Host "[+] Installed silent launcher in Windows Startup folder:" -ForegroundColor Green
Write-Host "    $VbsLauncherPath" -ForegroundColor Gray

# 2. Register in HKCU CurrentVersion\Run as secondary redundancy
$LaunchCmd = "wscript.exe `"$VbsLauncherPath`""
Set-ItemProperty -Path $RegistryKey -Name $RegistryValueName -Value $LaunchCmd -Force
Write-Host "[+] Registered in HKCU CurrentVersion\Run registry key." -ForegroundColor Green

# 3. Start the daemon right now if requested or not already running
Write-Host "[*] Launching SPARK background daemon now..." -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File "$ScriptPath" -Background

Start-Sleep -Seconds 3
& powershell -NoProfile -ExecutionPolicy Bypass -File "$ScriptPath" -Status
