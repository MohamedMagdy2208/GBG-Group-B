"""Unit tests for SQL safety validation."""

import pytest

from src.config.settings import Settings
from src.database.client import DatabaseManager
from src.services.rag_pipeline import ChatWithDatabaseService
from src.services.sql_validator import normalize_sql, validate_read_only_sql


def test_normalize_sql_removes_trailing_semicolon() -> None:
    assert normalize_sql("SELECT 1;") == "SELECT 1"


def test_validate_read_only_sql_accepts_select() -> None:
    assert validate_read_only_sql("SELECT * FROM customers") == "SELECT * FROM customers"


def test_validate_read_only_sql_rejects_multiple_statements() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("SELECT 1; SELECT 2")


def test_validate_read_only_sql_rejects_mutation() -> None:
    with pytest.raises(ValueError):
        validate_read_only_sql("DELETE FROM customers")


def test_execute_query_limit_detection_handles_existing_limit() -> None:
    settings = Settings.model_validate(
        {
            "DATABASE_URL": "sqlite:///:memory:",
        }
    )
    db = DatabaseManager(settings)
    sql = 'SELECT 1 AS value\nLIMIT 5'
    rows = db.execute_query(sql, limit=50)
    assert rows == [{"value": 1}]


def test_extract_clarification_request_ignores_none_sentence_when_sql_exists() -> None:
    result = ChatWithDatabaseService._extract_clarification_request(
        "None. The user request is clear and specifies the playlist ID and the number of tracks to display.",
        sql='SELECT t."Name" FROM "Track" t LIMIT 5',
    )
    assert result is None
