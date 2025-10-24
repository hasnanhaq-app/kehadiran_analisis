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
