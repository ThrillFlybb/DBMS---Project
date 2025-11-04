$ErrorActionPreference = 'Stop'

# Resolve repo root (directory containing this script's parent)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "[1/4] Ensuring virtual environment (.venv)" -ForegroundColor Cyan
if (!(Test-Path .venv)) {
	python -m venv .venv
}

Write-Host "[2/4] Activating venv and installing requirements" -ForegroundColor Cyan
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "[3/4] Configuring environment" -ForegroundColor Cyan
if (-not $env:PORT) { $env:PORT = '5000' }
$env:USE_WAITRESS = '1'

Write-Host "[4/4] Starting server on http://127.0.0.1:$($env:PORT)" -ForegroundColor Green
python app.py






