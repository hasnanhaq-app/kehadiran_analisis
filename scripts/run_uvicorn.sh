#!/usr/bin/env bash
# Helper to load .env and run uvicorn for local development
# Usage: ./scripts/run_uvicorn.sh

set -euo pipefail

# Load .env into environment (export all key=value pairs) without `source`
if [ -f .env ]; then
  # read lines, skip comments/blanks, export KEY=VALUE (preserves parentheses etc.)
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ''|\#*) continue ;;
    esac
    # skip lines without '='
    [ "${line#*=}" = "$line" ] && continue
    key=${line%%=*}
    value=${line#*=}
    # trim whitespace around key (mac sed)
    key=$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    # remove surrounding quotes from value if present
    if [[ $value =~ ^\".*\"$ || $value =~ ^\'.*\'$ ]]; then
      value=${value:1:-1}
    fi
    export "$key"="$value"
  done < .env
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