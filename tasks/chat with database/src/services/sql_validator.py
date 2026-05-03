"""Read-only SQL validation helpers."""

from __future__ import annotations

import re


FORBIDDEN_SQL_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bCOPY\b",
]


def normalize_sql(sql: str) -> str:
    """Trim surrounding whitespace and remove a trailing semicolon."""

    return sql.strip().rstrip(";")


def validate_read_only_sql(sql: str) -> str:
    """Return normalized SQL when it is safe to execute."""

    normalized = normalize_sql(sql)
    if not normalized:
        raise ValueError("The model did not return a SQL query.")
    if ";" in normalized:
        raise ValueError("Multiple SQL statements are not allowed.")
    if not re.match(r"^\s*SELECT\b", normalized, flags=re.IGNORECASE):
        raise ValueError("Only SELECT statements are allowed.")
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            raise ValueError("Unsafe SQL detected.")
    return normalized

