"""Persist and query local user annotations."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
JSON_PATH = DATA_DIR / "annotations.json"
CSV_PATH = DATA_DIR / "annotations.csv"

CSV_COLUMNS = [
    "file_name",
    "label",
    "value",
    "page",
    "x",
    "y",
    "width",
    "height",
    "page_width",
    "page_height",
]


def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


def _write_json(all_data: list[dict[str, Any]]):
    _ensure_data_dir()
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)


def _validate_annotations(annotations: list[dict[str, Any]]):
    for idx, annotation in enumerate(annotations, start=1):
        if not str(annotation.get("label", "")).strip():
            raise ValueError(f"Annotation {idx} is missing a field label.")
        if not str(annotation.get("value", "")).strip():
            raise ValueError(f"Annotation {idx} is missing a text value.")


def _rebuild_csv(all_data: list[dict[str, Any]]):
    rows = []
    for file_entry in all_data:
        file_name = file_entry.get("file_name", "")
        for annotation in file_entry.get("annotations", []):
            bbox = annotation.get("bbox", [0, 0, 0, 0])
            rows.append(
                {
                    "file_name": file_name,
                    "label": annotation.get("label", ""),
                    "value": annotation.get("value", ""),
                    "page": annotation.get("page", 1),
                    "x": bbox[0] if len(bbox) > 0 else 0,
                    "y": bbox[1] if len(bbox) > 1 else 0,
                    "width": bbox[2] if len(bbox) > 2 else 0,
                    "height": bbox[3] if len(bbox) > 3 else 0,
                    "page_width": annotation.get("page_width", ""),
                    "page_height": annotation.get("page_height", ""),
                }
            )

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def load_all_annotations() -> list[dict[str, Any]]:
    """Return all stored annotations as a list of file annotation records."""

    _ensure_data_dir()
    if not JSON_PATH.exists():
        return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def save_annotations(file_name: str, annotations: list[dict[str, Any]]):
    """Save/update annotations for a specific file."""

    _validate_annotations(annotations)
    all_data = load_all_annotations()
    all_data = [d for d in all_data if d.get("file_name") != file_name]
    all_data.append({"file_name": file_name, "annotations": annotations})
    _write_json(all_data)
    _rebuild_csv(all_data)


def get_annotations_for_file(file_name: str) -> list[dict[str, Any]]:
    """Return annotations for a specific file, or an empty list."""

    for entry in load_all_annotations():
        if entry.get("file_name") == file_name:
            return entry.get("annotations", [])
    return []


def load_as_dataframe() -> pd.DataFrame:
    """Return all annotations as a flat dataframe."""

    _ensure_data_dir()
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=CSV_COLUMNS)
    return pd.read_csv(CSV_PATH)


def delete_annotations(file_name: str):
    """Remove all annotations for a file and keep CSV in sync."""

    all_data = [d for d in load_all_annotations() if d.get("file_name") != file_name]
    _write_json(all_data)
    _rebuild_csv(all_data)
