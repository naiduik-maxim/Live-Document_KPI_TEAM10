$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
$testArgs = @("$PSScriptRoot/run_testcontainers.py")
& "$repo/.venv/Scripts/python.exe" @testArgs
exit $LASTEXITCODE
