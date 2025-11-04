# Kehadiran Analisis (FastAPI ETL)

This repository contains a small FastAPI example plus ETL tooling converted from a Jupyter notebook that performs attendance (kehadiran) analysis.

What I added
- `app/presensi.py` — transformed core notebook functions (helpers and `generate_presensi_laporan`).
- `app/etl.py` — chunked ETL helpers (fetch from remote DB, transform, load into local DB).
- `scripts/run_rekap.py` — CLI to fetch presence tables (via direct DB URL or SSH tunnel), run the transform, and save results to the local DB or Excel.
- `scripts/run_etl.py` — generic chunked ETL runner (source -> transform -> local DB).
- `tests/test_presensi.py` — unit tests for the presensi helpers and a basic generate_presensi_laporan scenario.

Quick setup

1. Create and activate a virtualenv (macOS / zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Environment variables

- `DATABASE_URL` — local database where results will be stored (e.g. `sqlite:///./local.db`).
- `REMOTE_DATABASE_URL` — optional, remote DB URL for direct access (e.g. `mysql+pymysql://user:pass@host:3306/bkd_presensi`).
- For SSH mode (use `--use-ssh`): set or pass `SSH_HOST`, `SSH_PORT`, `SSH_USER`, `SSH_PASSWORD` (or use key files). Also provide `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

Security note: avoid committing secrets to the repo. Prefer to provide credentials at runtime or use a secrets manager.

Running the attendance rekap (rekapitulasi)

Direct DB URL mode (recommended if remote DB is accessible):

```bash
export REMOTE_DATABASE_URL='mysql+pymysql://user:pass@host:3306/bkd_presensi'
export DATABASE_URL='sqlite:///./local.db'

python scripts/run_rekap.py --instansi 3062 --month 10 --year 2025
```

SSH tunneling mode (use when DB only reachable via SSH):

```bash
export DATABASE_URL='sqlite:///./local.db'

python scripts/run_rekap.py \
	--use-ssh \
	--ssh-host kehadiran-bkd.pemkomedan.go.id \
	--ssh-port 8570 \
	--ssh-user root \
	--ssh-password '<SSH_PASSWORD>' \
	--db-user root \
	--db-password '<DB_PASSWORD>' \
	--instansi 3062 --month 10 --year 2025
```

The script will:
- fetch `presensi_karyawan`, `presensi_rencana_shift`, `presensi_kehadiran`, `presensi_absen`, and `presensi_shift` tables from the remote source;
- merge shift schedules into the rencana table similar to the notebook;
- call `generate_presensi_laporan` to build the `df_laporan` DataFrame;
- write the result to the local DB table `rekap_kehadiran` (default) or an Excel file if `--out-excel` is passed.

ETL scripts and usage (expanded)
--------------------------------

There are two main helper scripts for ETL work in this repo:

- `scripts/run_rekap.py` — high-level runner that fetches the presence-related tables from a remote DB (either via a direct SQLAlchemy URL or over an SSH tunnel), runs the notebook-derived transform in `app/presensi.py` (`generate_presensi_laporan`), writes the resulting DataFrame to the local database table `rekap_kehadiran`, and optionally exports an Excel report.
- `scripts/run_etl.py` — a generic, chunk-aware ETL runner that uses `app/etl.py` to fetch large tables in chunks, apply a transform, and append results to a local DB without loading everything into memory.

Usage summary (two common modes):

1) Direct DB URL mode (recommended when you can connect directly):

```bash
export DATABASE_URL='sqlite:///./local.db'
export REMOTE_DATABASE_URL='mysql+pymysql://user:pass@host:3306/bkd_presensi'

python scripts/run_rekap.py \
	--instansi 3062 \
	--month 10 \
	--year 2025 \
	--local-url "$DATABASE_URL" \
	--remote-url "$REMOTE_DATABASE_URL"
```

2) SSH tunneling mode (when the DB is only reachable via SSH):

```bash
export DATABASE_URL='sqlite:///./local.db'

python scripts/run_rekap.py \
	--use-ssh \
	--ssh-host kehadiran-host.example.org \
	--ssh-port 22 \
	--ssh-user root \
	--ssh-password '<SSH_PASSWORD>' \
	--db-user root \
	--db-password '<DB_PASSWORD>' \
	--db-name bkd_presensi \
	--instansi 3062 \
	--month 10 \
	--year 2025 \
	--local-url "$DATABASE_URL" \
	--out-excel rekap_3062_10_2025.xlsx
```

Output handling
---------------

- Excel output: by default the runner will place Excel reports into an `out/` directory. If you pass `--out-excel` with a relative filename (for example `rekap.xlsx`), the runner will create `out/` (if missing) and write `out/rekap.xlsx`. If you pass an absolute path it is used as-is.
- Local DB: the default local DB table is `rekap_kehadiran`. You can change the local DB via the `--local-url` flag or the `DATABASE_URL` environment variable.
- Repository hygiene: generated outputs under `out/` are ignored via `.gitignore` to avoid committing large or sensitive exports.

Dependency & compatibility notes
-------------------------------

- Required packages (examples): pandas, sqlalchemy, pymysql, sshtunnel, paramiko==2.11.0, openpyxl, pytest.
- Important: `sshtunnel` depends on `paramiko` APIs that were changed in `paramiko` 4.x. We pin `paramiko==2.11.0` in `requirements.txt` to avoid runtime import errors when using SSH tunnels.
- Excel export uses `openpyxl` as the pandas engine — make sure it is installed if you plan to write `.xlsx` files.

Tests & CI
----------

- Unit tests for the presensi transform live in `tests/test_presensi.py`. Run them locally with:

```bash
# with venv activated
pytest -q
```

- A GitHub Actions workflow (`.github/workflows/pytest.yml`) runs the test suite on pushes and PRs.

Troubleshooting (common issues)
------------------------------

- Missing `openpyxl` when writing Excel: `pip install openpyxl`.
- `sshtunnel` fails with `AttributeError` referencing `DSSKey` or similar: ensure `paramiko==2.11.0` is installed (older `paramiko` is compatible with the version of `sshtunnel` used here).
- TypeError comparing Timestamp with date in transformations: the runner coerces presensi timestamp columns with `pd.to_datetime` before comparisons; if you modify upstream columns make sure they are parseable datetimes.

Housekeeping: local DB & generated files
--------------------------------------

If you created a local SQLite database (for example `local.db`) during tests or an ETL run and you prefer not to keep it in the Git history, untrack it and add it to `.gitignore`:

```bash
# remove from git index but keep local file
git rm --cached local.db || true
echo 'local.db' >> .gitignore
git add .gitignore && git commit -m "Ignore local DB"
```

Try it: minimal end-to-end
-------------------------

1. Create and activate venv and install deps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run a quick ETL (replace values with your credentials or use SSH mode):

```bash
export DATABASE_URL='sqlite:///./local.db'
export REMOTE_DATABASE_URL='mysql+pymysql://user:pass@host:3306/bkd_presensi'

python scripts/run_rekap.py --instansi 3062 --month 10 --year 2025 --local-url "$DATABASE_URL" --remote-url "$REMOTE_DATABASE_URL"
```

The report will be written into `out/` and the `rekap_kehadiran` table will be created/updated in the local DB.

Using `.env` and the SSH helper
--------------------------------

For convenient, repeatable runs you can store non-secret defaults in `.env` (do not commit it). A `.env.example` is provided. Quick steps:

```bash
# copy the example and edit .env locally
cp .env.example .env
# edit .env and fill SSH_HOST, SSH_USER, DB_USER, DB_PASSWORD, INSTANSI, MONTH, YEAR as needed
```

There's a helper script `scripts/run_rekap_ssh.sh` that will read `.env` (or prompt for missing values) and run the ETL over an SSH tunnel. Make it executable and run it like this:

```bash
chmod +x scripts/run_rekap_ssh.sh
./scripts/run_rekap_ssh.sh --instansi 3062 --month 10 --year 2025
```

The helper supports `--out-excel` to set the Excel filename and `--no-prompt` to run non-interactively (requires the values to be present in `.env` or passed as flags).

Chunked ETL

If you're working with very large tables, use `app/etl.py` and `scripts/run_etl.py` which support reading in chunks and writing incrementally to avoid OOM.

Running tests

```bash
# from project root, virtualenv active
pytest -q
```

Notes & next improvements

- Performance: `generate_presensi_laporan` currently iterates rows and may be slow for very large datasets. I can help vectorize/group operations for speed.
- Schema: results are written with `pandas.DataFrame.to_sql`. For production, consider creating a proper schema and Alembic migrations.
- Deprecations: Pydantic and FastAPI show deprecation warnings in tests (see `app/schemas.py` and `app/main.py`). Consider updating to lifespan handlers and Pydantic v2 `ConfigDict` if you plan to upgrade.

If you want, I can add a GitHub Actions workflow to run tests on push and a sample `.env.example` file to document env variables.

— End of README
# Simple FastAPI app

This is a minimal FastAPI example using a venv.

Quick start (macOS / zsh):

1. Create a virtual environment and activate it

```bash
cd /Users/macbookm1/Code/python/fastAPI-base
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app

```bash
uvicorn app.main:app --reload
```

4. Run tests

```bash
PYTHONPATH=. pytest -q
```

Notes:
- The app is simple and stores items in memory. For production, use a database.
- `.venv/` is ignored in `.gitignore`.

Database (MySQL) configuration
--------------------------------

Set the `DATABASE_URL` environment variable to point to your MySQL database. Example:

```bash
export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/dbname"
```

If `DATABASE_URL` is not set the app defaults to a local SQLite file `./test.db` which is convenient for development and testing.

Note: This project uses SQLAlchemy ORM. For production schema migrations, integrate Alembic.

Alembic (database migrations)
------------------------------

This project includes an Alembic configuration that reads the `DATABASE_URL` from
the environment. Use Alembic to generate, inspect, and apply schema migrations.

Basic workflow (development)

1. Load environment variables and activate the venv

```bash
cd /Users/macbookm1/Code/python/fastAPI-base
set -a; source .env; set +a
source .venv/bin/activate
export PYTHONPATH=.
```

2. Generate an autogenerate migration (creates a new file under `alembic/versions`)

```bash
alembic -c alembic.ini revision --autogenerate -m "describe changes"
```

3. Review the generated migration file and adjust if needed. Then apply it to the
	target database:

```bash
alembic -c alembic.ini upgrade head
```

If the database already contains the tables (for example you created them manually or via `init_db()`),
mark the current revision without applying SQL with:

```bash
# record current models as applied
alembic -c alembic.ini stamp head
```

Useful Alembic commands

- `alembic -c alembic.ini current` — show current revision of the DB
- `alembic -c alembic.ini history` — show migration history
- `alembic -c alembic.ini downgrade -1` — roll back one migration
- `alembic -c alembic.ini show <rev>` — show revision script

Notes and safety

- Always review autogenerated migrations before applying them, especially in production.
- Do not run migrations against a production database without backups and a rollback plan.
- For CI, create a fresh test database and run `alembic upgrade head` against it to ensure migrations apply.
- Alembic uses `alembic/env.py` which imports `app.models` to gather `MetaData` for autogenerate — keep your models importable (use `PYTHONPATH=.` when running commands from project root).

If you want, I can add convenience Makefile targets (e.g. `make db-upgrade`, `make db-rev`) or CI steps that run Alembic automatically.

Analytics (pandas)
-------------------

This repo includes a small analytics helper module at `app/analytics.py` that
lets analysts load database tables into pandas DataFrames and run simple
aggregations. It is intentionally lightweight and intended for ad-hoc analysis.

Quick usage

```bash
cd /Users/macbookm1/Code/python/fastAPI-base
source .venv/bin/activate
set -a; source .env; set +a
python scripts/analytics_example.py
```

This script will read `items` and `users` from the database configured by
`DATABASE_URL`, write CSVs to the `analytics_output/` folder, and print the
output path.

If you need more complex ETL/analysis pipelines, I can add an example using
`dask` for larger-than-memory data, or a notebook with example visualizations.

Chunked reads for large tables
-----------------------------

If your tables are larger than available memory you can use the chunked-read
helpers in `app/analytics.py`:

- `query_to_df_chunks(sql, engine=None, chunksize=10000)` — returns an iterator
	of pandas DataFrame chunks.
- `to_csv_chunked(sql, csv_path, engine=None, chunksize=10000)` — stream-query
	results and write them to CSV without loading the entire table into memory.

Example: export a large table to CSV without OOM

```bash
cd /Users/macbookm1/Code/python/fastAPI-base
source .venv/bin/activate
set -a; source .env; set +a
python - <<'PY'
from app.analytics import to_csv_chunked
sql = 'SELECT * FROM very_large_table'
to_csv_chunked(sql, 'very_large_table.csv', chunksize=20000)
print('done')
PY
```

If you need more throughput, I can add a parallel exporter (process pool or dask) that writes partitions concurrently.

Controlling automatic DB creation
--------------------------------

For local convenience the app can attempt to create the database on startup (this is useful when you don't want to run `CREATE DATABASE` manually). This is disabled by default in production. To enable it set the `CREATE_DB_ON_STARTUP` environment variable to `true`, `1` or `yes`.

You can set this in your `.env` (example):

```env
CREATE_DB_ON_STARTUP=true
```

If enabled, on startup the app will run `CREATE DATABASE IF NOT EXISTS ...` (MySQL only) before creating tables. The connecting user must have privileges to create databases.

Running the app with environment variables loaded
------------------------------------------------

Quick way to load `.env` and start the server (zsh):

```bash
cd /Users/macbookm1/Code/python/fastAPI-base
source .venv/bin/activate
# load .env and export values
set -a; source .env; set +a
uvicorn app.main:app --reload
```

Or use the provided helper script which activates the venv (if present), loads `.env`, and runs `uvicorn`:

```bash
./scripts/run_uvicorn.sh
```

If you want to run the server in background for development, you can use `nohup` or a process manager. Example (background, simple):

```bash
set -a; source .env; set +a
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &>/dev/null &
```

For production on macOS consider using launchd or a process manager (supervisord, systemd on Linux, or container orchestration). Brew service wrappers can also be used if you package the app as a service.
