from datetime import UTC, datetime

from app.models import FoundItem, FoundItemStatus, LostReport, LostReportStatus, RiskLevel
from app.services.matching_engine import matching_engine


def _lost(**overrides):
    base = LostReport(
        item_title="Black iPhone 14 on flight MS123",
        category="Phone",
        raw_description="Black iPhone 14 with clear case lost at gate B12 on flight MS123",
        ai_clean_description=None,
        brand="Apple",
        model="iPhone 14",
        color="black",
        lost_location="Terminal 2 Gate B12",
        flight_number="MS123",
        ai_extracted_attributes_json={"unique_identifiers": ["IMEI123456789"]},
        contact_email="x@y.com",
        contact_phone=None,
        lost_datetime=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        status=LostReportStatus.open,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _found(**overrides):
    base = FoundItem(
        item_title="Black smartphone",
        category="Phone",
        raw_description="Black smartphone with clear case found at gate B12",
        ai_clean_description=None,
        ai_extracted_attributes_json={"unique_identifiers": ["IMEI123456789"], "flight_number": "MS123"},
        vision_tags_json=[],
        vision_ocr_text=None,
        brand="Apple",
        model=None,
        color="black",
        found_location="Terminal 2 Gate B12",
        storage_location="Lost & Found Office T2",
        risk_level=RiskLevel.high_value,
        found_datetime=datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
        status=FoundItemStatus.registered,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_evidence_spans_marks_category_color_location_flight_identifier() -> None:
    spans = matching_engine.evidence_spans(_lost(), _found())
    assert spans["category_match"] is True
    assert spans["color_match"] is True
    assert spans["location_match"] is True
    assert spans["flight_match"] is True
    assert "imei123456789" in spans["identifier_overlap"]
    assert spans["lost"]["category"], "should highlight the lost-side category"
    assert spans["found"]["color"], "should highlight the found-side color"
    assert any(span["text"].lower().startswith("ms123") for span in spans["lost"]["flight"])


def test_evidence_spans_includes_shared_terms() -> None:
    spans = matching_engine.evidence_spans(_lost(), _found())
    assert any(term in {"black", "iphone", "smartphone", "case", "gate"} for term in spans["shared_terms"])


def test_evidence_spans_no_match_returns_empty_facets() -> None:
    spans = matching_engine.evidence_spans(
        _lost(category="Bag", color="red", lost_location="Baggage Claim 4", flight_number="QR99", ai_extracted_attributes_json={}),
        _found(category="Phone", color="black", found_location="Restroom near gate F1", ai_extracted_attributes_json={}),
    )
    assert spans["category_match"] is False
    assert spans["color_match"] is False
    assert spans["location_match"] is False
    assert spans["flight_match"] is False
    assert spans["identifier_overlap"] == []
