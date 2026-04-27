"""
Processor service — Azure Document Intelligence API calls.

Integrates:
  - OCR / Read     (prebuilt-read)
  - Layout Analysis (prebuilt-layout)
  - General Documents, Invoices, Receipts — same base call, different model ID
  - Custom Model   — multi-file, user-supplied model ID

All functions return a plain dict so the results component can render it.
"""

import base64
import numpy as np
import streamlit as st

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest


# ── Model name → Azure model ID mapping ────────────────────────────────────────
MODEL_MAP = {
    "OCR / Read":        "prebuilt-read",
    "Layout Analysis":   "prebuilt-layout",
    "General Documents": "prebuilt-document",
    "Invoices":          "prebuilt-invoice",
    "Receipts":          "prebuilt-receipt",
}


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _get_credentials() -> tuple[str, str]:
    """Retrieve Azure credentials stored in Streamlit session state."""
    endpoint = st.session_state.get("azure_endpoint", "")
    api_key  = st.session_state.get("azure_api_key", "")
    return endpoint, api_key


def _make_client(endpoint: str, api_key: str) -> DocumentIntelligenceClient:
    return DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
    )


def _file_to_base64(uploaded_file) -> str:
    """Read a Streamlit UploadedFile and return a base64-encoded string."""
    uploaded_file.seek(0)
    return base64.b64encode(uploaded_file.read()).decode("utf-8")


def _format_bounding_box(bounding_box) -> str:
    """Convert a flat polygon list into a readable coordinate string."""
    if not bounding_box:
        return "N/A"
    reshaped = np.array(bounding_box).reshape(-1, 2)
    return ", ".join(["[{}, {}]".format(x, y) for x, y in reshaped])


# ── OCR / Read serialiser ────────────────────────────────────────────────────────

def _serialize_read_result(result) -> dict:
    """
    Convert a prebuilt-read AnalyzeResult SDK object into a plain dict
    that matches what the formatters and JSON view expect.
    """
    output = {
        "model_id": "prebuilt-read",
        "content": result.content,
        "styles": [],
        "pages": [],
    }

    # Styles (handwritten detection)
    for style in (result.styles or []):
        output["styles"].append({
            "is_handwritten": style.is_handwritten,
        })

    # Pages → lines + words
    for page in (result.pages or []):
        page_data = {
            "page_number": page.page_number,
            "width":       page.width,
            "height":      page.height,
            "unit":        page.unit,
            "lines":       [],
            "words":       [],
        }

        for line in (page.lines or []):
            page_data["lines"].append({
                "content":       line.content,
                "bounding_box":  _format_bounding_box(line.polygon),
            })

        for word in (page.words or []):
            page_data["words"].append({
                "content":    word.content,
                "confidence": word.confidence,
            })

        output["pages"].append(page_data)

    return output


# ── Layout serialiser ────────────────────────────────────────────────────────────

def _serialize_layout_result(result) -> dict:
    """
    Convert a prebuilt-layout AnalyzeResult SDK object into a plain dict.
    Captures styles, lines, selection marks, and tables.
    """
    output = {
        "model_id": "prebuilt-layout",
        "content":  result.content,
        "styles":   [],
        "pages":    [],
        "tables":   [],
    }

    # Styles
    for style in (result.styles or []):
        output["styles"].append({
            "is_handwritten": style.is_handwritten,
        })

    # Pages → lines + selection marks
    for page in (result.pages or []):
        page_data = {
            "page_number":      page.page_number,
            "lines":            [],
            "selection_marks":  [],
        }

        for line in (page.lines or []):
            page_data["lines"].append({
                "line_index": (page.lines or []).index(line),
                "content":    line.content,
            })

        for mark in (page.selection_marks or []):
            page_data["selection_marks"].append({
                "state":      mark.state,
                "confidence": mark.confidence,
            })

        output["pages"].append(page_data)

    # Tables
    for t_idx, table in enumerate(result.tables or []):
        table_data = {
            "table_index": t_idx,
            "row_count":   table.row_count,
            "column_count": table.column_count,
            "cells": [],
        }
        for cell in (table.cells or []):
            table_data["cells"].append({
                "row_index":    cell.row_index,
                "column_index": cell.column_index,
                "content":      cell.content,
            })
        output["tables"].append(table_data)

    return output


# ── Generic serialiser (Invoices, Receipts, General Documents) ──────────────────

def _serialize_generic_result(result, model_id: str) -> dict:
    """
    Use the SDK's built-in as_dict() for models that return
    structured document fields (invoices, receipts, general documents).
    Falls back to a minimal manual dict if as_dict() is unavailable.
    """
    try:
        data = result.as_dict()
        data["model_id"] = model_id
        return data
    except AttributeError:
        return {
            "model_id": model_id,
            "content":  getattr(result, "content", ""),
            "documents": [],
        }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def process_document(uploaded_file, model_name: str) -> dict:
    """
    Process a single uploaded file with the selected standard model.

    Args:
        uploaded_file : Streamlit UploadedFile
        model_name    : One of the keys in MODEL_MAP

    Returns:
        dict — serialised result ready for JSON display and table formatting
    """
    endpoint, api_key = _get_credentials()
    if not endpoint or not api_key:
        return {"error": "Azure credentials are missing. Please set them in the sidebar."}

    model_id = MODEL_MAP.get(model_name, "prebuilt-read")

    try:
        client  = _make_client(endpoint, api_key)
        b64data = _file_to_base64(uploaded_file)

        poller = client.begin_analyze_document(
            model_id,
            AnalyzeDocumentRequest(bytes_source=base64.b64decode(b64data)),
        )
        result = poller.result()

        # Route to the right serialiser
        if model_id == "prebuilt-read":
            return _serialize_read_result(result)
        elif model_id == "prebuilt-layout":
            return _serialize_layout_result(result)
        else:
            return _serialize_generic_result(result, model_id)

    except Exception as exc:
        return {"error": str(exc)}


def process_custom_model(uploaded_files: list) -> dict:
    """
    Process multiple documents (≥ 5) with the user's custom model.
    Each file is analysed individually; results are combined into one dict.

    Args:
        uploaded_files : list of Streamlit UploadedFile objects

    Returns:
        dict — combined results for all uploaded files
    """
    endpoint, api_key = _get_credentials()
    model_id = st.session_state.get("custom_model_id", "")

    if not endpoint or not api_key:
        return {"error": "Azure credentials are missing. Please set them in the sidebar."}
    if not model_id:
        return {"error": "Custom Model ID is missing. Please set it in the sidebar."}

    try:
        client  = _make_client(endpoint, api_key)
        results = []

        for uploaded_file in uploaded_files:
            b64data = _file_to_base64(uploaded_file)
            poller  = client.begin_analyze_document(
                model_id,
                AnalyzeDocumentRequest(bytes_source=base64.b64decode(b64data)),
            )
            result = poller.result()
            file_result = _serialize_generic_result(result, model_id)
            file_result["file_name"] = uploaded_file.name
            results.append(file_result)

        return {
            "model_id":     model_id,
            "total_files":  len(results),
            "file_results": results,
        }

    except Exception as exc:
        return {"error": str(exc)}