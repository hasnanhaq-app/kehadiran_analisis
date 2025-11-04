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
