"""Backward-compatible processing helpers.

New code should use services.document_service directly. These wrappers keep the
existing component imports working while returning full SDK dictionaries.
"""

from __future__ import annotations

from services.document_service import AnalyzeOptions, analyze_document
from services.model_registry import resolve_model_id


def process_document(uploaded_file, model_name: str, options: AnalyzeOptions | None = None) -> dict:
    """Analyze a document with a supported prebuilt display name or model ID."""

    return analyze_document(resolve_model_id(model_name), uploaded_file, options)


def extract_with_annotations(uploaded_file, file_name: str) -> dict:
    """Run a local OCR/value matching check against saved annotations.

    This is not Azure custom model inference. It is retained as a lightweight
    validation helper for manually entered annotation values.
    """

    from utils.annotation_store import get_annotations_for_file

    ocr_result = process_document(uploaded_file, "OCR / Read")
    if "error" in ocr_result:
        return ocr_result

    annotations = get_annotations_for_file(file_name)
    if not annotations:
        return {
            "model_id": "annotation-based",
            "warning": f"No annotations found for '{file_name}'. Please annotate first.",
            "ocr_content": ocr_result.get("content", ""),
            "matched_fields": [],
            "unmatched_annotations": [],
        }

    full_text = ocr_result.get("content", "")
    matched = []
    unmatched = []
    skipped = []

    for annotation in annotations:
        label = annotation.get("label", "")
        expected_value = str(annotation.get("value", "")).strip()
        entry = {
            "label": label,
            "value": expected_value,
            "bbox": annotation.get("bbox", [0, 0, 0, 0]),
        }
        if not expected_value:
            skipped.append({**entry, "reason": "Empty annotation value"})
            continue

        found = expected_value in full_text
        entry["ocr_matched"] = found
        if found:
            matched.append(entry)
        else:
            unmatched.append(entry)

    return {
        "model_id": "annotation-based",
        "file_name": file_name,
        "ocr_content": full_text,
        "matched_fields": matched,
        "unmatched_annotations": unmatched,
        "skipped_annotations": skipped,
        "total_annotations": len(annotations),
        "match_rate": f"{len(matched)}/{len(annotations)}",
    }
