"""
Complete App Test Suite
=======================
1. Correctness Tests     - Known-answer questions across all difficulty levels
2. Security Tests        - SQL injection, write operations, prompt injection
3. Edge Case Tests       - Empty inputs, long inputs, nonsense, ambiguous questions
4. Schema Coverage Tests - Every table gets queried at least once
5. Performance Tests     - Latency benchmarks
"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.chains import generate_sql, run_sql, generate_response
from src.utils import validate_sql_readonly, validate_question, clean_sql
from src.database import get_table_names, get_cached_table_info, execute_query

PASS = 0
FAIL = 0
TOTAL_TIME = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def test_query(question, expected_in_result=None, expected_in_answer=None, should_fail=False):
    """Run a full chain test: question -> SQL -> execute -> answer."""
    global TOTAL_TIME
    try:
        t0 = time.time()
        sql = generate_sql(question)
        is_valid, err = validate_sql_readonly(sql)
        if not is_valid:
            if should_fail:
                test(f"Q: {question[:60]}", True)
                return
            test(f"Q: {question[:60]}", False, f"Generated unsafe SQL: {err}")
            return

        result = run_sql(sql)
        answer = generate_response(question, result)
        elapsed = time.time() - t0
        TOTAL_TIME += elapsed

        if should_fail:
            test(f"Q: {question[:60]}", False, "Expected failure but succeeded")
            return

        combined = (result + " " + answer).lower()

        if expected_in_result:
            found = expected_in_result.lower() in combined
            test(f"Q: {question[:60]}  ({elapsed:.1f}s)", found,
                 f"Expected '{expected_in_result}' not found")
        elif expected_in_answer:
            found = expected_in_answer.lower() in combined
            test(f"Q: {question[:60]}  ({elapsed:.1f}s)", found,
                 f"Expected '{expected_in_answer}' not found")
        else:
            test(f"Q: {question[:60]}  ({elapsed:.1f}s)", "error" not in result.lower())

    except Exception as e:
        if should_fail:
            test(f"Q: {question[:60]}", True)
        else:
            test(f"Q: {question[:60]}", False, f"Exception: {e}")


def run_all():
    global PASS, FAIL, TOTAL_TIME

    # ================================================================
    # 1. CORRECTNESS TESTS — Known-answer questions
    # ================================================================
    print("\n" + "=" * 70)
    print("1. CORRECTNESS TESTS (known-answer verification)")
    print("=" * 70)

    # Simple
    print("\n  --- Simple Queries ---")
    test_query("How many customers are there?", expected_in_result="59")
    test_query("How many artists are in the database?", expected_in_result="275")
    test_query("How many tracks are there?", expected_in_result="3503")
    test_query("How many invoices exist?", expected_in_result="412")
    test_query("How many genres are there?", expected_in_result="25")
    test_query("How many playlists are there?", expected_in_result="18")
    test_query("How many employees work at the company?", expected_in_result="8")
    test_query("How many media types are there?", expected_in_result="5")

    # Filtered
    print("\n  --- Filtered Queries ---")
    test_query("How many customers are in the USA?", expected_in_result="13")
    test_query("How many customers are in Brazil?", expected_in_result="5")
    test_query("How many customers are in Canada?", expected_in_result="8")

    # JOINs
    print("\n  --- JOIN Queries ---")
    test_query("How many tracks does AC/DC have?", expected_in_result="18")
    test_query("Which country generated the highest revenue?", expected_in_answer="USA")
    test_query("What is the most purchased track?", expected_in_answer=None)  # just check it works

    # Aggregations
    print("\n  --- Aggregation Queries ---")
    test_query("What is the average invoice total?", expected_in_result="5.6")
    test_query("What is the total revenue from all invoices?", expected_in_result="2328")
    test_query("How many customers does each country have? Show top 3", expected_in_answer="USA")

    # Complex
    print("\n  --- Complex Queries ---")
    test_query("Who are the top 5 customers by total spending?", expected_in_answer=None)
    test_query("Find employees who do not report to anyone", expected_in_answer="Andrew")
    test_query("What are the top 3 best-selling genres?", expected_in_answer="Rock")
    test_query("List all employees with their manager's name", expected_in_answer=None)
    test_query("Rank customers by spending within each country", expected_in_answer=None)

    # ================================================================
    # 2. SECURITY TESTS
    # ================================================================
    print("\n" + "=" * 70)
    print("2. SECURITY TESTS")
    print("=" * 70)

    # SQL injection via validate_sql_readonly
    print("\n  --- SQL Write Operation Blocking ---")
    test("Block DROP TABLE", validate_sql_readonly('DROP TABLE "Customer"')[0] == False)
    test("Block DELETE FROM", validate_sql_readonly('DELETE FROM "Customer"')[0] == False)
    test("Block INSERT INTO", validate_sql_readonly('INSERT INTO "Customer" VALUES (1)')[0] == False)
    test("Block UPDATE SET", validate_sql_readonly('UPDATE "Customer" SET "FirstName"=\'x\'')[0] == False)
    test("Block ALTER TABLE", validate_sql_readonly('ALTER TABLE "Customer" DROP COLUMN "Email"')[0] == False)
    test("Block CREATE TABLE", validate_sql_readonly('CREATE TABLE hack(id int)')[0] == False)
    test("Block TRUNCATE", validate_sql_readonly('TRUNCATE TABLE "Customer"')[0] == False)
    test("Block GRANT", validate_sql_readonly('GRANT ALL ON "Customer" TO public')[0] == False)
    test("Block REVOKE", validate_sql_readonly('REVOKE ALL ON "Customer" FROM public')[0] == False)
    test("Block lowercase drop", validate_sql_readonly('drop table "Customer"')[0] == False)
    test("Block mixed case DrOp", validate_sql_readonly('DrOp TaBlE "Customer"')[0] == False)
    test("Allow SELECT", validate_sql_readonly('SELECT * FROM "Customer"')[0] == True)
    test("Allow SELECT with JOIN", validate_sql_readonly('SELECT * FROM "Customer" c JOIN "Invoice" i ON c."CustomerId" = i."CustomerId"')[0] == True)
    test("Allow CTE", validate_sql_readonly('WITH cte AS (SELECT 1) SELECT * FROM cte')[0] == True)

    # Input validation (prompt injection)
    print("\n  --- Input Validation / Prompt Injection ---")
    test("Reject empty input", validate_question("")[0] == False)
    test("Reject whitespace only", validate_question("   ")[0] == False)
    test("Reject >500 chars", validate_question("x" * 501)[0] == False)
    test("Accept 500 chars", validate_question("x" * 500)[0] == True)
    test("Reject DROP TABLE in question", validate_question("DROP TABLE customers")[0] == False)
    test("Reject DELETE FROM in question", validate_question("Please DELETE FROM users")[0] == False)
    test("Reject INSERT INTO in question", validate_question("INSERT INTO users VALUES(1)")[0] == False)
    test("Accept normal question", validate_question("How many customers?")[0] == True)
    test("Accept 'drop' in context", validate_question("What is the drop in sales?")[0] == True)

    # run_sql enforcement
    print("\n  --- run_sql Write Enforcement ---")
    try:
        run_sql('DROP TABLE "Customer"')
        test("run_sql blocks DROP", False)
    except ValueError:
        test("run_sql blocks DROP", True)

    try:
        run_sql('DELETE FROM "Customer" WHERE 1=1')
        test("run_sql blocks DELETE", False)
    except ValueError:
        test("run_sql blocks DELETE", True)

    try:
        run_sql('UPDATE "Customer" SET "FirstName"=\'hacked\'')
        test("run_sql blocks UPDATE", False)
    except ValueError:
        test("run_sql blocks UPDATE", True)

    # ================================================================
    # 3. EDGE CASE TESTS
    # ================================================================
    print("\n" + "=" * 70)
    print("3. EDGE CASE TESTS")
    print("=" * 70)

    # SQL cleaning
    print("\n  --- SQL Cleaning ---")
    test("Clean ```sql fences", clean_sql("```sql\nSELECT 1\n```") == "SELECT 1")
    test("Clean ``` fences", clean_sql("```\nSELECT 1\n```") == "SELECT 1")
    test("Clean SQLQUERY: prefix", clean_sql("SQLQUERY: SELECT 1") == "SELECT 1")
    test("Clean SQL: prefix", clean_sql("SQL: SELECT 1") == "SELECT 1")
    test("Strip whitespace", clean_sql("  SELECT 1  ") == "SELECT 1")

    # Ambiguous / tricky questions (just check they don't crash)
    print("\n  --- Tricky Questions (should not crash) ---")
    test_query("What?", expected_in_answer=None)
    test_query("Show me everything", expected_in_answer=None)
    test_query("Who is the best employee?", expected_in_answer=None)
    test_query("Compare Rock vs Jazz sales", expected_in_answer=None)

    # ================================================================
    # 4. SCHEMA COVERAGE TESTS — Every table queried
    # ================================================================
    print("\n" + "=" * 70)
    print("4. SCHEMA COVERAGE TESTS (every table)")
    print("=" * 70)

    tables = get_table_names()
    test(f"Found all 11 tables ({len(tables)})", len(tables) >= 11)

    table_questions = {
        "Album": ("How many albums are there?", "347"),
        "Artist": ("How many artists are there?", "275"),
        "Customer": ("How many customers are there?", "59"),
        "Employee": ("How many employees are there?", "8"),
        "Genre": ("How many genres exist?", "25"),
        "Invoice": ("How many invoices are there?", "412"),
        "InvoiceLine": ("How many invoice lines are there?", "2240"),
        "MediaType": ("How many media types exist?", "5"),
        "Playlist": ("How many playlists are there?", "18"),
        "PlaylistTrack": ("How many playlist-track associations are there?", "8715"),
        "Track": ("How many tracks are in the database?", "3503"),
    }

    # Direct SQL verification (no LLM needed)
    print("\n  --- Direct Table Count Verification ---")
    for table, (_, expected) in table_questions.items():
        try:
            result = execute_query(f'SELECT COUNT(*) AS cnt FROM "{table}"')
            test(f"{table} has {expected} rows", expected in result)
        except Exception as e:
            test(f"{table} query", False, str(e))

    # Schema info loads
    info = get_cached_table_info()
    test("Schema info is non-empty", len(info) > 500)

    # ================================================================
    # 5. PERFORMANCE TESTS
    # ================================================================
    print("\n" + "=" * 70)
    print("5. PERFORMANCE SUMMARY")
    print("=" * 70)

    total_llm_calls = PASS + FAIL  # approximate
    if TOTAL_TIME > 0:
        print(f"\n  Total LLM chain time:  {TOTAL_TIME:.1f}s")
        print(f"  Avg per LLM query:     {TOTAL_TIME / max(1, total_llm_calls - 30):.1f}s")  # subtract non-LLM tests
    else:
        print("\n  No LLM queries ran.")

    # ================================================================
    # FINAL SUMMARY
    # ================================================================
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    total = PASS + FAIL
    pct = PASS / total * 100 if total > 0 else 0
    print(f"\n  PASSED:  {PASS}/{total}  ({pct:.1f}%)")
    print(f"  FAILED:  {FAIL}/{total}")
    print("=" * 70)

    return FAIL == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
