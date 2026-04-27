import streamlit as st
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from src.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
)
from src.database import get_cached_table_info, execute_query
from src.prompts import build_fewshot_prompt, RESPONSE_PROMPT
from src.utils import clean_sql, validate_sql_readonly

MAX_RETRIES = 2

SQL_FIX_PROMPT = ChatPromptTemplate.from_template("""The following PostgreSQL query failed with an error. Fix the query and return ONLY the corrected SQL.

Original question: {question}
Failed SQL: {failed_sql}
Error: {error}

RULES:
- Wrap ALL identifiers and aliases in double quotes (PostgreSQL is case-sensitive for quoted identifiers).
- Use ROUND((expression)::numeric, 2) — never ROUND(float, N).
- When referencing a subquery/CTE alias column, always use double quotes: sub."ColumnName".
- Return ONLY the corrected SQL query, no explanation.

Corrected SQL:""")


@st.cache_resource
def get_llm():
    return AzureChatOpenAI(
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def generate_sql(question: str) -> str:
    """Generate a SQL query from a natural language question."""
    llm = get_llm()
    prompt = build_fewshot_prompt()
    chain = prompt | llm | StrOutputParser()
    table_info = get_cached_table_info()
    raw = chain.invoke({"input": question, "table_info": table_info})
    return clean_sql(raw)


def _fix_sql(question: str, failed_sql: str, error: str) -> str:
    """Ask the LLM to fix a failed SQL query."""
    llm = get_llm()
    chain = SQL_FIX_PROMPT | llm | StrOutputParser()
    raw = chain.invoke({
        "question": question,
        "failed_sql": failed_sql,
        "error": str(error)[:500],
    })
    return clean_sql(raw)


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


def generate_response(question: str, data: str) -> str:
    """Generate a natural language response from query results."""
    llm = get_llm()
    chain = RESPONSE_PROMPT | llm | StrOutputParser()
    return chain.invoke({"question": question, "data": data})
