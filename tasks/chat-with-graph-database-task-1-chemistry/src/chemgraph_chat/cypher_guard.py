from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class CypherValidationError(ValueError):
    """Raised when generated Cypher is not safe for the read-only chat path."""


@dataclass(frozen=True)
class SafeCypher:
    query: str
    parameters: dict[str, Any]


BLOCKED_KEYWORDS = {
    "ALTER",
    "CALL",
    "COMMIT",
    "CREATE",
    "DELETE",
    "DETACH",
    "DROP",
    "FOREACH",
    "GRANT",
    "LOAD",
    "MERGE",
    "REMOVE",
    "RENAME",
    "REVOKE",
    "SET",
    "START",
    "STOP",
    "TERMINATE",
}

ALLOWED_START_KEYWORDS = {"MATCH", "OPTIONAL", "WITH", "UNWIND"}
READ_CLAUSES = {"MATCH", "OPTIONAL", "WHERE", "WITH", "UNWIND", "RETURN", "ORDER", "SKIP", "LIMIT", "DISTINCT", "AS", "AND", "OR", "NOT", "IN", "IS", "NULL", "TRUE", "FALSE", "CASE", "WHEN", "THEN", "ELSE", "END"}
COMMENT_MARKERS = ("//", "/*", "*/")
MAX_LIMIT = 100


def _strip_terminal_semicolon(query: str) -> str:
    stripped = query.strip()
    if stripped.endswith(";"):
        stripped = stripped[:-1].strip()
    if ";" in stripped:
        raise CypherValidationError("Only one Cypher statement is allowed.")
    return stripped


def _reject_comments(query: str) -> None:
    if any(marker in query for marker in COMMENT_MARKERS):
        raise CypherValidationError("Cypher comments are not allowed in generated queries.")


def _tokens(query: str) -> list[str]:
    return re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", query.upper())


def _validate_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(parameters, dict):
        raise CypherValidationError("Cypher parameters must be a JSON object.")

    def validate_value(value: Any, path: str) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [validate_value(item, f"{path}[]") for item in value]
        raise CypherValidationError(f"Unsupported parameter value at {path}.")

    return {str(key): validate_value(value, str(key)) for key, value in parameters.items()}


def _extract_existing_limit(query: str) -> int | None:
    matches = re.findall(r"\bLIMIT\s+(\d+)\b", query, flags=re.IGNORECASE)
    if not matches:
        return None
    return int(matches[-1])


def _enforce_limit(query: str, max_rows: int) -> str:
    safe_max = min(max(1, max_rows), MAX_LIMIT)
    existing_limit = _extract_existing_limit(query)
    if existing_limit is None:
        return f"{query} LIMIT {safe_max}"
    if existing_limit > safe_max:
        return re.sub(
            r"\bLIMIT\s+\d+\b(?!.*\bLIMIT\s+\d+\b)",
            f"LIMIT {safe_max}",
            query,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return query


def validate_readonly_cypher(
    query: str,
    parameters: dict[str, Any] | None = None,
    *,
    max_rows: int = 50,
) -> SafeCypher:
    if not isinstance(query, str) or not query.strip():
        raise CypherValidationError("Cypher query cannot be empty.")

    _reject_comments(query)
    stripped = _strip_terminal_semicolon(query)
    normalized = re.sub(r"\s+", " ", stripped).strip()
    tokens = _tokens(normalized)

    if not tokens:
        raise CypherValidationError("Cypher query cannot be empty.")
    if tokens[0] not in ALLOWED_START_KEYWORDS:
        raise CypherValidationError("Only read-only MATCH/WITH/UNWIND queries are allowed.")
    if "RETURN" not in tokens:
        raise CypherValidationError("Read-only chat queries must include RETURN.")

    blocked = sorted(set(tokens).intersection(BLOCKED_KEYWORDS))
    if blocked:
        raise CypherValidationError(f"Blocked Cypher keyword(s): {', '.join(blocked)}.")

    safe_parameters = _validate_parameters(parameters or {})
    limited_query = _enforce_limit(normalized, max_rows)
    return SafeCypher(query=limited_query, parameters=safe_parameters)

