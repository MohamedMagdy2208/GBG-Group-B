"""Prompt construction utilities for SQL generation and answer synthesis."""

from __future__ import annotations

import json

from src.utils.types import RetrievalDocument


def build_sql_generation_messages(
    question: str,
    retrieved_docs: list[RetrievalDocument],
    max_rows: int,
) -> list[dict[str, str]]:
    """Create messages that ask the model for one PostgreSQL query."""

    context_blob = "\n\n".join(
        [f"[{doc.kind}] {doc.title}\n{doc.text}" for doc in retrieved_docs]
    )
    system_message = (
        "You are a PostgreSQL analyst working on a music-store business database. "
        "Return JSON with keys sql, rationale, and clarification_needed. "
        "Generate exactly one read-only SELECT query. "
        "Prefer explicit joins, double-quote table and column names, and add LIMIT "
        f"{max_rows} when the user asks for rows rather than a pure aggregate."
    )
    user_message = (
        f"User question:\n{question}\n\n"
        f"Relevant context:\n{context_blob}\n\n"
        "Respond as JSON only."
    )
    return [{"role": "system", "content": system_message}, {"role": "user", "content": user_message}]


def build_answer_messages(
    question: str,
    sql: str,
    rows: list[dict],
) -> list[dict[str, str]]:
    """Create messages that ask the model to summarize SQL results."""

    system_message = (
        "You are a business analyst. Summarize SQL results accurately, keep numbers faithful "
        "to the data, and mention if the answer is based on a sample due to a row limit."
    )
    user_message = (
        f"Question:\n{question}\n\n"
        f"Executed SQL:\n{sql}\n\n"
        f"Rows:\n{json.dumps(rows, default=str, indent=2)}\n\n"
        "Write a concise answer for a business user."
    )
    return [{"role": "system", "content": system_message}, {"role": "user", "content": user_message}]

