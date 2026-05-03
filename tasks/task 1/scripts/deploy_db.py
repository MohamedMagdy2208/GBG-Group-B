"""
Database deployment script — loads 11 CSV files into PostgreSQL.
Works with both local PostgreSQL and Azure Database for PostgreSQL.

Usage:
    python scripts/deploy_db.py
    # or with a custom DATABASE_URL:
    DATABASE_URL=postgresql://... python scripts/deploy_db.py
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set.")
    print("Set it in .env or export it before running this script.")
    sys.exit(1)

CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "csv")

FILE_LIST = [
    "Artist.csv",
    "Album.csv",
    "MediaType.csv",
    "Genre.csv",
    "Employee.csv",
    "Customer.csv",
    "Invoice.csv",
    "Track.csv",
    "InvoiceLine.csv",
    "Playlist.csv",
    "PlaylistTrack.csv",
]


def deploy():
    engine = create_engine(DATABASE_URL)

    print(f"Connecting to database...")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Connection successful.\n")

    for filename in FILE_LIST:
        filepath = os.path.join(CSV_DIR, filename)
        table_name = filename.replace(".csv", "")

        try:
            df = pd.read_csv(filepath)
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            print(f"  [OK] {table_name}: {len(df)} rows loaded")
        except Exception as e:
            print(f"  [FAIL] {table_name}: {e}")

    # Verify
    print("\n--- Verification ---")
    with engine.connect() as conn:
        for filename in FILE_LIST:
            table_name = filename.replace(".csv", "")
            try:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                count = result.scalar()
                print(f"  {table_name}: {count} rows")
            except Exception as e:
                print(f"  {table_name}: ERROR - {e}")

    print("\nDone.")


if __name__ == "__main__":
    deploy()
