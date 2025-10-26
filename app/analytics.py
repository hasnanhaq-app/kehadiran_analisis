"""Simple analytics helpers to load SQL data into pandas DataFrames.

This module provides small convenience functions for analysts to run
SQL queries against the configured `DATABASE_URL` and return pandas
DataFrame objects for further processing.

It intentionally keeps a minimal surface area: get_engine(), query_to_df(),
and a few small helpers for the example `items` and `users` models in this repo.
"""
from __future__ import annotations

import os
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

def get_engine(database_url: Optional[str] = None, **engine_kwargs) -> Engine:
    """Create and return a SQLAlchemy engine.

    By default the function reads `DATABASE_URL` from environment if
    `database_url` argument is not provided.
    """
    url = database_url or os.getenv("DATABASE_URL") or "sqlite:///./test.db"

    connect_args = engine_kwargs.pop("connect_args", None)
    if url.startswith("sqlite"):
        # default sqlite connect args
        connect_args = connect_args or {"check_same_thread": False}

    # enable pool_pre_ping for reliable MySQL connections
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args or {}, **engine_kwargs)
    return engine


def query_to_df(sql: str, engine: Optional[Engine] = None, database_url: Optional[str] = None, **pd_read_sql_kwargs) -> pd.DataFrame:
    """Execute a SQL string and return a pandas DataFrame.

    Either `engine` or `database_url` (or env `DATABASE_URL`) will be used.
    Any kwargs are forwarded to `pandas.read_sql_query`.
    """
    if engine is None:
        engine = get_engine(database_url)
    with engine.connect() as conn:
        df = pd.read_sql_query(sql, conn, **pd_read_sql_kwargs)
    return df


def get_items_df(engine: Optional[Engine] = None) -> pd.DataFrame:
    """Return a DataFrame of all rows in `items` table.

    Columns: id, name, description
    """
    sql = "SELECT id, name, description FROM items"
    return query_to_df(sql, engine=engine)


def get_users_df(engine: Optional[Engine] = None) -> pd.DataFrame:
    """Return a DataFrame of all rows in `users` table.

    Columns: id, name, email
    """
    sql = "SELECT id, name, email FROM users"
    return query_to_df(sql, engine=engine)


def items_summary(engine: Optional[Engine] = None) -> pd.DataFrame:
    """Return a small summary DataFrame for items: counts and sample grouping.

    Example output columns: name, count, example_description
    """
    df = get_items_df(engine=engine)
    if df.empty:
        return pd.DataFrame(columns=["name", "count", "example_description"])

    grouped = df.groupby("name").agg(
        count=("id", "count"),
        example_description=("description", "first"),
    )
    result = grouped.reset_index().sort_values("count", ascending=False)
    return result


def query_to_df_chunks(sql: str, engine: Optional[Engine] = None, database_url: Optional[str] = None, chunksize: int = 10000, **pd_read_sql_kwargs):
    """Yield DataFrame chunks from a SQL query.

    Use this for tables that are too large to fit in memory. This returns an
    iterator of pandas DataFrame objects; each chunk will contain up to
    `chunksize` rows.
    """
    if engine is None:
        engine = get_engine(database_url)

    conn = engine.connect()
    try:
        iterator = pd.read_sql_query(sql, conn, chunksize=chunksize, **pd_read_sql_kwargs)
        for chunk in iterator:
            yield chunk
    finally:
        conn.close()


def to_csv_chunked(sql: str, csv_path: str, engine: Optional[Engine] = None, database_url: Optional[str] = None, chunksize: int = 10000, **pd_read_sql_kwargs):
    """Execute a query and write results to CSV in chunks.

    This writes the first chunk with header and then appends subsequent chunks
    without header; useful to export very large tables without loading them
    fully into memory.
    """
    first = True
    for chunk in query_to_df_chunks(sql, engine=engine, database_url=database_url, chunksize=chunksize, **pd_read_sql_kwargs):
        if first:
            chunk.to_csv(csv_path, index=False, mode="w")
            first = False
        else:
            chunk.to_csv(csv_path, index=False, mode="a", header=False)
    return csv_path
