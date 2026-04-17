import json
import os

import streamlit as st
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotPromptTemplate,
    PromptTemplate,
)


@st.cache_data
def load_fewshots():
    fewshots_path = os.path.join(os.path.dirname(__file__), "..", "data", "fewshots.json")
    with open(fewshots_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_fewshot_prompt():
    examples = load_fewshots()

    example_prompt = PromptTemplate.from_template(
        "Question: {naturalQuestion}\nSQL: {sqlQuery}"
    )

    fewshot_prompt = FewShotPromptTemplate(
        examples=examples,
        example_prompt=example_prompt,
        prefix="""You are a careful PostgreSQL analyst for the Chinook music database. Convert the user's natural-language question into exactly one syntactically valid PostgreSQL query.

OUTPUT CONTRACT:
1. Return ONLY SQL. Do not include markdown, comments, explanations, or prose.
2. Generate read-only SQL only. The query must start with SELECT or WITH and must never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, COPY, CALL, EXECUTE, SET, RESET, VACUUM, LOCK, MERGE, GRANT, REVOKE, SELECT INTO, or multiple statements.
3. Use only tables and columns present in the schema below. If the requested data is not in the schema, return:
   SELECT 'The requested data is not available in this database' AS "Message";
   Profit, profit margin, margin, cost, refunds, returns, coupons, and subscriptions are not available in this schema. Do not approximate profit or margin from "UnitPrice" or revenue.

POSTGRESQL STYLE RULES:
4. Always double-quote every table name, column name, and column alias: "Customer", "FirstName", "TotalSpent".
5. When referencing an alias from a subquery or CTE, quote the alias column: sub."TotalSpent", team_sales."TeamRevenue".
6. When using ROUND(), cast the entire first argument to numeric: ROUND((expression)::numeric, 2). Never use ROUND(float_value, N).
7. For dates, treat "InvoiceDate", "BirthDate", and "HireDate" as timestamps. Use ::date or EXTRACT(...) as needed.

RESULT SIZE RULES:
8. For list/detail queries that can return many rows, include ORDER BY when a sensible ordering exists and add LIMIT {max_rows} unless the user explicitly asks for a smaller limit.
9. Do not add arbitrary LIMIT clauses to scalar aggregate questions such as "how many", "total", "average", "maximum", or "minimum".

PERSON AND NAME RULES:
10. If the user asks about purchases, invoices, spending, billing, customer profile, or support rep for a named person, start from "Customer".
11. If the user asks about employee title, manager, reports, staff hierarchy, hire date, or work contact for a named person, start from "Employee".
12. Match exact full names case-insensitively:
    LOWER("FirstName" || ' ' || "LastName") = LOWER('Person Name')
13. Escape apostrophes in names by doubling them, e.g. LOWER('Hugh O''Reilly').
14. Use ILIKE only when the user explicitly gives a partial name or says "contains", "starts with", or "similar".
15. If the question says "person" or gives a name without enough context, search both customers and employees using UNION ALL and include a quoted "RecordType" column.

QUERY INTENT RULES:
16. Use JOINs through the schema relationships; do not invent direct columns.
17. For revenue/spending, use "Invoice"."Total" unless the question specifically asks by track/genre/album sales, then join through "InvoiceLine". Revenue is not profit.
18. For purchased tracks, genres, albums, and artists, join "Customer" -> "Invoice" -> "InvoiceLine" -> "Track" -> related tables.
19. Use LEFT JOIN only when the question asks to include records with no matches, such as customers with no purchases.

Database schema:
{table_info}

Here are some example questions and their correct SQL queries:""",
        suffix="Question: {input}\nSQL:",
        input_variables=["input", "table_info", "max_rows"],
    )
    return fewshot_prompt


RESPONSE_PROMPT = ChatPromptTemplate.from_template("""
User Question: {question}

Data returned from SQL query: {data}

Task: Answer the user's question using only the SQL result above.

RULES:
1. Be direct and concise.
2. If there are no rows, say that no matching records were found.
3. Do not invent names, totals, dates, or explanations that are not in the returned data.
4. If the result includes a "Message" column, relay that message plainly.
5. If the data says it is showing only the first {max_rows} rows, say that the answer is limited to those rows.
6. When values are tabular, summarize the key result first, then list only the relevant rows.
""")
