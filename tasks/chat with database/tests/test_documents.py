"""Tests for retrieval document generation."""

from src.retrieval.documents import build_all_documents


def test_build_all_documents_includes_schema_and_examples() -> None:
    schema_snapshot = [
        {
            "table": "Customer",
            "columns": [{"name": "CustomerId", "type": "INTEGER", "nullable": False, "default": None}],
            "foreign_keys": [],
        }
    ]
    documents = build_all_documents(schema_snapshot)
    assert any(document.kind == "schema" for document in documents)
    assert any(document.kind == "example" for document in documents)

