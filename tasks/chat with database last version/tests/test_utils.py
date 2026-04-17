"""Unit tests for SQL validation, input validation, and SQL cleaning."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import validate_sql_readonly, clean_sql, ensure_sql_limit, validate_question


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

    # === SQL Read-Only Validation ===
    print("=" * 60)
    print("TEST SUITE: SQL Read-Only Validation")
    print("=" * 60)

    # Should PASS (valid read-only queries)
    test("Simple SELECT", validate_sql_readonly('SELECT * FROM "Customer"')[0] == True)
    test("SELECT with WHERE", validate_sql_readonly('SELECT "Name" FROM "Artist" WHERE "ArtistId" = 1')[0] == True)
    test("SELECT with JOIN", validate_sql_readonly('SELECT c."FirstName", i."Total" FROM "Customer" c JOIN "Invoice" i ON c."CustomerId" = i."CustomerId"')[0] == True)
    test("SELECT with GROUP BY", validate_sql_readonly('SELECT "Country", COUNT(*) FROM "Customer" GROUP BY "Country"')[0] == True)
    test("SELECT with subquery", validate_sql_readonly('SELECT * FROM "Customer" WHERE "CustomerId" IN (SELECT "CustomerId" FROM "Invoice")')[0] == True)
    test("SELECT with CTE", validate_sql_readonly('WITH cte AS (SELECT * FROM "Customer") SELECT * FROM cte')[0] == True)
    test("SELECT with window function", validate_sql_readonly('SELECT "Name", RANK() OVER (ORDER BY "Milliseconds" DESC) FROM "Track"')[0] == True)

    # Should FAIL (write operations blocked)
    test("Block DROP TABLE", validate_sql_readonly('DROP TABLE "Customer"')[0] == False)
    test("Block DELETE", validate_sql_readonly('DELETE FROM "Customer" WHERE "CustomerId" = 1')[0] == False)
    test("Block INSERT", validate_sql_readonly('INSERT INTO "Customer" VALUES (1, "Test")')[0] == False)
    test("Block UPDATE", validate_sql_readonly('UPDATE "Customer" SET "FirstName" = "Hack"')[0] == False)
    test("Block ALTER", validate_sql_readonly('ALTER TABLE "Customer" ADD COLUMN "Hack" TEXT')[0] == False)
    test("Block CREATE", validate_sql_readonly('CREATE TABLE "Hack" (id INT)')[0] == False)
    test("Block TRUNCATE", validate_sql_readonly('TRUNCATE TABLE "Customer"')[0] == False)
    test("Block GRANT", validate_sql_readonly('GRANT ALL ON "Customer" TO public')[0] == False)
    test("Block mixed case drop", validate_sql_readonly('drop table "Customer"')[0] == False)
    test("Block SELECT INTO", validate_sql_readonly('SELECT 1 INTO "NewTable"')[0] == False)
    test("Block COPY", validate_sql_readonly('COPY "Customer" TO STDOUT')[0] == False)
    test("Block CALL", validate_sql_readonly('CALL refresh_customer_stats()')[0] == False)
    test("Block multiple statements", validate_sql_readonly('SELECT 1; SELECT 2')[0] == False)
    test("Allow forbidden words in strings", validate_sql_readonly('SELECT \'DROP TABLE is text\' AS "Message"')[0] == True)

    for r in results:
        print(r)

    # === SQL Cleaning ===
    results.clear()
    print("\n" + "=" * 60)
    print("TEST SUITE: SQL Cleaning")
    print("=" * 60)

    test("Remove ```sql fences", clean_sql('```sql\nSELECT 1\n```') == 'SELECT 1')
    test("Remove ``` fences", clean_sql('```\nSELECT 1\n```') == 'SELECT 1')
    test("Remove SQLQUERY: prefix", clean_sql('SQLQUERY: SELECT 1') == 'SELECT 1')
    test("Remove SQL: prefix", clean_sql('SQL: SELECT 1') == 'SELECT 1')
    test("Strip whitespace", clean_sql('  SELECT 1  ') == 'SELECT 1')
    test("Pass through clean SQL", clean_sql('SELECT * FROM "Customer"') == 'SELECT * FROM "Customer"')
    test("Preserve single-quoted string values", clean_sql('SELECT * FROM "Genre" WHERE "Name" = \'Rock\'') == 'SELECT * FROM "Genre" WHERE "Name" = \'Rock\'')
    test("Preserve fallback message string", clean_sql('SELECT \'The requested data is not available in this database\' AS "Message"') == 'SELECT \'The requested data is not available in this database\' AS "Message"')
    test("Quote qualified alias columns", clean_sql('SELECT sub.TotalSpent FROM sub ORDER BY TotalSpent DESC') == 'SELECT sub."TotalSpent" FROM sub ORDER BY "TotalSpent" DESC')
    test("Extract SQL from prose", clean_sql('Here is the query:\nSELECT 1 AS TotalRows') == 'SELECT 1 AS "TotalRows"')

    for r in results:
        print(r)

    # === SQL Limiting ===
    results.clear()
    print("\n" + "=" * 60)
    print("TEST SUITE: SQL Limiting")
    print("=" * 60)

    test("Add missing top-level LIMIT", ensure_sql_limit('SELECT * FROM "Customer"', 50) == 'SELECT * FROM "Customer"\nLIMIT 50')
    test("Preserve explicit top-level LIMIT", ensure_sql_limit('SELECT * FROM "Customer" LIMIT 5', 50) == 'SELECT * FROM "Customer" LIMIT 5')
    test("Add LIMIT before trailing semicolon", ensure_sql_limit('SELECT * FROM "Customer";', 50) == 'SELECT * FROM "Customer"\nLIMIT 50;')
    test("Do not limit scalar aggregate", ensure_sql_limit('SELECT COUNT(*) AS "TotalCustomers" FROM "Customer"', 50) == 'SELECT COUNT(*) AS "TotalCustomers" FROM "Customer"')
    test("Do not limit message query", ensure_sql_limit('SELECT \'The requested data is not available in this database\' AS "Message";', 50) == 'SELECT \'The requested data is not available in this database\' AS "Message";')

    for r in results:
        print(r)

    # === Input Validation ===
    results.clear()
    print("\n" + "=" * 60)
    print("TEST SUITE: Input Validation")
    print("=" * 60)

    test("Valid question", validate_question("How many customers?")[0] == True)
    test("Empty string rejected", validate_question("")[0] == False)
    test("Whitespace only rejected", validate_question("   ")[0] == False)
    test("Too long rejected (>500)", validate_question("x" * 501)[0] == False)
    test("Exactly 500 chars OK", validate_question("x" * 500)[0] == True)
    test("SQL injection: DROP TABLE", validate_question("DROP TABLE customers")[0] == False)
    test("SQL injection: DELETE FROM", validate_question("DELETE FROM users")[0] == False)
    test("SQL injection: INSERT INTO", validate_question("INSERT INTO users VALUES(1)")[0] == False)
    test("Normal question with 'drop' in context OK", validate_question("What is the drop in sales?")[0] == True)
    test("Normal question with 'delete' OK", validate_question("How to delete my account?")[0] == True)

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


def test_script_suite():
    assert run_tests()
