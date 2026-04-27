import json
import os
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotPromptTemplate,
    PromptTemplate,
)
import streamlit as st


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
        prefix="""You are a PostgreSQL expert. Given a user question, generate a syntactically correct PostgreSQL query.

CRITICAL RULES:
1. Always wrap ALL table names, column names, AND column aliases in double quotes (e.g., "TotalSpent", "Revenue") because PostgreSQL folds unquoted identifiers to lowercase. When referencing a subquery alias in an outer query, use: subquery_alias."ColumnAlias" (e.g., customer_revenue."CustomerRevenue").
2. When using ROUND(), ALWAYS cast the ENTIRE first argument to numeric: ROUND((expression)::numeric, 2). Never use ROUND(float_value, N) — PostgreSQL requires explicit cast. Example: ROUND((SUM("Total") / COUNT(*))::numeric, 2).
3. Only use tables and columns that exist in the schema below. If the question asks about data that does NOT exist in the schema (e.g., coupons, refunds, subscriptions, profit margins, returns), do NOT generate a query. Instead return: SELECT 'The requested data is not available in this database' AS "Message";
4. Return ONLY the SQL query, no explanations.

Database schema:
{table_info}

Here are some example questions and their correct SQL queries:""",
        suffix="Question: {input}\nSQL:",
        input_variables=["input", "table_info"],
    )
    return fewshot_prompt


RESPONSE_PROMPT = ChatPromptTemplate.from_template("""
User Question: {question}

Data returned from SQL query: {data}

Task: Answer the user's question based on the data returned from the SQL query.
Provide a clear, concise answer in natural language.
""")
