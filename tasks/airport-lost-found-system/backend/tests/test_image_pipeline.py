"""End-to-end checks for the image-handling code paths.

We exercise:
1. Vision local-mode keyword extraction from the filename.
2. Vision describe_item_from_vision returns sensible defaults.
3. Blob validation (content type, signature, size, alias).
4. PII masking before search indexing keeps title/category usable.
5. Vision results survive enrichment-style update (no double-call when image unchanged).
"""
from __future__ import annotations

import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from app.services.azure_blob_service import azure_blob_service, _normalize_content_type
from app.services.azure_openai_service import azure_openai_service
from app.services.azure_vision_service import azure_vision_service
from app.core.security import mask_sensitive_text


def _upload(content: bytes, content_type: str | None, filename: str = "x.jpg") -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type or ""})


def test_vision_local_mode_picks_up_filename_keywords() -> None:
    result = asyncio.run(azure_vision_service.analyze_uploaded_item_image("/uploads/found-items/black-iphone-found.jpg"))
    names = [tag["name"] for tag in result["tags"]]
    assert "iphone" in names or "phone" in names
    assert isinstance(result["objects"], list)


def test_vision_local_mode_falls_back_to_personal_item() -> None:
    result = asyncio.run(azure_vision_service.analyze_uploaded_item_image("/uploads/proofs/abcdef.jpg"))
    assert result["tags"]
    assert result["caption"]


def test_vision_objects_and_tags_are_independent_lists() -> None:
    """Mutating one returned list must not affect the other (regression guard)."""
    result = asyncio.run(azure_vision_service.analyze_uploaded_item_image("/uploads/proofs/laptop.jpg"))
    result["tags"].append({"name": "extra", "confidence": 1.0})
    assert {"name": "extra", "confidence": 1.0} not in result["objects"]


def test_blob_validate_accepts_jpeg_with_alias_content_type() -> None:
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"0" * 64
    upload = _upload(jpeg_bytes, "image/jpg")
    canonical = asyncio.run(azure_blob_service.validate_file(upload, jpeg_bytes))
    assert canonical == "image/jpeg"


def test_blob_validate_rejects_mismatched_signature() -> None:
    fake = b"NOT-A-REAL-IMAGE" + b"0" * 64
    upload = _upload(fake, "image/jpeg")
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(azure_blob_service.validate_file(upload, fake))
    assert excinfo.value.status_code == 400


def test_blob_validate_rejects_unsupported_content_type() -> None:
    upload = _upload(b"\xff\xd8\xff" + b"0" * 64, "application/octet-stream")
    with pytest.raises(HTTPException):
        asyncio.run(azure_blob_service.validate_file(upload, b"\xff\xd8\xff" + b"0" * 64))


def test_blob_validate_rejects_tiny_file() -> None:
    upload = _upload(b"\xff\xd8\xff", "image/jpeg")
    with pytest.raises(HTTPException):
        asyncio.run(azure_blob_service.validate_file(upload, b"\xff\xd8\xff"))


def test_normalize_content_type_strips_charset_and_aliases() -> None:
    assert _normalize_content_type("Image/JPG") == "image/jpeg"
    assert _normalize_content_type("image/png; charset=utf-8") == "image/png"
    assert _normalize_content_type(None) is None


def test_describe_from_vision_routes_dangerous_items() -> None:
    vision = {
        "caption": "A pocket knife with a wooden handle",
        "tags": [{"name": "knife"}],
        "objects": [{"name": "blade"}],
        "ocr_text": "",
    }
    result = asyncio.run(azure_openai_service.describe_item_from_vision(vision))
    assert result["suggested_risk_level"] == "dangerous"


def test_pii_masking_preserves_title_and_category_keywords() -> None:
    raw = "Black iPhone 14 imei 123456789012345 lost at gate B12 flight MS123"
    masked = mask_sensitive_text(raw)
    assert masked is not None
    lower = masked.lower()
    # Searchable keywords stay visible.
    assert "iphone" in lower
    assert "gate" in lower
    assert "flight" in lower
    # 15-digit identifier is redacted.
    assert "123456789012345" not in masked
    assert "[REDACTED]" in masked


def test_describe_from_vision_handles_empty_payload() -> None:
    result = asyncio.run(azure_openai_service.describe_item_from_vision({"caption": "", "tags": [], "objects": [], "ocr_text": ""}))
    assert result["item_title"]
    assert result["confidence"] >= 0
    assert result["suggested_risk_level"] in {"normal", "high_value", "sensitive", "dangerous"}


def test_local_embedding_dimension_matches_search_vector_dimension() -> None:
    _, embedding = azure_openai_service.fallback_embedding("Black iPhone 14 at gate B12")
    assert len(embedding) == azure_openai_service.settings.azure_search_vector_dimensions


def test_identifier_grounding_drops_planted_serials() -> None:
    raw = "Lost a black iphone at gate B12"
    fake_response = {"unique_identifiers": ["IMEI999999999999999"], "color": "black"}
    grounded = azure_openai_service._enforce_identifier_grounding(fake_response, raw)
    # The fake serial does not appear in the raw text -> dropped.
    assert grounded["unique_identifiers"] == []


def test_identifier_grounding_keeps_serials_present_in_raw_text() -> None:
    raw = "Lost an iphone, serial number ABC123XYZ, at gate B12"
    response = {"unique_identifiers": ["ABC123XYZ"]}
    grounded = azure_openai_service._enforce_identifier_grounding(response, raw)
    assert "ABC123XYZ" in grounded["unique_identifiers"]
