#!/usr/bin/env bash
# Helper script to run scripts/run_rekap.py over an SSH tunnel using env vars or a .env file.
# Usage:
# 1) Create a `.env` in the project root (see .env.example) or export env vars.
# 2) Make executable: chmod +x scripts/run_rekap_ssh.sh
# 3) Run: ./scripts/run_rekap_ssh.sh

set -euo pipefail
cd "$(dirname "$0")/.."

# Load .env if it exists (export variables)
if [ -f .env ]; then
  # Safely parse simple KEY=VALUE lines from .env and export them.
  # This avoids shell parsing errors when values contain characters like ()
  while IFS= read -r line || [ -n "$line" ]; do
    # skip comments and blank lines
    case "$line" in
      \#*|"") continue ;;
    esac
    # only parse lines with KEY=VALUE
    if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      key="${line%%=*}"
      val="${line#*=}"
      # remove surrounding single or double quotes if present (safely)
      if [[ "$val" =~ ^".*"$ ]]; then
        # remove surrounding double quotes safely
        val="${val#\"}"
        val="${val%\"}"
      elif [[ "$val" =~ ^'.*'$ ]]; then
        # remove surrounding single quotes safely
        val="${val#\'}"
        val="${val%\'}"
      fi
      export "$key"="$val"
    fi
  done < .env
fi

# Defaults
: "${SSH_PORT:=22}"
: "${DB_HOST:=127.0.0.1}"
: "${DB_PORT:=3306}"
: "${LOCAL_URL:=sqlite:///./local.db}"
: "${OUT_EXCEL:=}" # if empty, script chooses default

# Accept command-line overrides for instansi/month/year and out-excel
NO_PROMPT=0
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --instansi)
      INSTANSI="$2"; shift 2;;
    --month)
      MONTH="$2"; shift 2;;
    --year)
      YEAR="$2"; shift 2;;
    --out-excel)
      OUT_EXCEL="$2"; shift 2;;
    --no-prompt)
      NO_PROMPT=1; shift;;
    -h|--help)
      echo "Usage: $0 [--instansi ID] [--month M] [--year Y] [--out-excel FILE] [--no-prompt]"; exit 0;;
    *)
      # stop parsing on first unknown -- assume rest are not for this script
      break;;
  esac
done

# Prompt for missing non-secret values (unless --no-prompt)
if [ $NO_PROMPT -eq 0 ]; then
  if [ -z "${INSTANSI:-}" ]; then
    read -rp "instansi (e.g. 3062): " INSTANSI
  fi
  if [ -z "${MONTH:-}" ]; then
    read -rp "month (1-12): " MONTH
  fi
  if [ -z "${YEAR:-}" ]; then
    read -rp "year (e.g. 2025): " YEAR
  fi
else
  # if no-prompt and required values are missing, error out
  if [ -z "${INSTANSI:-}" ] || [ -z "${MONTH:-}" ] || [ -z "${YEAR:-}" ]; then
    echo "Error: --no-prompt set but --instansi/--month/--year not provided" >&2
    exit 2
  fi
fi

# Prompt for secrets if missing
if [ -z "${SSH_HOST:-}" ]; then
  read -rp "SSH host: " SSH_HOST
fi
if [ -z "${SSH_USER:-}" ]; then
  read -rp "SSH user: " SSH_USER
fi
if [ -z "${SSH_PASSWORD:-}" ]; then
  read -rsp "SSH password (input hidden): " SSH_PASSWORD
  echo
fi
if [ -z "${DB_USER:-}" ]; then
  read -rp "DB user: " DB_USER
fi
if [ -z "${DB_PASSWORD:-}" ]; then
  read -rsp "DB password (input hidden): " DB_PASSWORD
  echo
fi
if [ -z "${DB_NAME:-}" ]; then
  read -rp "DB name (default: bkd_presensi): " DB_NAME
  DB_NAME=${DB_NAME:-bkd_presensi}
fi

# Prepare out excel default if not supplied
# Prepare default out excel if not supplied
if [ -z "${OUT_EXCEL}" ]; then
  OUT_EXCEL="rekap_${INSTANSI}_${MONTH}_${YEAR}.xlsx"
fi

# Ensure PYTHONPATH is set so local package imports work
export PYTHONPATH=.

echo "Running rekap for instansi=${INSTANSI} month=${MONTH} year=${YEAR}..."

python scripts/run_rekap.py \
  --use-ssh \
  --ssh-host "$SSH_HOST" \
  --ssh-port "$SSH_PORT" \
  --ssh-user "$SSH_USER" \
  --ssh-password "$SSH_PASSWORD" \
  --db-host "$DB_HOST" \
  --db-port "$DB_PORT" \
  --db-user "$DB_USER" \
  --db-password "$DB_PASSWORD" \
  --db-name "$DB_NAME" \
  --instansi "$INSTANSI" \
  --month "$MONTH" \
  --year "$YEAR" \
  --local-url "$LOCAL_URL" \
  --out-excel "$OUT_EXCEL"

echo "Done. If an Excel file was requested it will be under ./out/ or at the absolute path you provided."