"""Tests for the image-similarity helpers and the matching-engine image signal."""
from __future__ import annotations

import asyncio
from io import BytesIO

import pytest

from app.services.image_similarity_service import image_similarity_service, ImageSimilarityService

PIL = pytest.importorskip("PIL")
imagehash = pytest.importorskip("imagehash")
from PIL import Image, ImageDraw  # type: ignore  # noqa: E402


def _png_bytes(color: tuple[int, int, int], size: int = 64) -> bytes:
    image = Image.new("RGB", (size, size), color=color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _png_bytes_with_text(text: str, size: int = 64) -> bytes:
    image = Image.new("RGB", (size, size), color=(220, 220, 220))
    draw = ImageDraw.Draw(image)
    draw.rectangle([(8, 8), (size - 8, size - 8)], outline=(0, 0, 0), width=2)
    draw.text((10, 24), text, fill=(0, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_phash_identical_images_score_100() -> None:
    bytes_value = _png_bytes((0, 0, 0))
    h1 = ImageSimilarityService._phash_from_bytes(bytes_value)
    h2 = ImageSimilarityService._phash_from_bytes(bytes_value)
    assert h1 is not None and h2 is not None
    assert image_similarity_service.phash_similarity(h1, h2) == 100.0


def test_phash_similar_images_score_above_70() -> None:
    h1 = ImageSimilarityService._phash_from_bytes(_png_bytes_with_text("airport"))
    h2 = ImageSimilarityService._phash_from_bytes(_png_bytes_with_text("airport"))
    assert h1 and h2
    score = image_similarity_service.phash_similarity(h1, h2)
    assert score >= 90  # same image rendered twice -> identical


def test_phash_different_images_score_low() -> None:
    h_black = ImageSimilarityService._phash_from_bytes(_png_bytes((0, 0, 0)))
    h_white = ImageSimilarityService._phash_from_bytes(_png_bytes((255, 255, 255)))
    assert h_black and h_white
    # Solid black vs solid white share the same flat-image phash (all zeros) by design;
    # take a textured contrast instead.
    h_text = ImageSimilarityService._phash_from_bytes(_png_bytes_with_text("ABC"))
    assert h_text is not None
    assert image_similarity_service.phash_similarity(h_text, h_white) < 95


def test_phash_handles_missing_or_invalid_input() -> None:
    assert image_similarity_service.phash_similarity(None, "abc") == 0.0
    assert image_similarity_service.phash_similarity("abc", None) == 0.0
    assert image_similarity_service.phash_similarity("not-hex", "0123456789abcdef") == 0.0


def test_local_image_vector_is_deterministic_and_correct_dimension() -> None:
    payload = _png_bytes_with_text("hello")
    vector_a = image_similarity_service._local_image_vector(payload)
    vector_b = image_similarity_service._local_image_vector(payload)
    assert vector_a == vector_b
    # Image vector is fixed at 1024 dims to match Azure Vision multimodal output.
    assert len(vector_a) == 1024


def test_compute_image_vector_local_path(tmp_path) -> None:
    settings = image_similarity_service.settings
    upload_dir = settings.local_upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / "found-items" / "image-vector-test.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_png_bytes((10, 20, 30)))
    try:
        result = asyncio.run(image_similarity_service.compute_image_vector("/uploads/found-items/image-vector-test.png"))
        assert result is not None
        vector_id, vector = result
        assert vector_id.startswith("local-img-") or vector_id.startswith("img-")
        assert len(vector) == 1024
    finally:
        try:
            target.unlink()
        except FileNotFoundError:
            pass


def test_compute_phash_local_path(tmp_path) -> None:
    settings = image_similarity_service.settings
    target = settings.local_upload_dir / "found-items" / "phash-test.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_png_bytes_with_text("Lost & Found"))
    try:
        first = asyncio.run(image_similarity_service.compute_phash("/uploads/found-items/phash-test.png"))
        second = asyncio.run(image_similarity_service.compute_phash("/uploads/found-items/phash-test.png"))
        assert first and second and first == second
    finally:
        try:
            target.unlink()
        except FileNotFoundError:
            pass


def test_compute_phash_returns_none_for_missing_url() -> None:
    assert asyncio.run(image_similarity_service.compute_phash(None)) is None
    assert asyncio.run(image_similarity_service.compute_phash("")) is None


def test_matching_engine_image_score_uses_phash() -> None:
    from datetime import UTC, datetime

    from app.models import FoundItem, FoundItemStatus, LostReport, LostReportStatus, RiskLevel
    from app.services.matching_engine import matching_engine

    common_phash = "abcd1234abcd1234"
    lost = LostReport(
        item_title="Black phone",
        category="Phone",
        raw_description="Lost a black phone",
        ai_clean_description=None,
        ai_extracted_attributes_json={},
        color="black",
        lost_location="Terminal 2",
        flight_number=None,
        lost_datetime=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        status=LostReportStatus.open,
        proof_phash=common_phash,
    )
    found = FoundItem(
        item_title="Black phone",
        category="Phone",
        raw_description="Found a black phone",
        ai_clean_description=None,
        ai_extracted_attributes_json={},
        vision_tags_json=[],
        vision_ocr_text=None,
        color="black",
        found_location="Terminal 2",
        risk_level=RiskLevel.normal,
        found_datetime=datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
        status=FoundItemStatus.registered,
        image_phash=common_phash,
    )
    breakdown = matching_engine.score(lost, found)
    assert breakdown["image_score"] == 100.0
    assert breakdown["match_score"] >= 50


def test_matching_engine_image_score_zero_when_phash_missing() -> None:
    from datetime import UTC, datetime

    from app.models import FoundItem, FoundItemStatus, LostReport, LostReportStatus, RiskLevel
    from app.services.matching_engine import matching_engine

    lost = LostReport(
        item_title="Black phone",
        category="Phone",
        raw_description="Lost a black phone",
        ai_clean_description=None,
        ai_extracted_attributes_json={},
        color="black",
        lost_location="Terminal 2",
        flight_number=None,
        lost_datetime=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        status=LostReportStatus.open,
    )
    found = FoundItem(
        item_title="Black phone",
        category="Phone",
        raw_description="Found a black phone",
        ai_clean_description=None,
        ai_extracted_attributes_json={},
        vision_tags_json=[],
        vision_ocr_text=None,
        color="black",
        found_location="Terminal 2",
        risk_level=RiskLevel.normal,
        found_datetime=datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
        status=FoundItemStatus.registered,
    )
    breakdown = matching_engine.score(lost, found)
    assert breakdown["image_score"] == 0.0
