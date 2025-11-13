#!/usr/bin/env python3
"""
Check MySQL connectivity using SQLAlchemy. Reads environment variables or a
.env file. Useful for verifying the same connection string the app will use.

Usage:
  python scripts/check_mysql.py

Environment variables used (prefer setting in .env):
  REMOTE_DATABASE_URL (optional) - full SQLAlchemy URL
  or DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

The script prints a small summary and samples some rows from `rekap_kehadiran`.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def load_env():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # dotenv not installed or .env missing; rely on environment
        pass


def build_database_url():
    url = os.getenv("REMOTE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    db = os.getenv("DB_NAME", "bkd_presensi")

    if not (user and pwd):
        return None

    return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"


def main():
    load_env()
    db_url = build_database_url()
    if not db_url:
        print("No REMOTE_DATABASE_URL or DB_USER/DB_PASSWORD found in environment.")
        sys.exit(2)

    print("Using DB URL:", db_url.replace(os.getenv("DB_PASSWORD", ""), "<hidden>") )

    engine = create_engine(db_url, pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            print("SELECT 1 ->", conn.execute(text("SELECT 1")).scalar())

            # list tables (MySQL)
            try:
                tables = conn.execute(text("SHOW TABLES")).fetchall()
                tables_list = [t[0] for t in tables]
                print("Tables (first 20):", tables_list[:20])
            except Exception:
                print("Unable to run SHOW TABLES on this engine; skipping table list.")

            # sample rows from rekap_bulanan if it exists
            try:
                res = conn.execute(text("SELECT * FROM rekap_bulanan LIMIT 5")).fetchall()
                print(f"Sample rows from rekap_bulanan ({len(res)}):")
                for r in res:
                    print(r)
            except Exception:
                print("Table `rekap_bulanan` not found or unreadable; skip sample rows.")

    except SQLAlchemyError as e:
        print("Connection failed:", e)
        sys.exit(3)


if __name__ == "__main__":
    main()
