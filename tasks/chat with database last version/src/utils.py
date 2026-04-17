import re

FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b("
    r"ALTER|ANALYZE|CALL|COMMENT|COPY|CREATE|DELETE|DO|DROP|EXEC|EXECUTE|"
    r"GRANT|INSERT|LOCK|MERGE|REFRESH|REINDEX|RESET|REVOKE|SET|TRUNCATE|"
    r"UPDATE|VACUUM"
    r")\b",
    re.IGNORECASE,
)

SELECT_INTO_PATTERN = re.compile(
    r"\bSELECT\b[\s\S]*\bINTO\b",
    re.IGNORECASE,
)

READONLY_START_PATTERN = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)

SQL_INJECTION_PATTERN = re.compile(
    r"\b(DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|ALTER\s+TABLE|CREATE\s+TABLE|TRUNCATE\s+TABLE)\b",
    re.IGNORECASE,
)


def _strip_sql_literals_and_comments(sql: str) -> str:
    """Return SQL with strings, quoted identifiers, and comments blanked out."""
    result = []
    i = 0
    length = len(sql)

    while i < length:
        char = sql[i]
        nxt = sql[i:i + 2]

        if nxt == "--":
            end = sql.find("\n", i + 2)
            if end == -1:
                result.append(" ")
                break
            result.append(" ")
            i = end
            continue

        if nxt == "/*":
            end = sql.find("*/", i + 2)
            result.append(" ")
            i = length if end == -1 else end + 2
            continue

        if char in {"'", '"'}:
            quote = char
            i += 1
            while i < length:
                if sql[i] == quote:
                    if i + 1 < length and sql[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            result.append(" ")
            continue

        if char == "$":
            tag = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[i:])
            if tag:
                token = tag.group(0)
                end = sql.find(token, i + len(token))
                result.append(" ")
                i = length if end == -1 else end + len(token)
                continue

        result.append(char)
        i += 1

    return "".join(result)


def _transform_outside_single_quotes(sql: str, transform) -> str:
    result = []
    i = 0
    length = len(sql)

    while i < length:
        if sql[i] != "'":
            start = i
            while i < length and sql[i] != "'":
                i += 1
            result.append(transform(sql[start:i]))
            continue

        start = i
        i += 1
        while i < length:
            if sql[i] == "'":
                if i + 1 < length and sql[i + 1] == "'":
                    i += 2
                    continue
                i += 1
                break
            i += 1
        result.append(sql[start:i])

    return "".join(result)


def _has_top_level_keyword(sql: str, keywords: set[str]) -> bool:
    normalized = _strip_sql_literals_and_comments(sql)
    depth = 0
    for match in re.finditer(r"\(|\)|\b[A-Za-z_][A-Za-z0-9_]*\b", normalized):
        token = match.group(0)
        if token == "(":
            depth += 1
            continue
        if token == ")":
            depth = max(0, depth - 1)
            continue
        if depth == 0 and token.upper() in keywords:
            return True
    return False


def ensure_sql_limit(sql: str, limit: int) -> str:
    """Add a top-level LIMIT to generated SQL when the model omitted one."""
    sql = sql.strip()
    if not sql:
        return sql
    if limit <= 0 or _has_top_level_keyword(sql, {"LIMIT", "FETCH"}):
        return sql
    normalized = _strip_sql_literals_and_comments(sql)
    if not _has_top_level_keyword(sql, {"FROM"}):
        return sql
    if (
        re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", normalized, re.IGNORECASE)
        and not _has_top_level_keyword(sql, {"GROUP"})
    ):
        return sql

    semicolon = ";" if sql.endswith(";") else ""
    base_sql = sql[:-1].rstrip() if semicolon else sql
    return f"{base_sql}\nLIMIT {limit}{semicolon}"


def validate_sql_readonly(sql: str) -> tuple[bool, str]:
    """Validate that a SQL query is read-only. Returns (is_valid, error_message)."""
    normalized = _strip_sql_literals_and_comments(sql).strip()

    if not normalized:
        return False, "Query rejected: empty SQL is not allowed."

    without_trailing_semicolon = normalized.rstrip("; \t\r\n")
    if ";" in without_trailing_semicolon:
        return False, "Query rejected: multiple SQL statements are not allowed."

    if not READONLY_START_PATTERN.search(normalized):
        return False, "Query rejected: only SELECT queries are allowed."

    select_into = SELECT_INTO_PATTERN.search(normalized)
    if select_into:
        return False, "Query rejected: SELECT INTO is not allowed. This is a read-only database."

    match = FORBIDDEN_SQL_KEYWORDS.search(normalized)
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

    def _fix_chunk(chunk):
        # Match unquoted identifiers: word boundary, not preceded by " or .
        # Avoid double-quoting already quoted identifiers.
        chunk = re.sub(
            r'(?<!")\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Z][A-Za-z0-9_]*[a-z][A-Za-z0-9_]*)(?!")',
            lambda match: (
                match.group(0)
                if match.group(2).upper() in SQL_KEYWORDS
                else f'{match.group(1)}."{match.group(2)}"'
            ),
            chunk,
        )
        return re.sub(
            r'(?<!")(?<!\.)(?<!\w)([A-Z][A-Za-z0-9_]*[a-z][A-Za-z0-9_]*)(?!")',
            _fix,
            chunk,
        )

    result = _transform_outside_single_quotes(sql, _fix_chunk)
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
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", raw, flags=re.IGNORECASE | re.DOTALL)
    sql = fenced.group(1).strip() if fenced else raw.strip()
    if sql.upper().startswith("SQLQUERY:"):
        sql = sql[9:].strip()
    if sql.upper().startswith("SQL:"):
        sql = sql[4:].strip()
    start = re.search(r"\b(SELECT|WITH)\b", sql, flags=re.IGNORECASE)
    if start:
        sql = sql[start.start():].strip()
    sql = fix_unquoted_mixed_case(sql)
    sql = fix_round_cast(sql)
    return sql.strip()


def validate_question(question: str, max_length: int = 500) -> tuple[bool, str]:
    """Validate user input. Returns (is_valid, error_message)."""
    if not question or not question.strip():
        return False, "Please enter a question."
    if len(question) > max_length:
        return False, f"Question is too long ({len(question)} chars). Maximum is {max_length} characters."
    if SQL_INJECTION_PATTERN.search(question):
        return False, "Your question contains SQL-like syntax that is not allowed. Please rephrase using natural language."
    return True, ""
