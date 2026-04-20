from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import neo4j


def _flatten_keys(key_lists: Iterable[Any]) -> list[str]:
    keys: set[str] = set()
    for key_list in key_lists or []:
        if isinstance(key_list, list):
            for key in key_list:
                keys.add(str(key))
    return sorted(keys)


def _format_sample_values(values: Iterable[Any]) -> str:
    formatted: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if len(text) > 60:
            text = f"{text[:57]}..."
        formatted.append(text)
    return ", ".join(formatted)


def get_schema_summary(driver: neo4j.Driver, database: str) -> str:
    node_query = """
    MATCH (n)
    UNWIND labels(n) AS label
    RETURN label, collect(DISTINCT keys(n)) AS key_lists
    ORDER BY label
    """
    relationship_query = """
    MATCH ()-[r]->()
    RETURN type(r) AS relationship_type, collect(DISTINCT keys(r)) AS key_lists
    ORDER BY relationship_type
    """
    pattern_query = """
    MATCH (a)-[r]->(b)
    RETURN DISTINCT labels(a) AS start_labels,
           type(r) AS relationship_type,
           labels(b) AS end_labels
    ORDER BY relationship_type
    """
    sample_values_query = """
    MATCH (n)
    UNWIND labels(n) AS label
    UNWIND keys(n) AS property
    WITH label, property, collect(DISTINCT n[property]) AS values
    RETURN label, property, values[..8] AS sample_values
    ORDER BY label, property
    """

    with driver.session(database=database, default_access_mode=neo4j.READ_ACCESS) as session:
        node_rows = session.execute_read(
            lambda tx: [record.data() for record in tx.run(node_query)]
        )
        rel_rows = session.execute_read(
            lambda tx: [record.data() for record in tx.run(relationship_query)]
        )
        pattern_rows = session.execute_read(
            lambda tx: [record.data() for record in tx.run(pattern_query)]
        )
        sample_value_rows = session.execute_read(
            lambda tx: [record.data() for record in tx.run(sample_values_query)]
        )

    lines = [
        "Neo4j chemistry graph schema.",
        "Node labels and properties:",
    ]
    if node_rows:
        for row in node_rows:
            props = ", ".join(_flatten_keys(row.get("key_lists", []))) or "no properties"
            lines.append(f"- {row['label']}: {props}")
    else:
        lines.append("- No nodes found.")

    lines.append("Relationship types and properties:")
    if rel_rows:
        for row in rel_rows:
            props = ", ".join(_flatten_keys(row.get("key_lists", []))) or "no properties"
            lines.append(f"- {row['relationship_type']}: {props}")
    else:
        lines.append("- No relationships found.")

    lines.append("Observed relationship patterns:")
    if pattern_rows:
        for row in pattern_rows:
            start = ":".join(row.get("start_labels", [])) or "Node"
            end = ":".join(row.get("end_labels", [])) or "Node"
            rel_type = row.get("relationship_type", "RELATES_TO")
            lines.append(f"- ({start})-[:{rel_type}]->({end})")
    else:
        lines.append("- No relationship patterns found.")

    lines.append("Sample node property values; Neo4j string matching is case-sensitive:")
    if sample_value_rows:
        for row in sample_value_rows:
            values = _format_sample_values(row.get("sample_values", []))
            if values:
                lines.append(f"- {row['label']}.{row['property']}: {values}")
    else:
        lines.append("- No sample values found.")

    return "\n".join(lines)
