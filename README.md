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
