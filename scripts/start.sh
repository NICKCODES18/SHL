#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3.11 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f "data/catalog.json" ] || [ "$(wc -c < data/catalog.json)" -lt 1000 ]; then
  echo "Building catalog from SHL website (first run)..."
  python -m app.scraper.catalog_scraper
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
