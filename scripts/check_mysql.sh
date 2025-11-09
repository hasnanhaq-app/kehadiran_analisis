#!/usr/bin/env bash
# Simple wrapper to load .env (if present) and run the Python MySQL check script.
# Make executable with: chmod +x scripts/check_mysql.sh

set -eu

# load .env if it exists
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  source .env
  set +a
fi

python3 scripts/check_mysql.py
