"""ETL helpers to fetch from a remote DB, transform, and load into the local DB.

This module uses the existing analytics helpers for SQL -> pandas chunks and
then writes to the local database using pandas.DataFrame.to_sql. It's intentionally
small and designed to be adapted to the actual notebook transformation logic.
"""
from __future__ import annotations

import os
from typing import Callable, Iterator, Optional

import pandas as pd
from sqlalchemy.engine import Engine

from .analytics import get_engine, query_to_df_chunks


def fetch_table_chunks(table: str, where: Optional[str] = None, chunksize: int = 10000, *, engine: Optional[Engine] = None, database_url: Optional[str] = None) -> Iterator[pd.DataFrame]:
    """Yield DataFrame chunks for `SELECT * FROM {table}` from the source DB.

    Provide either an `engine` or a `database_url` (or rely on env var). `where`
    can be used to filter rows (e.g. "timestamp >= '2025-01-01'").
    """
    sql = f"SELECT * FROM {table}"
    if where:
        sql = f"{sql} WHERE {where}"
    # query_to_df_chunks supports engine/database_url
    yield from query_to_df_chunks(sql, engine=engine, database_url=database_url, chunksize=chunksize)


def default_transform(df: pd.DataFrame) -> pd.DataFrame:
    """A small, safe default transform to apply to each chunk.

    - Normalize column names to snake_case-ish (lowercase, replace spaces)
    - Drop exact-duplicate rows
    - Attempt to parse any column with 'time' or 'date' in the name as datetime
    Users should replace this with notebook-specific transforms.
    """
    if df.empty:
        return df

    # normalize columns
    df = df.rename(columns=lambda c: str(c).strip().lower().replace(" ", "_") )

    # parse datetime-like columns heuristically
    for col in df.columns:
        if any(k in col for k in ("time", "date", "at", "timestamp")):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                # if parsing fails, leave as-is
                pass

    # drop exact duplicates
    df = df.drop_duplicates()
    return df


def append_chunks_to_table(chunks: Iterator[pd.DataFrame], table: str, local_engine: Optional[Engine] = None, local_database_url: Optional[str] = None, if_exists: str = "append") -> int:
    """Write chunk iterator into local DB table using pandas.to_sql.

    Returns total number of rows written.
    """
    written = 0
    # if local_engine is None, get_engine will use env DATABASE_URL
    engine = local_engine or get_engine(local_database_url)

    first = True
    for chunk in chunks:
        if chunk.empty:
            continue
        # use if_exists='replace' only for the first chunk when requested
        mode = if_exists if first else "append"
        chunk.to_sql(table, engine, if_exists=mode, index=False, method="multi")
        written += len(chunk)
        first = False

    return written


def etl_table(table: str, transform: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None, *,
              remote_database_url_env: str = "REMOTE_DATABASE_URL", local_database_url_env: str = "DATABASE_URL",
              remote_database_url: Optional[str] = None, local_database_url: Optional[str] = None,
              chunksize: int = 10000, where: Optional[str] = None) -> int:
    """Perform ETL for a single table: fetch -> transform -> load.

    - `transform` is applied to each chunk. If not provided, `default_transform`
      is used.
    - `remote_database_url` overrides env var `REMOTE_DATABASE_URL`.
    - `local_database_url` overrides env var `DATABASE_URL`.
    Returns number of rows written to local DB.
    """
    transform = transform or default_transform

    remote_url = remote_database_url or os.getenv(remote_database_url_env)
    local_url = local_database_url or os.getenv(local_database_url_env)

    # yield chunks from remote
    chunk_iter = fetch_table_chunks(table, where=where, chunksize=chunksize, database_url=remote_url)

    # apply transform and write chunk-by-chunk to avoid large memory usage
    def transformed_chunks() -> Iterator[pd.DataFrame]:
        for chunk in chunk_iter:
            try:
                out = transform(chunk)
            except Exception:
                # if transform fails for a chunk, skip or re-raise depending on needs
                raise
            yield out

    written = append_chunks_to_table(transformed_chunks(), table, local_database_url=local_url, if_exists="append")
    return written


__all__ = [
    "fetch_table_chunks",
    "default_transform",
    "append_chunks_to_table",
    "etl_table",
]
