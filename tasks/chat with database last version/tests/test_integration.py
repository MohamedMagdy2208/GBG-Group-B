"""Integration tests — test the full chain against the live database and Azure OpenAI."""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import get_db, get_cached_table_info, get_table_names, execute_query
from src.chains import generate_sql, run_sql, generate_response
from src.utils import validate_sql_readonly


def run_tests():
    passed = 0
    failed = 0
    results = []

    def test(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            results.append(f"  [PASS] {name}")
        else:
            failed += 1
            results.append(f"  [FAIL] {name}")

    # === Database Connection Tests ===
    print("=" * 60)
    print("TEST SUITE: Database Connection")
    print("=" * 60)

    try:
        db = get_db()
        test("Database connection", db is not None)
    except Exception as e:
        test(f"Database connection (error: {e})", False)

    try:
        tables = get_table_names()
        test("Get table names", len(tables) > 0)
        expected_tables = {"Album", "Artist", "Customer", "Employee", "Genre",
                           "Invoice", "InvoiceLine", "MediaType", "Playlist",
                           "PlaylistTrack", "Track"}
        test(f"All 11 tables present ({len(tables)} found)", expected_tables.issubset(set(tables)))
    except Exception as e:
        test(f"Get table names (error: {e})", False)

    try:
        table_info = get_cached_table_info()
        test("Schema cache loads", len(table_info) > 100)
    except Exception as e:
        test(f"Schema cache (error: {e})", False)

    for r in results:
        print(r)

    # === Direct Query Tests ===
    results.clear()
    print("\n" + "=" * 60)
    print("TEST SUITE: Direct SQL Execution")
    print("=" * 60)

    try:
        result = execute_query('SELECT COUNT(*) AS cnt FROM "Customer"')
        test("Count customers", "59" in result)
    except Exception as e:
        test(f"Count customers (error: {e})", False)

    try:
        result = execute_query('SELECT COUNT(*) AS cnt FROM "Track"')
        test("Count tracks", "3503" in result)
    except Exception as e:
        test(f"Count tracks (error: {e})", False)

    try:
        result = execute_query('SELECT COUNT(*) AS cnt FROM "Artist"')
        test("Count artists", "275" in result)
    except Exception as e:
        test(f"Count artists (error: {e})", False)

    # Test read-only enforcement
    try:
        run_sql('DROP TABLE "Customer"')
        test("Block DROP TABLE", False)
    except ValueError:
        test("Block DROP TABLE", True)
    except Exception as e:
        test(f"Block DROP TABLE (unexpected error: {e})", False)

    try:
        run_sql('DELETE FROM "Customer"')
        test("Block DELETE", False)
    except ValueError:
        test("Block DELETE", True)

    for r in results:
        print(r)

    # === Summary ===
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
