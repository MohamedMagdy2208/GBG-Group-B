"""Helpers for Azure-compatible custom model training artifacts."""

from __future__ import annotations

import re
from typing import Any


FIELDS_SCHEMA = "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/fields.json"
LABELS_SCHEMA = "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/labels.json"


def safe_project_id(name: str) -> str:
    """Return a blob-prefix-safe project id."""

    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip("-")
    return cleaned or "document-intelligence-project"


def sanitize_fields(fields: list[str]) -> list[str]:
    """Return unique, non-empty field names in user order."""

    cleaned = []
    seen = set()
    for field in fields:
        value = field.strip()
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)
    return cleaned


def generate_fields_json(fields: list[str]) -> dict[str, Any]:
    """Generate the fields.json document used by Studio-labeled datasets."""

    return {
        "$schema": FIELDS_SCHEMA,
        "fields": [
            {
                "fieldKey": field,
                "fieldType": "string",
                "fieldFormat": "not-specified",
            }
            for field in sanitize_fields(fields)
        ],
        "definitions": {},
    }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def bbox_to_normalized_polygon(
    bbox: list[float],
    page_width: float,
    page_height: float,
) -> list[float]:
    """Convert [x, y, width, height] to a normalized 8-number polygon."""

    x, y, width, height = [float(v) for v in bbox[:4]]
    if page_width <= 0 or page_height <= 0:
        raise ValueError("Page width and height are required for label export.")
    x1 = _clamp(x / page_width)
    y1 = _clamp(y / page_height)
    x2 = _clamp((x + width) / page_width)
    y2 = _clamp((y + height) / page_height)
    return [x1, y1, x2, y1, x2, y2, x1, y2]


def generate_labels_json(
    file_name: str,
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a region-label .labels.json document for one source file."""

    labels = []
    for annotation in annotations:
        label = str(annotation.get("label", "")).strip()
        value = str(annotation.get("value", "")).strip()
        bbox = annotation.get("bbox") or []
        if not label or not value or len(bbox) < 4:
            continue

        page_width = float(annotation.get("page_width") or annotation.get("image_width") or 0)
        page_height = float(
            annotation.get("page_height") or annotation.get("image_height") or 0
        )
        if not page_width or not page_height:
            x, y, width, height = [float(v) for v in bbox[:4]]
            page_width = max(x + width, 1.0)
            page_height = max(y + height, 1.0)

        labels.append(
            {
                "label": label,
                "value": [
                    {
                        "page": int(annotation.get("page", 1)),
                        "text": value,
                        "boundingBoxes": [
                            bbox_to_normalized_polygon(bbox, page_width, page_height)
                        ],
                    }
                ],
                "labelType": "region",
            }
        )

    return {"$schema": LABELS_SCHEMA, "document": file_name, "labels": labels}


def prepare_training_assets(
    *,
    blob_prefix: str,
    uploaded_files: list[Any],
    fields: list[str],
    layout_results: dict[str, dict[str, Any]],
    annotations_by_file: dict[str, list[dict[str, Any]]],
) -> list[tuple[str, bytes | dict[str, Any], str]]:
    """Build blob upload payloads for a labeled custom extraction dataset."""

    prefix = blob_prefix.strip("/")
    assets: list[tuple[str, bytes | dict[str, Any], str]] = [
        (f"{prefix}/fields.json", generate_fields_json(fields), "application/json")
    ]

    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        assets.append((f"{prefix}/{file_name}", file_bytes, uploaded_file.type or "application/octet-stream"))
        assets.append(
            (
                f"{prefix}/{file_name}.ocr.json",
                layout_results.get(file_name, {}),
                "application/json",
            )
        )
        assets.append(
            (
                f"{prefix}/{file_name}.labels.json",
                generate_labels_json(file_name, annotations_by_file.get(file_name, [])),
                "application/json",
            )
        )
    return assets


def validate_training_inputs(
    uploaded_files: list[Any],
    fields: list[str],
    annotations_by_file: dict[str, list[dict[str, Any]]],
    layout_results: dict[str, dict[str, Any]],
) -> list[str]:
    """Return human-readable training blockers."""

    errors = []
    if len(uploaded_files) < 5:
        errors.append("Upload at least 5 documents.")
    if not sanitize_fields(fields):
        errors.append("Add at least one field.")
    for uploaded_file in uploaded_files:
        name = uploaded_file.name
        if "error" in layout_results.get(name, {}):
            errors.append(f"Layout analysis failed for {name}.")
        if not layout_results.get(name):
            errors.append(f"Run layout analysis for {name}.")
        annotations = annotations_by_file.get(name, [])
        if not annotations:
            errors.append(f"Add at least one annotation for {name}.")
            continue
        if any(not str(annotation.get("label", "")).strip() for annotation in annotations):
            errors.append(f"Every annotation for {name} needs a field label.")
        if any(not str(annotation.get("value", "")).strip() for annotation in annotations):
            errors.append(f"Every annotation for {name} needs a text value.")
    return errors
