from __future__ import annotations

import os

import pytest

from chemgraph_chat.config import load_settings
from chemgraph_chat.db import create_driver, run_read_query, verify_connectivity
from chemgraph_chat.seed import load_seed_statements, run_seed


def test_seed_file_contains_idempotent_statements() -> None:
    statements = load_seed_statements()

    assert statements
    assert all("CREATE " not in statement.upper() for statement in statements)
    assert any("Aspirin" in statement for statement in statements)


@pytest.mark.skipif(
    not all(os.getenv(name) for name in ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"]),
    reason="Neo4j environment variables are not configured.",
)
def test_seed_smoke_against_configured_neo4j() -> None:
    settings = load_settings(require_openai=False)
    driver = create_driver(settings)
    try:
        verify_connectivity(driver, settings.neo4j_database)
        assert run_seed(driver, settings.neo4j_database) > 0
        rows = run_read_query(
            driver,
            settings.neo4j_database,
            "MATCH (:Drug {name: 'Aspirin'})-[:TREATS]->(:Disease {name: 'Headache'}) RETURN count(*) AS count",
        )
        assert rows[0]["count"] >= 1
    finally:
        driver.close()

