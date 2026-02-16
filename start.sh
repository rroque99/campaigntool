#!/usr/bin/env bash
set -euo pipefail

# Gmail Email Campaign Tool — single-command startup
# Builds the frontend (if needed) and starts the backend, serving everything
# from a single process on port 8000.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Building frontend..."
cd "$SCRIPT_DIR/frontend"
npm install --silent
npm run build

echo "==> Installing backend dependencies..."
cd "$SCRIPT_DIR/backend"
uv sync --quiet

echo "==> Running database migrations..."
uv run alembic upgrade head

echo "==> Starting server on http://localhost:8000"
ENVIRONMENT=production uv run uvicorn src.campaign.main:app --host 0.0.0.0 --port 8000
