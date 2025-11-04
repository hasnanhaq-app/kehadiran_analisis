"""Small CLI to run the ETL for one or more tables.

This script is an entry point for running the ETL outside of the notebook.
It reads env vars `REMOTE_DATABASE_URL` and `DATABASE_URL` for source and
target DBs. You can also pass them as arguments.
"""
from __future__ import annotations

import argparse
import os
from typing import List

from app.etl import etl_table


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run ETL from remote DB into local DB")
    p.add_argument("--tables", nargs="+", required=True, help="Table names to ETL (space separated)")
    p.add_argument("--remote-url", default=os.getenv("REMOTE_DATABASE_URL"), help="Remote DB URL (overrides REMOTE_DATABASE_URL env)")
    p.add_argument("--local-url", default=os.getenv("DATABASE_URL"), help="Local DB URL (overrides DATABASE_URL env)")
    p.add_argument("--chunksize", type=int, default=10000, help="Chunk size for reading remote DB")
    p.add_argument("--where", default=None, help="Optional SQL WHERE clause to filter rows (no leading WHERE)")
    return p.parse_args()


def main():
    args = parse_args()

    remote = args.remote_url
    local = args.local_url
    if not remote:
        print("No remote DB URL provided. Set REMOTE_DATABASE_URL or pass --remote-url")
        return
    if not local:
        print("No local DB URL provided. Set DATABASE_URL or pass --local-url")
        return

    total = 0
    for table in args.tables:
        print(f"ETL table {table} from {remote} -> {local} (chunksize={args.chunksize})")
        try:
            written = etl_table(table, remote_database_url=remote, local_database_url=local, chunksize=args.chunksize, where=args.where)
        except Exception as exc:
            print(f"Failed ETL for {table}: {exc}")
            continue
        print(f"Wrote {written} rows to local table {table}")
        total += written

    print(f"ETL complete. Total rows written: {total}")


if __name__ == "__main__":
    main()
