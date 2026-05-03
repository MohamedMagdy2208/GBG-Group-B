from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any

try:
    from neo4j.graph import Node, Path, Relationship
except Exception:  # pragma: no cover - import guard for minimal test environments
    Node = Path = Relationship = ()  # type: ignore[assignment]


def _element_id(value: Any) -> str | int | None:
    element_id = getattr(value, "element_id", None)
    if element_id is not None:
        return element_id
    legacy_id = getattr(value, "id", None)
    if legacy_id is not None:
        return legacy_id
    return None


def _looks_like_node(value: Any) -> bool:
    return isinstance(value, Node) or (
        hasattr(value, "labels")
        and hasattr(value, "items")
        and not hasattr(value, "start_node")
        and not hasattr(value, "end_node")
    )


def _looks_like_relationship(value: Any) -> bool:
    return isinstance(value, Relationship) or (
        hasattr(value, "type")
        and hasattr(value, "items")
        and hasattr(value, "start_node")
        and hasattr(value, "end_node")
    )


def _looks_like_path(value: Any) -> bool:
    return isinstance(value, Path) or (
        hasattr(value, "nodes")
        and hasattr(value, "relationships")
        and not isinstance(value, (str, bytes))
    )


def serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if _looks_like_node(value):
        return {
            "type": "node",
            "id": _element_id(value),
            "labels": sorted(str(label) for label in getattr(value, "labels", [])),
            "properties": {str(key): serialize_value(item) for key, item in dict(value).items()},
        }
    if _looks_like_relationship(value):
        return {
            "type": "relationship",
            "id": _element_id(value),
            "relationship_type": str(getattr(value, "type", "")),
            "start_node_id": _element_id(getattr(value, "start_node", None)),
            "end_node_id": _element_id(getattr(value, "end_node", None)),
            "properties": {str(key): serialize_value(item) for key, item in dict(value).items()},
        }
    if _looks_like_path(value):
        return {
            "type": "path",
            "nodes": [serialize_value(node) for node in getattr(value, "nodes", [])],
            "relationships": [
                serialize_value(rel) for rel in getattr(value, "relationships", [])
            ],
        }
    if isinstance(value, Mapping):
        return {str(key): serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize_value(item) for item in value]
    return str(value)


def serialize_record(record: Any) -> dict[str, Any]:
    if hasattr(record, "data"):
        data = record.data()
    else:
        data = dict(record)
    return {str(key): serialize_value(value) for key, value in data.items()}


def records_to_rows(records: list[Any]) -> list[dict[str, Any]]:
    return [serialize_record(record) for record in records]

