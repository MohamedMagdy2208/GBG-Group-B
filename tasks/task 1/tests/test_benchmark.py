"""Benchmark tests — test SQL generation accuracy and latency across question categories."""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.chains import generate_sql, run_sql, generate_response
from src.utils import validate_sql_readonly


# Test cases grouped by difficulty
BENCHMARK_CASES = [
    # --- Simple queries ---
    {
        "category": "Simple",
        "question": "How many customers are in the USA?",
        "expected_contains": "13",
        "description": "Simple COUNT with WHERE",
    },
    {
        "category": "Simple",
        "question": "How many tracks are in the database?",
        "expected_contains": "3503",
        "description": "Simple COUNT all rows",
    },
    {
        "category": "Simple",
        "question": "How many genres are there?",
        "expected_contains": "25",
        "description": "Simple COUNT on Genre table",
    },
    # --- JOIN queries ---
    {
        "category": "JOIN",
        "question": "Which country generated the highest revenue?",
        "expected_contains": "USA",
        "description": "GROUP BY + ORDER BY + LIMIT 1",
    },
    {
        "category": "JOIN",
        "question": "How many tracks does the artist AC/DC have?",
        "expected_contains": "18",
        "description": "Multi-table JOIN (Artist -> Album -> Track)",
    },
    {
        "category": "JOIN",
        "question": "What is the total number of invoices?",
        "expected_contains": "412",
        "description": "Simple COUNT on Invoice",
    },
    # --- Aggregation queries ---
    {
        "category": "Aggregation",
        "question": "What is the average invoice total?",
        "expected_contains": "5.6",
        "description": "AVG aggregation",
    },
    {
        "category": "Aggregation",
        "question": "How many customers does each country have? Show top 5.",
        "expected_contains": "USA",
        "description": "GROUP BY + ORDER BY + LIMIT",
    },
    # --- Complex queries ---
    {
        "category": "Complex",
        "question": "Who are the top 3 customers by total spending?",
        "expected_contains": None,  # Just check it runs
        "description": "JOIN + GROUP BY + ORDER BY + LIMIT",
    },
    {
        "category": "Complex",
        "question": "Find employees who do not report to anyone",
        "expected_contains": "Andrew",
        "description": "NULL check (General Manager)",
    },
    {
        "category": "Complex",
        "question": "What are the top 3 best-selling genres by number of tracks sold?",
        "expected_contains": "Rock",
        "description": "Multi-JOIN + GROUP BY + ORDER BY",
    },
    {
        "category": "Complex",
        "question": "List all employees with their manager's name",
        "expected_contains": None,
        "description": "Self-JOIN on Employee table",
    },
]


def run_benchmark():
    print("=" * 80)
    print("CHINOOK SQL CHATBOT — BENCHMARK TEST SUITE")
    print("Model: Azure OpenAI GPT-4o mini")
    print("=" * 80)

    total = len(BENCHMARK_CASES)
    passed = 0
    failed = 0
    errors = 0
    total_sql_time = 0
    total_exec_time = 0
    total_response_time = 0
    category_stats = {}

    for i, case in enumerate(BENCHMARK_CASES, 1):
        cat = case["category"]
        if cat not in category_stats:
            category_stats[cat] = {"passed": 0, "failed": 0, "errors": 0, "total_time": 0}

        print(f"\n--- Test {i}/{total}: [{cat}] {case['description']} ---")
        print(f"  Q: {case['question']}")

        try:
            # Generate SQL
            t0 = time.time()
            sql = generate_sql(case["question"])
            sql_time = time.time() - t0
            total_sql_time += sql_time
            print(f"  SQL ({sql_time:.2f}s): {sql[:120]}{'...' if len(sql) > 120 else ''}")

            # Validate read-only
            is_valid, err = validate_sql_readonly(sql)
            if not is_valid:
                print(f"  [FAIL] Generated unsafe SQL: {err}")
                failed += 1
                category_stats[cat]["failed"] += 1
                continue

            # Execute
            t1 = time.time()
            result = run_sql(sql)
            exec_time = time.time() - t1
            total_exec_time += exec_time
            print(f"  Result ({exec_time:.2f}s): {result[:100]}{'...' if len(result) > 100 else ''}")

            # Generate response
            t2 = time.time()
            answer = generate_response(case["question"], result)
            resp_time = time.time() - t2
            total_response_time += resp_time
            print(f"  Answer ({resp_time:.2f}s): {answer[:150]}{'...' if len(answer) > 150 else ''}")

            case_time = sql_time + exec_time + resp_time
            category_stats[cat]["total_time"] += case_time

            # Check expected
            if case["expected_contains"] is not None:
                if case["expected_contains"].lower() in (result + answer).lower():
                    print(f"  [PASS] Contains expected: '{case['expected_contains']}'")
                    passed += 1
                    category_stats[cat]["passed"] += 1
                else:
                    print(f"  [FAIL] Missing expected: '{case['expected_contains']}'")
                    failed += 1
                    category_stats[cat]["failed"] += 1
            else:
                # Just check it executed without error
                if "error" not in result.lower():
                    print(f"  [PASS] Executed successfully")
                    passed += 1
                    category_stats[cat]["passed"] += 1
                else:
                    print(f"  [FAIL] Execution returned error")
                    failed += 1
                    category_stats[cat]["failed"] += 1

        except Exception as e:
            print(f"  [ERROR] {e}")
            errors += 1
            category_stats[cat]["errors"] += 1

    # === Summary ===
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    print(f"\n  Total tests:    {total}")
    print(f"  Passed:         {passed}")
    print(f"  Failed:         {failed}")
    print(f"  Errors:         {errors}")
    print(f"  Accuracy:       {passed/total*100:.1f}%")
    print(f"\n  Avg SQL generation time:    {total_sql_time/total:.2f}s")
    print(f"  Avg query execution time:   {total_exec_time/max(total-errors,1):.2f}s")
    print(f"  Avg response generation:    {total_response_time/max(total-errors,1):.2f}s")
    print(f"  Total benchmark time:       {total_sql_time+total_exec_time+total_response_time:.1f}s")

    print(f"\n  Per-category breakdown:")
    for cat, stats in category_stats.items():
        cat_total = stats["passed"] + stats["failed"] + stats["errors"]
        pct = stats["passed"] / cat_total * 100 if cat_total > 0 else 0
        avg_time = stats["total_time"] / cat_total if cat_total > 0 else 0
        print(f"    {cat:15s}  {stats['passed']}/{cat_total} passed ({pct:.0f}%)  avg {avg_time:.2f}s/query")

    print("=" * 80)
    return errors == 0 and failed == 0


if __name__ == "__main__":
    success = run_benchmark()
    sys.exit(0 if success else 1)
