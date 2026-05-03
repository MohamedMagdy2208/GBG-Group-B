"""Format Azure Document Intelligence results for Streamlit tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

APP_METADATA_KEYS = {"file_name"}
OPERATION_METADATA_KEYS = {
    "status",
    "createdDateTime",
    "created_date_time",
    "lastUpdatedDateTime",
    "last_updated_date_time",
}


def _flatten_dict(d: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    items: dict[str, Any] = {}
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(_flatten_dict(value, new_key, sep))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    items.update(_flatten_dict(item, f"{new_key}[{idx}]", sep))
                else:
                    items[f"{new_key}[{idx}]"] = item
        else:
            items[new_key] = value
    return items


def _snake_to_camel(value: str) -> str:
    if "_" not in value:
        return value
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _to_azure_wire_shape(value: Any) -> Any:
    if isinstance(value, list):
        return [_to_azure_wire_shape(item) for item in value]
    if not isinstance(value, dict):
        return value

    converted: dict[str, Any] = {}
    for key, item in value.items():
        wire_key = _snake_to_camel(str(key))
        if wire_key == "fields" and isinstance(item, dict):
            converted[wire_key] = {
                field_key: _to_azure_wire_shape(field_value)
                for field_key, field_value in item.items()
            }
        else:
            converted[wire_key] = _to_azure_wire_shape(item)
    return converted


def to_azure_studio_json(result: dict[str, Any]) -> dict[str, Any]:
    """Return a REST/Studio-style JSON payload for display and download."""

    if "analyzeResult" in result or "analyze_result" in result:
        return _to_azure_wire_shape(result)

    payload: dict[str, Any] = {"status": result.get("status", "succeeded")}
    created = result.get("createdDateTime") or result.get("created_date_time")
    updated = result.get("lastUpdatedDateTime") or result.get("last_updated_date_time")
    if created:
        payload["createdDateTime"] = created
    if updated:
        payload["lastUpdatedDateTime"] = updated

    analyze_result = {
        key: value
        for key, value in result.items()
        if key not in APP_METADATA_KEYS and key not in OPERATION_METADATA_KEYS
    }
    payload["analyzeResult"] = _to_azure_wire_shape(analyze_result)
    return payload


def _page_from_bounding_regions(field: dict[str, Any]) -> str:
    regions = field.get("boundingRegions") or field.get("bounding_regions") or []
    pages = []
    for region in regions:
        page = region.get("pageNumber") or region.get("page_number")
        if page is not None:
            pages.append(str(page))
    return ", ".join(pages)


def fields_to_dataframe(result: dict[str, Any]) -> pd.DataFrame:
    """Return one row per extracted document field."""

    rows = []
    for doc_idx, document in enumerate(result.get("documents", []) or []):
        fields = document.get("fields", {}) or {}
        for field_name, field in fields.items():
            if not isinstance(field, dict):
                rows.append(
                    {
                        "Document": doc_idx + 1,
                        "Field": field_name,
                        "Type": "",
                        "Content": field,
                        "Value": field,
                        "Confidence": "",
                        "Page": "",
                    }
                )
                continue
            value_keys = [key for key in field.keys() if key.startswith("value")]
            value = field.get(value_keys[0], "") if value_keys else ""
            rows.append(
                {
                    "Document": doc_idx + 1,
                    "Field": field_name,
                    "Type": field.get("type", ""),
                    "Content": field.get("content", ""),
                    "Value": value,
                    "Confidence": field.get("confidence", ""),
                    "Page": _page_from_bounding_regions(field),
                }
            )
    return pd.DataFrame(rows)


def pages_to_dataframe(result: dict[str, Any]) -> pd.DataFrame:
    """Return line/word/selection mark rows from pages."""

    rows = []
    for page in result.get("pages", []) or []:
        page_num = page.get("pageNumber") or page.get("page_number") or ""
        for line in page.get("lines", []) or []:
            rows.append(
                {
                    "Page": page_num,
                    "Type": "Line",
                    "Content": line.get("content", ""),
                    "Confidence": "",
                }
            )
        for word in page.get("words", []) or []:
            rows.append(
                {
                    "Page": page_num,
                    "Type": "Word",
                    "Content": word.get("content", ""),
                    "Confidence": word.get("confidence", ""),
                }
            )
        for mark in page.get("selectionMarks", []) or page.get("selection_marks", []) or []:
            rows.append(
                {
                    "Page": page_num,
                    "Type": "Selection Mark",
                    "Content": mark.get("state", ""),
                    "Confidence": mark.get("confidence", ""),
                }
            )
    return pd.DataFrame(rows)


def tables_to_dataframes(result: dict[str, Any]) -> list[tuple[str, pd.DataFrame]]:
    """Return each extracted table as a dataframe."""

    dataframes = []
    for table_idx, table in enumerate(result.get("tables", []) or []):
        row_count = table.get("rowCount") or table.get("row_count") or 0
        col_count = table.get("columnCount") or table.get("column_count") or 0
        if not row_count or not col_count:
            continue

        grid = [["" for _ in range(col_count)] for _ in range(row_count)]
        for cell in table.get("cells", []) or []:
            row = cell.get("rowIndex", cell.get("row_index", 0))
            col = cell.get("columnIndex", cell.get("column_index", 0))
            if row < row_count and col < col_count:
                grid[row][col] = cell.get("content", "")

        columns = [f"Column {idx + 1}" for idx in range(col_count)]
        if grid and any(grid[0]):
            columns = [
                value if value else f"Column {idx + 1}"
                for idx, value in enumerate(grid[0])
            ]
            body = grid[1:]
        else:
            body = grid
        dataframes.append((f"Table {table_idx + 1}", pd.DataFrame(body, columns=columns)))
    return dataframes


def result_to_dataframe(result: dict[str, Any], model_id: str = "") -> pd.DataFrame | None:
    """Return the most useful flat table for downloads."""

    if not result or "error" in result:
        return None

    fields_df = fields_to_dataframe(result)
    if not fields_df.empty:
        return fields_df

    page_df = pages_to_dataframe(result)
    if not page_df.empty:
        return page_df

    flat = _flatten_dict(result)
    return pd.DataFrame(list(flat.items()), columns=["Field", "Value"])
