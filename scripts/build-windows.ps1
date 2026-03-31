[CmdletBinding()]
param(
    [string]$PythonExecutable = ""
)

$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "scripts/build-windows.ps1 must be run on Windows."
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $PythonExecutable) {
    $venvPython = Join-Path $root ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $PythonExecutable = $venvPython
    }
    else {
        $PythonExecutable = "python.exe"
    }
}

$checkCommand = @("-c", "import PyInstaller")
& $PythonExecutable @checkCommand | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed for $PythonExecutable. Run: $PythonExecutable -m pip install -r $root\requirements-packaging.txt"
}

$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--distpath", (Join-Path $root "dist\windows"),
    "--workpath", (Join-Path $root "build\windows"),
    (Join-Path $root "pto_planner.spec")
)

& $PythonExecutable @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
