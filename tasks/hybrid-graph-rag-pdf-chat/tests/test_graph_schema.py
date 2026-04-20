from __future__ import annotations

from app.services.graph_store import SCHEMA_PATH, load_cypher_statements


def test_neo4j_schema_file_contains_core_constraints_and_indexes():
    statements = load_cypher_statements(SCHEMA_PATH)
    joined = "\n".join(statements)

    assert "document_id_unique" in joined
    assert "chunk_id_unique" in joined
    assert "entity_id_unique" in joined
    assert "entity_fulltext_index" in joined
    assert all(statement.endswith(";") is False for statement in statements)

