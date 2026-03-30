"""Database helpers for connectivity, schema inspection, and read-only querying."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from sqlalchemy import create_engine, inspect, text

from src.config.settings import Settings


class DatabaseManager:
    """Thin wrapper around SQLAlchemy for application-specific database tasks."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_engine(settings.database_url, future=True)

    def healthcheck(self) -> bool:
        """Return True when the database accepts a simple query."""

        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def table_names(self) -> list[str]:
        """Return the user tables visible to the application."""

        return inspect(self.engine).get_table_names()

    def execute_query(self, sql: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Execute a read-only query and return a list of dictionaries."""

        final_sql = sql.strip().rstrip(";")
        if limit and not re.search(r"\bLIMIT\s+\d+\b", final_sql, flags=re.IGNORECASE):
            final_sql = f"{final_sql}\nLIMIT {int(limit)}"

        with self.engine.connect() as connection:
            result = connection.execute(text(final_sql))
            rows = result.mappings().all()
        return [dict(row) for row in rows]

    def execute_many(self, statements: Iterable[str]) -> None:
        """Run a list of maintenance statements in a single transaction."""

        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def get_schema_snapshot(self) -> list[dict[str, Any]]:
        """Collect a compact schema snapshot for prompting and retrieval."""

        inspector = inspect(self.engine)
        snapshot: list[dict[str, Any]] = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            snapshot.append(
                {
                    "table": table_name,
                    "columns": [
                        {
                            "name": column["name"],
                            "type": str(column["type"]),
                            "nullable": column["nullable"],
                            "default": column.get("default"),
                        }
                        for column in columns
                    ],
                    "foreign_keys": [
                        {
                            "constrained_columns": fk["constrained_columns"],
                            "referred_table": fk["referred_table"],
                            "referred_columns": fk["referred_columns"],
                        }
                        for fk in foreign_keys
                    ],
                }
            )
        return snapshot

    def has_required_tables(self, required_tables: Iterable[str]) -> bool:
        """Check whether a set of expected tables is already present."""

        available = set(self.table_names())
        return all(table in available for table in required_tables)


def build_database_manager(settings: Settings) -> DatabaseManager:
    """Factory used by app startup and tests."""

    return DatabaseManager(settings)
