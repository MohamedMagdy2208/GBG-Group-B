from __future__ import annotations

import pytest

from chemgraph_chat.cypher_guard import CypherValidationError, validate_readonly_cypher


def test_accepts_readonly_query_and_adds_limit() -> None:
    safe = validate_readonly_cypher(
        "MATCH (d:Drug)-[:TREATS]->(disease:Disease) RETURN d.name AS drug",
        max_rows=25,
    )

    assert safe.query.endswith("LIMIT 25")
    assert safe.parameters == {}


def test_accepts_case_insensitive_string_filter() -> None:
    safe = validate_readonly_cypher(
        "MATCH (d:Drug)-[:TREATS]->(dis:Disease)-[:AFFECTS]->(o:Organism) "
        "WHERE toLower(o.type) = toLower($organismType) "
        "RETURN d.name AS drugName, dis.name AS diseaseName",
        {"organismType": "human"},
        max_rows=50,
    )

    assert "toLower(o.type)" in safe.query
    assert safe.query.endswith("LIMIT 50")
    assert safe.parameters == {"organismType": "human"}


def test_preserves_small_existing_limit() -> None:
    safe = validate_readonly_cypher(
        "MATCH (n) RETURN n LIMIT 3",
        max_rows=10,
    )

    assert safe.query == "MATCH (n) RETURN n LIMIT 3"


def test_caps_large_existing_limit() -> None:
    safe = validate_readonly_cypher(
        "MATCH (n) RETURN n LIMIT 500",
        max_rows=40,
    )

    assert safe.query == "MATCH (n) RETURN n LIMIT 40"


@pytest.mark.parametrize(
    "query",
    [
        "CREATE (:Drug {name: 'Bad'}) RETURN 1",
        "MATCH (n) SET n.name = 'x' RETURN n",
        "MATCH (n) DELETE n RETURN n",
        "MATCH (n) RETURN n; MATCH (m) RETURN m",
        "MATCH (n) RETURN n // CREATE (:Bad)",
        "MATCH (n) RETURN n /* hidden */",
        "CALL db.labels() YIELD label RETURN label",
        "LOAD CSV FROM 'file:///x.csv' AS row RETURN row",
    ],
)
def test_blocks_unsafe_queries(query: str) -> None:
    with pytest.raises(CypherValidationError):
        validate_readonly_cypher(query)


def test_requires_return_clause() -> None:
    with pytest.raises(CypherValidationError):
        validate_readonly_cypher("MATCH (n)")


def test_rejects_complex_parameter_values() -> None:
    with pytest.raises(CypherValidationError):
        validate_readonly_cypher(
            "MATCH (n {name: $name}) RETURN n",
            {"name": {"nested": "bad"}},
        )
