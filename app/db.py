import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read DB URL from environment so user can point to a MySQL server.
# Example MySQL URL: mysql+pymysql://user:password@host:3306/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db() -> None:
    """Create database tables (if they don't exist).

    This is a simple helper used during development and testing. For
    production, use proper migrations (Alembic).
    """
    Base.metadata.create_all(bind=engine)
