"""Bootstrap Chinook CSV files into the configured SQL database."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import inspect

from src.database.client import DatabaseManager
from src.database.schema import CHINOOK_TABLES, build_metadata


CSV_ENCODING = "latin-1"


def bootstrap_database(
    db: DatabaseManager,
    data_dir: Path,
    replace_existing: bool = False,
) -> dict:
    """Create tables and load CSV data into the configured database."""

    metadata = build_metadata()
    table_names = [table.name for table in CHINOOK_TABLES]
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    if replace_existing and existing_tables:
        metadata.drop_all(db.engine, checkfirst=True)

    metadata.create_all(db.engine, checkfirst=True)

    loaded_counts: dict[str, int] = {}
    with db.engine.begin() as connection:
        for table in CHINOOK_TABLES:
            csv_path = data_dir / f"{table.name}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing CSV file for table '{table.name}': {csv_path}")

            if not replace_existing and table.name in existing_tables:
                count = connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table.name}"').scalar_one()
                loaded_counts[table.name] = int(count)
                continue

            dataframe = pd.read_csv(csv_path, encoding=CSV_ENCODING)
            dataframe = dataframe.where(pd.notnull(dataframe), None)
            if replace_existing:
                connection.exec_driver_sql(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE')
            elif table.name in existing_tables:
                connection.exec_driver_sql(f'DELETE FROM "{table.name}"')

            dataframe.to_sql(table.name, connection, if_exists="append", index=False, method="multi")
            loaded_counts[table.name] = int(len(dataframe))

    return {"status": "success", "tables": table_names, "row_counts": loaded_counts}


def bootstrap_required(db: DatabaseManager) -> bool:
    """Return True when one or more core tables are missing."""

    expected = [table.name for table in CHINOOK_TABLES]
    return not db.has_required_tables(expected)
