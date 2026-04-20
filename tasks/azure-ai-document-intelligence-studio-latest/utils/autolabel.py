"""Convert Azure analysis fields into editable label suggestions."""

from __future__ import annotations

import json
import re
from typing import Any


VALUE_PREFIXES = ("value", "value_")


def normalize_field_key(value: str) -> str:
    """Normalize field names for best-effort matching."""

    return re.sub(r"[^a-z0-9]+", "", value.lower())


def match_project_field(source_field: str, project_fields: list[str]) -> str:
    """Return the closest exact-normalized project field for a source field."""

    source = normalize_field_key(source_field)
    for field in project_fields:
        if normalize_field_key(field) == source:
            return field
    return source_field


def extract_autolabel_suggestions(
    result: dict[str, Any],
    *,
    confidence_threshold: float = 0.0,
) -> list[dict[str, Any]]:
    """Return editable label suggestions from an Azure analysis result."""

    if not result or "error" in result:
        return []

    pages = _page_lookup(result.get("pages", []) or [])
    suggestions: list[dict[str, Any]] = []
    for document in result.get("documents", []) or []:
        fields = document.get("fields", {}) or {}
        suggestions.extend(
            _walk_fields(
                fields,
                pages=pages,
                confidence_threshold=confidence_threshold,
            )
        )
    return suggestions


def suggestion_to_annotation(
    suggestion: dict[str, Any],
    target_label: str,
) -> dict[str, Any]:
    """Convert one accepted suggestion into a stored annotation."""

    return {
        "label": target_label.strip(),
        "value": str(suggestion.get("value", "")).strip(),
        "bbox": suggestion["bbox"],
        "page": suggestion.get("page", 1),
        "page_width": suggestion.get("page_width", 1),
        "page_height": suggestion.get("page_height", 1),
        "confidence": suggestion.get("confidence", ""),
        "source_field": suggestion.get("source_field", ""),
        "source_model": suggestion.get("source_model", ""),
    }


def _walk_fields(
    fields: dict[str, Any],
    *,
    pages: dict[int, dict[str, Any]],
    confidence_threshold: float,
    parent: str = "",
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for field_name, field in fields.items():
        path = f"{parent}.{field_name}" if parent else field_name
        if not isinstance(field, dict):
            continue

        child_fields = _child_fields(field)
        array_items = _array_items(field)
        if child_fields:
            suggestions.extend(
                _walk_fields(
                    child_fields,
                    pages=pages,
                    confidence_threshold=confidence_threshold,
                    parent=path,
                )
            )

        for idx, item in enumerate(array_items, start=1):
            item_path = f"{path}[{idx}]"
            if isinstance(item, dict):
                item_children = _child_fields(item)
                if item_children:
                    suggestions.extend(
                        _walk_fields(
                            item_children,
                            pages=pages,
                            confidence_threshold=confidence_threshold,
                            parent=item_path,
                        )
                    )
                else:
                    suggestions.extend(
                        _field_suggestions(
                            item_path,
                            item,
                            pages=pages,
                            confidence_threshold=confidence_threshold,
                        )
                    )

        if not child_fields and not array_items:
            suggestions.extend(
                _field_suggestions(
                    path,
                    field,
                    pages=pages,
                    confidence_threshold=confidence_threshold,
                )
            )
    return suggestions


def _field_suggestions(
    source_field: str,
    field: dict[str, Any],
    *,
    pages: dict[int, dict[str, Any]],
    confidence_threshold: float,
) -> list[dict[str, Any]]:
    confidence = field.get("confidence")
    if confidence is not None and float(confidence) < confidence_threshold:
        return []

    value = _field_value(field)
    if not value:
        return []

    suggestions = []
    for region in _field_regions(field):
        bbox = _region_bbox(region)
        if not bbox:
            continue
        page_number = int(region.get("pageNumber") or region.get("page_number") or 1)
        page = pages.get(page_number, {})
        page_width = float(page.get("width") or max(bbox[0] + bbox[2], 1.0))
        page_height = float(page.get("height") or max(bbox[1] + bbox[3], 1.0))
        suggestions.append(
            {
                "source_field": source_field,
                "target_label": source_field,
                "value": value,
                "confidence": confidence if confidence is not None else "",
                "page": page_number,
                "bbox": bbox,
                "page_width": page_width,
                "page_height": page_height,
            }
        )
    return suggestions


def _field_value(field: dict[str, Any]) -> str:
    content = str(field.get("content", "")).strip()
    if content:
        return content

    for key, value in field.items():
        if key in {"valueArray", "value_array", "valueObject", "value_object"}:
            continue
        if not key.startswith(VALUE_PREFIXES):
            continue
        if value is None:
            continue
        if isinstance(value, dict):
            if "amount" in value:
                currency = value.get("currencyCode") or value.get("currency_code") or ""
                return f"{value['amount']} {currency}".strip()
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, list):
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _field_regions(field: dict[str, Any]) -> list[dict[str, Any]]:
    return field.get("boundingRegions") or field.get("bounding_regions") or []


def _child_fields(field: dict[str, Any]) -> dict[str, Any]:
    value_object = field.get("valueObject") or field.get("value_object")
    if isinstance(value_object, dict):
        return value_object
    return {}


def _array_items(field: dict[str, Any]) -> list[Any]:
    value_array = field.get("valueArray") or field.get("value_array")
    return value_array if isinstance(value_array, list) else []


def _region_bbox(region: dict[str, Any]) -> list[float] | None:
    polygon = region.get("polygon") or region.get("boundingBox") or region.get("bounding_box")
    if not polygon:
        return None

    points = _polygon_points(polygon)
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    width = x2 - x1
    height = y2 - y1
    if width <= 0 or height <= 0:
        return None
    return [x1, y1, width, height]


def _polygon_points(polygon: list[Any]) -> list[tuple[float, float]]:
    if not polygon:
        return []
    if all(isinstance(value, (int, float)) for value in polygon):
        return [
            (float(polygon[idx]), float(polygon[idx + 1]))
            for idx in range(0, len(polygon) - 1, 2)
        ]
    points = []
    for point in polygon:
        if isinstance(point, dict):
            x = point.get("x")
            y = point.get("y")
            if x is not None and y is not None:
                points.append((float(x), float(y)))
    return points


def _page_lookup(pages: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    lookup = {}
    for page in pages:
        page_number = page.get("pageNumber") or page.get("page_number")
        if page_number is not None:
            lookup[int(page_number)] = page
    return lookup
