# Windows startup script
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt

$catalog = "data\catalog.json"
if (-not (Test-Path $catalog) -or (Get-Item $catalog).Length -lt 1000) {
    Write-Host "Building catalog from SHL website (first run)..."
    python -m app.scraper.catalog_scraper
}

$port = if ($env:PORT) { $env:PORT } else { "8000" }
uvicorn app.main:app --host 0.0.0.0 --port $port
