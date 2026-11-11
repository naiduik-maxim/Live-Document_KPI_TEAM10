param([ValidateSet("", "1", "2", "3", "4")][string]$Module = "")
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
$testArgs = @("$PSScriptRoot/run_testcontainers.py")
if ($Module) { $testArgs += @("--module", $Module) }
& "$repo/.venv/Scripts/python.exe" @testArgs
exit $LASTEXITCODE
