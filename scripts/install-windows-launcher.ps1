[CmdletBinding()]
param(
    [switch]$DesktopShortcut
)

$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "scripts/install-windows-launcher.ps1 must be run on Windows."
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourceDir = Join-Path $root "dist\windows\PTO Planner"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\PTO Planner"
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shortcutPath = Join-Path $startMenuDir "PTO Planner.lnk"
$desktopShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "PTO Planner.lnk"
$targetPath = Join-Path $installDir "PTO Planner.exe"

if (-not (Test-Path $sourceDir)) {
    throw "Build output not found at $sourceDir. Run scripts/build-windows.ps1 first."
}

if (Test-Path $installDir) {
    Remove-Item $installDir -Recurse -Force
}

New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item -Path (Join-Path $sourceDir "*") -Destination $installDir -Recurse -Force

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$targetPath,0"
$shortcut.Description = "Launch PTO Planner"
$shortcut.Save()

if ($DesktopShortcut) {
    $desktopShortcut = $shell.CreateShortcut($desktopShortcutPath)
    $desktopShortcut.TargetPath = $targetPath
    $desktopShortcut.WorkingDirectory = $installDir
    $desktopShortcut.IconLocation = "$targetPath,0"
    $desktopShortcut.Description = "Launch PTO Planner"
    $desktopShortcut.Save()
}
