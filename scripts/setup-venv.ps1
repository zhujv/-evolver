#Requires -Version 5.1
<#
  Recreate .venv at the repository root (Windows).
  Use when: "Fatal error in launcher", paths show "???", or project was moved
  from a non-ASCII path — old venv shims still point at the old location.

  Run from repo root:
    powershell -ExecutionPolicy Bypass -File .\scripts\setup-venv.ps1
#>
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

$venvDir = Join-Path $RepoRoot '.venv'
if (Test-Path $venvDir) {
    Write-Host "[setup-venv] Removing existing .venv ..."
    Remove-Item -LiteralPath $venvDir -Recurse -Force
}

Write-Host "[setup-venv] Creating .venv ..."
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m venv .venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv .venv
} else {
    Write-Error "No 'py' or 'python' on PATH. Install Python 3 from https://www.python.org/downloads/"
    exit 1
}

$pyexe = Join-Path $venvDir 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pyexe)) {
    Write-Error "venv missing: $pyexe"
    exit 1
}

Write-Host "[setup-venv] Installing dependencies (python -m pip, not pip.exe) ..."
& $pyexe -m pip install --upgrade pip
& $pyexe -m pip install -r (Join-Path $RepoRoot 'requirements.txt')

Write-Host ""
Write-Host "[setup-venv] OK. Next:"
Write-Host "  cd frontend; npm install; cd .."
Write-Host "  .\.venv\Scripts\python.exe start.py"
Write-Host ""
