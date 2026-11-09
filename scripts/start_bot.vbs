' ChatLens SPARK Daemon 1-Click Silent Background Launcher
' Double-clicking this script launches the SPARK daemon completely invisibly in the background.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

ScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
RepoRoot = fso.GetParentFolderName(ScriptDir)
DaemonScript = fso.BuildPath(ScriptDir, "run_daemon.ps1")

Command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & DaemonScript & """ -LogToFile -Continuous"
WshShell.Run Command, 0, False
