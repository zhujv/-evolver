#Requires -Version 5.1
<#
  Quick check: correct evolver package + optional backend on 16888.
  Run from repo root:
    powershell -ExecutionPolicy Bypass -File .\scripts\verify-env.ps1
#>
$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

$py = Join-Path $RepoRoot '.venv\Scripts\python.exe'
Write-Host "[verify-env] Repo: $RepoRoot"

if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "[verify-env] FAIL: missing $py — run scripts\setup-venv.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "[verify-env] Python (venv): $py"
$out = & $py -c "import evolver; print(evolver.__file__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[verify-env] FAIL: import evolver`n$out" -ForegroundColor Red
    exit 1
}
Write-Host "[verify-env] evolver -> $out"

$body = '{"method":"health","params":{},"id":1}'
try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:16888/rpc' -Method POST -Body $body -ContentType 'application/json' -TimeoutSec 3 -UseBasicParsing
    Write-Host "[verify-env] backend 16888: OK ($($r.StatusCode))"
} catch {
    Write-Host "[verify-env] backend 16888: not reachable (start: python start.py or .\.venv\Scripts\python.exe -m evolver.server)" -ForegroundColor Yellow
}

Write-Host "[verify-env] done."
exit 0
