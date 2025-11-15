import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import make_url

# Read DB URL from environment so user can point to a MySQL server.
# Example MySQL URL: mysql+pymysql://user:password@host:3306/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def create_database_if_missing() -> None:
    """Create the database (server-level) if it doesn't exist.

    This is a convenience for local development. It will do nothing for
    SQLite URLs. For server databases (MySQL) it connects to the server
    without selecting a database and issues CREATE DATABASE IF NOT EXISTS.

    Note: the connecting user must have privileges to CREATE DATABASE.
    """
    url = make_url(DATABASE_URL)
    backend = url.get_backend_name()
    # Nothing to do for SQLite
    if backend in ("sqlite",):
        return

    database = url.database
    if not database:
        # Nothing to create if no database specified in URL
        return

    # Build a URL that points to the server but not a specific database
    url_without_db = url.set(database=None)
    # Use a temporary engine to execute CREATE DATABASE
    tmp_engine = create_engine(str(url_without_db))
    try:
        with tmp_engine.connect() as conn:
            # ensure CREATE DATABASE runs outside transactional context
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        tmp_engine.dispose()


def init_db() -> None:
    """Create database (if needed) and tables.

    For production you should use migrations (Alembic). This helper is
    intended for development and testing convenience only.
    """
    # Respect environment toggle so production deployments don't create DBs.
    create_db_flag = os.getenv("CREATE_DB_ON_STARTUP", "false").lower()
    should_create_db = create_db_flag in ("1", "true", "yes")

    if should_create_db:
        # Try to create the database first (no-op for SQLite)
        create_database_if_missing()

    Base.metadata.create_all(bind=engine)
