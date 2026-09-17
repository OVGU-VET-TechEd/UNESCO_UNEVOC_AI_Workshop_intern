# Usage: .\scripts\harness.ps1 run | extract | validate | review | check | agents
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
if (-not $Rest) { $Rest = @("--help") }
& $Py -m harness @Rest
exit $LASTEXITCODE
