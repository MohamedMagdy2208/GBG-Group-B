import streamlit as st
from langchain_community.utilities import SQLDatabase
from sqlalchemy import text
from src.config import DATABASE_URL, SQL_QUERY_TIMEOUT_SECONDS


@st.cache_resource
def get_db():
    return SQLDatabase.from_uri(DATABASE_URL)


@st.cache_data(ttl=3600)
def get_cached_table_info():
    """Cache the database schema for 1 hour to avoid fetching on every query."""
    db = get_db()
    return db.get_table_info()


def get_table_names():
    """Return list of table names in the database."""
    db = get_db()
    return db.get_usable_table_names()


def get_table_columns(table_name: str) -> list[str]:
    """Return column names for a given table."""
    db = get_db()
    engine = db._engine
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table ORDER BY ordinal_position"
        ), {"table": table_name})
        return [row[0] for row in result]


MAX_RESULT_ROWS = 50


def execute_query(sql: str) -> str:
    """Execute a SQL query with a timeout and row limit."""
    db = get_db()
    engine = db._engine
    with engine.connect() as conn:
        conn.execute(text(f"SET statement_timeout = '{SQL_QUERY_TIMEOUT_SECONDS}s'"))
        result = conn.execute(text(sql))
        rows = result.fetchmany(MAX_RESULT_ROWS + 1)
        columns = list(result.keys())
        if not rows:
            return "No results found."
        truncated = len(rows) > MAX_RESULT_ROWS
        rows = rows[:MAX_RESULT_ROWS]
        output = ", ".join(columns) + "\n"
        for row in rows:
            output += ", ".join(str(v) for v in row) + "\n"
        if truncated:
            output += f"\n(Showing first {MAX_RESULT_ROWS} rows — query returned more results)"
        return output.strip()
