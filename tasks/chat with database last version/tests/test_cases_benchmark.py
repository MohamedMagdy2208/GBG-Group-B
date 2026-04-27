"""
Comprehensive Benchmark from test cases.txt
============================================
Runs all 7 categories + the recommended 20-question benchmark.
Scores each on: SQL correctness, schema understanding, robustness.

Scoring: 0 = wrong/hallucinated, 1 = partial, 2 = fully correct
"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.chains import generate_sql, run_sql_with_retry, generate_response
from src.utils import validate_sql_readonly

RESULTS = []
TOTAL_TIME = 0


def run_question(category, difficulty, question, expected=None, should_have_no_data=False):
    """Run a single question through the full chain and score it."""
    global TOTAL_TIME
    entry = {
        "category": category,
        "difficulty": difficulty,
        "question": question,
        "score": 0,
        "detail": "",
    }

    try:
        t0 = time.time()
        sql = generate_sql(question)
        is_valid, err = validate_sql_readonly(sql)
        if not is_valid:
            entry["detail"] = f"BLOCKED: {err}"
            entry["score"] = 0
            RESULTS.append(entry)
            return

        result, sql = run_sql_with_retry(question, sql)
        answer = generate_response(question, result)
        elapsed = time.time() - t0
        TOTAL_TIME += elapsed

        combined = (result + " " + answer).lower()

        # For error-handling questions (no data exists)
        if should_have_no_data:
            if any(w in combined for w in ["not available", "no ", "does not", "doesn't", "cannot", "don't have", "no results", "unavailable", "not exist", "not found", "not present", "not in", "no data", "no such", "unfortunately"]):
                entry["score"] = 2
                entry["detail"] = f"({elapsed:.1f}s) Correctly identified missing data"
            elif "no results" in combined or result.strip() == "No results found.":
                entry["score"] = 1
                entry["detail"] = f"({elapsed:.1f}s) Returned empty but didn't explain why"
            else:
                entry["score"] = 0
                entry["detail"] = f"({elapsed:.1f}s) May have hallucinated"
        elif expected:
            if expected.lower() in combined:
                entry["score"] = 2
                entry["detail"] = f"({elapsed:.1f}s) Found expected: '{expected}'"
            else:
                # Check if SQL ran without error
                if "error" not in result.lower() and result != "No results found.":
                    entry["score"] = 1
                    entry["detail"] = f"({elapsed:.1f}s) SQL ran but expected '{expected}' not found"
                else:
                    entry["score"] = 0
                    entry["detail"] = f"({elapsed:.1f}s) Failed - expected '{expected}'"
        else:
            # No expected value — just check it ran successfully
            if "error" not in result.lower() and result.strip() != "":
                entry["score"] = 2
                entry["detail"] = f"({elapsed:.1f}s) OK"
            elif result == "No results found.":
                entry["score"] = 1
                entry["detail"] = f"({elapsed:.1f}s) No results returned"
            else:
                entry["score"] = 0
                entry["detail"] = f"({elapsed:.1f}s) Error in execution"

        # Print SQL for inspection
        sql_preview = sql.replace('\n', ' ')[:100]
        entry["sql_preview"] = sql_preview

    except Exception as e:
        entry["score"] = 0
        entry["detail"] = f"EXCEPTION: {str(e)[:100]}"

    RESULTS.append(entry)


def print_category(cat_name):
    cat_results = [r for r in RESULTS if r["category"] == cat_name]
    if not cat_results:
        return
    total_score = sum(r["score"] for r in cat_results)
    max_score = len(cat_results) * 2
    pct = total_score / max_score * 100 if max_score > 0 else 0

    for r in cat_results:
        score_label = ["WRONG", "PARTIAL", "CORRECT"][r["score"]]
        print(f"  [{score_label:7s}] {r['question'][:65]}")
        print(f"           {r['detail']}")

    print(f"\n  Category Score: {total_score}/{max_score} ({pct:.0f}%)\n")


def main():
    print("=" * 80)
    print("CHINOOK SQL CHATBOT — FULL BENCHMARK (from test cases.txt)")
    print("Model: Azure OpenAI GPT-4o")
    print("=" * 80)

    # ---- 1) Easy ----
    print("\n" + "-" * 80)
    print("1) EASY QUESTIONS")
    print("-" * 80)
    run_question("Easy", "easy", "How many customers are in the database?", expected="59")
    run_question("Easy", "easy", "List all customers from Brazil.", expected="Brazil")
    run_question("Easy", "easy", "Show the first name, last name, and email of all employees.")
    run_question("Easy", "easy", "Which tracks belong to the album Big Ones?")
    run_question("Easy", "easy", "List all playlists in the database.", expected="18")
    run_question("Easy", "easy", "How many invoices were created in 2009?")
    run_question("Easy", "easy", "Show all genres available in the database.")
    run_question("Easy", "easy", "Who is the manager of employee Jane Peacock?", expected="Nancy")
    run_question("Easy", "easy", "List all artists whose name starts with A.")
    run_question("Easy", "easy", "What is the unit price of the track Balls to the Wall?")
    print_category("Easy")

    # ---- 2) Medium ----
    print("-" * 80)
    print("2) MEDIUM QUESTIONS")
    print("-" * 80)
    run_question("Medium", "medium", "Which 10 customers spent the most money overall?")
    run_question("Medium", "medium", "What are the top 5 best-selling tracks by quantity sold?")
    run_question("Medium", "medium", "Which countries generated the most invoice revenue?", expected="USA")
    run_question("Medium", "medium", "How many invoices were created by each customer?")
    run_question("Medium", "medium", "Which employee supports the most customers?")
    run_question("Medium", "medium", "What are the top 5 selling genres by revenue?", expected="Rock")
    run_question("Medium", "medium", "Which albums have the most tracks?")
    run_question("Medium", "medium", "What is the average invoice total by country?")
    run_question("Medium", "medium", "Which city has the highest number of customers?")
    run_question("Medium", "medium", "List customers who have never made a purchase.")
    run_question("Medium", "medium", "Which artists have the most tracks in the database?")
    run_question("Medium", "medium", "What are the monthly sales totals for 2010?")
    run_question("Medium", "medium", "Which media type has the most tracks?")
    run_question("Medium", "medium", "Show the number of tracks in each playlist.")
    run_question("Medium", "medium", "Which customers bought tracks from the genre Rock?")
    print_category("Medium")

    # ---- 3) Hard ----
    print("-" * 80)
    print("3) HARD QUESTIONS")
    print("-" * 80)
    run_question("Hard", "hard", "Which customer spent the most on Rock music?")
    run_question("Hard", "hard", "What are the top 3 artists by total sales revenue?")
    run_question("Hard", "hard", "Which employee's customers generated the highest total revenue?")
    run_question("Hard", "hard", "For each country, what is the best-selling genre?")
    run_question("Hard", "hard", "Which album generated the highest revenue?")
    run_question("Hard", "hard", "Which customer bought the largest number of distinct tracks?")
    run_question("Hard", "hard", "Which customers purchased tracks from more than 3 different genres?")
    run_question("Hard", "hard", "What percentage of total revenue comes from the top 10 customers?")
    run_question("Hard", "hard", "Which track generated the most revenue in 2012?")
    run_question("Hard", "hard", "Find the most popular artist in each country based on purchases.")
    run_question("Hard", "hard", "Which genre has the highest average track price?")
    run_question("Hard", "hard", "Find customers whose total spending is above the average customer spending.")
    print_category("Hard")

    # ---- 4) Advanced Analytical ----
    print("-" * 80)
    print("4) ADVANCED ANALYTICAL QUESTIONS")
    print("-" * 80)
    run_question("Advanced", "advanced", "Compare sales in 2011 versus 2012 by percentage growth.")
    run_question("Advanced", "advanced", "Which 5 customers are most at risk of churn based on oldest last purchase date?")
    run_question("Advanced", "advanced", "What is the customer lifetime value by customer?")
    run_question("Advanced", "advanced", "Which sales agent has the highest average revenue per customer?")
    run_question("Advanced", "advanced", "Find the median invoice total.")
    run_question("Advanced", "advanced", "Which customers made purchases in multiple years?")
    run_question("Advanced", "advanced", "What is the average number of tracks per invoice?")
    run_question("Advanced", "advanced", "Which invoice contains the highest number of line items?")
    run_question("Advanced", "advanced", "What share of revenue comes from USA customers versus non-USA customers?", expected="USA")
    run_question("Advanced", "advanced", "Which countries have above-average invoice totals?")
    print_category("Advanced")

    # ---- 5) Edge-case / Ambiguity ----
    print("-" * 80)
    print("5) EDGE-CASE & AMBIGUITY QUESTIONS")
    print("-" * 80)
    run_question("Ambiguity", "edge", "Show the best customer.")
    run_question("Ambiguity", "edge", "Who is the top employee?")
    run_question("Ambiguity", "edge", "Which is the most popular album?")
    run_question("Ambiguity", "edge", "What is the biggest genre?")
    run_question("Ambiguity", "edge", "Show sales by location.")
    run_question("Ambiguity", "edge", "Which customers are active?")
    run_question("Ambiguity", "edge", "What is the best-selling music?")
    run_question("Ambiguity", "edge", "Which artist performs best?")
    run_question("Ambiguity", "edge", "What is the average purchase?")
    run_question("Ambiguity", "edge", "Which country is best?")
    print_category("Ambiguity")

    # ---- 6) Error-Handling (data doesn't exist) ----
    print("-" * 80)
    print("6) ERROR-HANDLING QUESTIONS (missing data)")
    print("-" * 80)
    run_question("ErrorHandling", "error", "Show revenue by quarter for 2015.", should_have_no_data=True)
    run_question("ErrorHandling", "error", "Which customers subscribed last month?", should_have_no_data=True)
    run_question("ErrorHandling", "error", "What is the refund rate?", should_have_no_data=True)
    run_question("ErrorHandling", "error", "Which products were returned most often?", should_have_no_data=True)
    run_question("ErrorHandling", "error", "Show profit margin by genre.", should_have_no_data=True)
    run_question("ErrorHandling", "error", "Which customers used coupons?", should_have_no_data=True)
    print_category("ErrorHandling")

    # ---- 7) SQL Stress Tests ----
    print("-" * 80)
    print("7) SQL STRESS-TEST QUESTIONS")
    print("-" * 80)
    run_question("StressTest", "stress", "Find customers whose spending is in the top 10% of all customers.")
    run_question("StressTest", "stress", "Rank artists by revenue within each genre.")
    run_question("StressTest", "stress", "Show the second highest spending customer in each country.")
    run_question("StressTest", "stress", "Find albums where every track is longer than 5 minutes.")
    run_question("StressTest", "stress", "Return the top 3 tracks per genre by revenue.")
    run_question("StressTest", "stress", "Find employees who support customers in more than 3 countries.")
    run_question("StressTest", "stress", "Show invoices where the total does not match the sum of line items.")
    run_question("StressTest", "stress", "Find duplicate track names across different albums.")
    run_question("StressTest", "stress", "Show customers whose average invoice total is above their country average.")
    print_category("StressTest")

    # ================================================================
    # FINAL SUMMARY
    # ================================================================
    print("=" * 80)
    print("FINAL BENCHMARK SUMMARY")
    print("=" * 80)

    categories = ["Easy", "Medium", "Hard", "Advanced", "Ambiguity", "ErrorHandling", "StressTest"]
    grand_total = 0
    grand_max = 0

    print(f"\n  {'Category':<20} {'Score':>8} {'Max':>6} {'Pct':>7} {'Questions':>10}")
    print(f"  {'-'*20} {'-'*8} {'-'*6} {'-'*7} {'-'*10}")

    for cat in categories:
        cat_results = [r for r in RESULTS if r["category"] == cat]
        score = sum(r["score"] for r in cat_results)
        mx = len(cat_results) * 2
        pct = score / mx * 100 if mx > 0 else 0
        grand_total += score
        grand_max += mx
        print(f"  {cat:<20} {score:>8} {mx:>6} {pct:>6.0f}% {len(cat_results):>10}")

    grand_pct = grand_total / grand_max * 100 if grand_max > 0 else 0
    total_questions = len(RESULTS)

    print(f"  {'-'*20} {'-'*8} {'-'*6} {'-'*7} {'-'*10}")
    print(f"  {'TOTAL':<20} {grand_total:>8} {grand_max:>6} {grand_pct:>6.1f}% {total_questions:>10}")

    # Score distribution
    correct = sum(1 for r in RESULTS if r["score"] == 2)
    partial = sum(1 for r in RESULTS if r["score"] == 1)
    wrong = sum(1 for r in RESULTS if r["score"] == 0)

    print(f"\n  Score Distribution:")
    print(f"    CORRECT (2):  {correct}/{total_questions}  ({correct/total_questions*100:.0f}%)")
    print(f"    PARTIAL (1):  {partial}/{total_questions}  ({partial/total_questions*100:.0f}%)")
    print(f"    WRONG   (0):  {wrong}/{total_questions}  ({wrong/total_questions*100:.0f}%)")

    print(f"\n  Total Time:     {TOTAL_TIME:.0f}s")
    print(f"  Avg per Query:  {TOTAL_TIME/max(total_questions,1):.1f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
