import streamlit as st
import re
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from src.config import (
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    MAX_RESULT_ROWS,
    require_env_vars,
)
from src.database import get_cached_table_info, execute_query
from src.history import format_chat_history
from src.prompts import build_fewshot_prompt, RESPONSE_PROMPT
from src.retrieval import select_relevant_fewshots
from src.utils import clean_sql, ensure_sql_limit, validate_sql_readonly

MAX_RETRIES = 2
UNAVAILABLE_DATA_SQL = (
    "SELECT 'The requested data is not available in this database' AS \"Message\";"
)
UNAVAILABLE_DATA_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bprofit\b",
        r"\bprofit\s+margins?\b",
        r"\bmargins?\b",
        r"\bcosts?\b",
        r"\brefunds?\b",
        r"\brefund\s+rate\b",
        r"\breturned\b",
        r"\breturns\b",
        r"\bcoupons?\b",
        r"\bsubscriptions?\b",
        r"\bsubscribed\b",
        r"\bpodcasts?\b",
    ]
]

SQL_FIX_PROMPT = ChatPromptTemplate.from_template("""The following PostgreSQL query failed with an error. Fix the query and return ONLY the corrected SQL.

Original question: {question}
Failed SQL: {failed_sql}
Error: {error}

RULES:
- Wrap ALL identifiers and aliases in double quotes (PostgreSQL is case-sensitive for quoted identifiers).
- Use ROUND((expression)::numeric, 2) - never ROUND(float, N).
- When referencing a subquery/CTE alias column, always use double quotes: sub."ColumnName".
- Return ONLY the corrected SQL query, no explanation.

Corrected SQL:""")


@st.cache_resource
def get_llm():
    env = require_env_vars("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")
    return AzureChatOpenAI(
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        azure_endpoint=env["AZURE_OPENAI_ENDPOINT"],
        api_key=env["AZURE_OPENAI_API_KEY"],
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=0,
    )


def _prepare_generated_sql(raw: str) -> str:
    sql = clean_sql(raw)
    is_valid, error_msg = validate_sql_readonly(sql)
    if not is_valid:
        raise ValueError(error_msg)
    sql = ensure_sql_limit(sql, MAX_RESULT_ROWS)
    is_valid, error_msg = validate_sql_readonly(sql)
    if not is_valid:
        raise ValueError(error_msg)
    return sql


def _get_unavailable_data_sql(question: str) -> str | None:
    if any(pattern.search(question) for pattern in UNAVAILABLE_DATA_PATTERNS):
        return UNAVAILABLE_DATA_SQL
    return None


def generate_sql(question: str, chat_history=None) -> str:
    """Generate a SQL query from a natural language question."""
    fallback_sql = _get_unavailable_data_sql(question)
    if fallback_sql:
        return _prepare_generated_sql(fallback_sql)

    llm = get_llm()
    examples = select_relevant_fewshots(question)
    prompt = build_fewshot_prompt(examples)
    chain = prompt | llm | StrOutputParser()
    table_info = get_cached_table_info()
    raw = chain.invoke({
        "input": question,
        "table_info": table_info,
        "max_rows": MAX_RESULT_ROWS,
        "chat_history": format_chat_history(chat_history),
    })
    return _prepare_generated_sql(raw)


def _fix_sql(question: str, failed_sql: str, error: str) -> str:
    """Ask the LLM to fix a failed SQL query."""
    llm = get_llm()
    chain = SQL_FIX_PROMPT | llm | StrOutputParser()
    raw = chain.invoke({
        "question": question,
        "failed_sql": failed_sql,
        "error": str(error)[:500],
    })
    return _prepare_generated_sql(raw)


def run_sql(sql: str) -> str:
    """Validate and execute a SQL query. Raises ValueError for write operations."""
    is_valid, error_msg = validate_sql_readonly(sql)
    if not is_valid:
        raise ValueError(error_msg)
    return execute_query(sql)


def run_sql_with_retry(question: str, sql: str) -> tuple[str, str]:
    """Execute SQL with auto-retry on failure. Returns (result, final_sql)."""
    is_valid, error_msg = validate_sql_readonly(sql)
    if not is_valid:
        raise ValueError(error_msg)

    last_error = None
    current_sql = sql
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = execute_query(current_sql)
            return result, current_sql
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                current_sql = _fix_sql(question, current_sql, str(e))
                is_valid, error_msg = validate_sql_readonly(current_sql)
                if not is_valid:
                    raise ValueError(error_msg)

    raise last_error


def generate_response(question: str, data: str, chat_history=None) -> str:
    """Generate a natural language response from query results."""
    llm = get_llm()
    chain = RESPONSE_PROMPT | llm | StrOutputParser()
    return chain.invoke({
        "question": question,
        "data": data,
        "max_rows": MAX_RESULT_ROWS,
        "chat_history": format_chat_history(chat_history),
    })
