#!/usr/bin/env bash
# Helper to load .env and run uvicorn for local development
# Usage: ./scripts/run_uvicorn.sh

set -euo pipefail

# Load .env into environment (export all key=value pairs)
if [ -f .env ]; then
  # export variables from .env into current environment
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo ".env not found in project root — create one or export DATABASE_URL yourself"
fi

# Activate venv if available
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Run uvicorn
exec uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}" --reload
