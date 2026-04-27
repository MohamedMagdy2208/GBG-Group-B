import re

FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC)\b",
    re.IGNORECASE,
)

SQL_INJECTION_PATTERN = re.compile(
    r"\b(DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|ALTER\s+TABLE|CREATE\s+TABLE|TRUNCATE\s+TABLE)\b",
    re.IGNORECASE,
)


def validate_sql_readonly(sql: str) -> tuple[bool, str]:
    """Validate that a SQL query is read-only. Returns (is_valid, error_message)."""
    match = FORBIDDEN_SQL_KEYWORDS.search(sql)
    if match:
        return False, f"Query rejected: write operation '{match.group()}' is not allowed. This is a read-only database."
    return True, ""


def fix_unquoted_mixed_case(sql: str) -> str:
    """Fix unquoted MixedCase identifiers throughout SQL.

    Handles:
    - AS TotalSpent -> AS "TotalSpent"
    - ORDER BY TotalSpent -> ORDER BY "TotalSpent"
    - Bare MixedCase words that aren't SQL keywords
    """
    SQL_KEYWORDS = {
        "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
        "CROSS", "ON", "AND", "OR", "NOT", "IN", "AS", "BY", "ORDER", "GROUP",
        "HAVING", "LIMIT", "OFFSET", "UNION", "ALL", "DISTINCT", "CASE", "WHEN",
        "THEN", "ELSE", "END", "WITH", "RECURSIVE", "NULL", "IS", "BETWEEN",
        "LIKE", "EXISTS", "DESC", "ASC", "INTO", "VALUES", "SET", "TRUE", "FALSE",
        "OVER", "PARTITION", "WITHIN", "FILTER", "LATERAL", "COALESCE", "NULLIF",
        "CAST", "SUM", "COUNT", "AVG", "MIN", "MAX", "ROUND", "EXTRACT", "YEAR",
        "MONTH", "DAY", "DATE", "PERCENTILE_CONT",
    }

    def _fix(match):
        word = match.group(0)
        # Don't touch SQL keywords, already quoted, or all lowercase
        if word.upper() in SQL_KEYWORDS or word == word.lower():
            return word
        # Only fix MixedCase identifiers (e.g., TotalSpent, CustomerRevenue)
        if any(c.isupper() for c in word[1:]) or word[0].isupper():
            return f'"{word}"'
        return word

    # Match unquoted identifiers: word boundary, not preceded by " or .
    # Avoid double-quoting already quoted identifiers
    result = re.sub(
        r'(?<!")(?<!\.)(?<!\w)([A-Z][A-Za-z0-9_]*[a-z][A-Za-z0-9_]*)(?!")',
        _fix,
        sql,
    )
    # Clean up any double-double-quotes from edge cases
    result = result.replace('""', '"')
    return result


def fix_round_cast(sql: str) -> str:
    """Fix PostgreSQL ROUND(double precision, int) error by adding ::numeric cast."""
    # Match ROUND(..., N) where the first arg is NOT already cast to numeric
    def _fix_round(match):
        expr = match.group(1)
        precision = match.group(2)
        # If already has ::numeric at the end, leave it alone
        if expr.rstrip().endswith("::numeric"):
            return match.group(0)
        return f"ROUND(({expr})::numeric, {precision})"

    return re.sub(
        r"ROUND\((.+?),\s*(\d+)\)",
        _fix_round,
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )


def clean_sql(raw: str) -> str:
    """Clean LLM output to extract the SQL query."""
    sql = raw.replace("```sql", "").replace("```", "").strip()
    if sql.upper().startswith("SQLQUERY:"):
        sql = sql[9:].strip()
    if sql.upper().startswith("SQL:"):
        sql = sql[4:].strip()
    sql = fix_unquoted_mixed_case(sql)
    sql = fix_round_cast(sql)
    return sql


def validate_question(question: str, max_length: int = 500) -> tuple[bool, str]:
    """Validate user input. Returns (is_valid, error_message)."""
    if not question or not question.strip():
        return False, "Please enter a question."
    if len(question) > max_length:
        return False, f"Question is too long ({len(question)} chars). Maximum is {max_length} characters."
    if SQL_INJECTION_PATTERN.search(question):
        return False, "Your question contains SQL-like syntax that is not allowed. Please rephrase using natural language."
    return True, ""
