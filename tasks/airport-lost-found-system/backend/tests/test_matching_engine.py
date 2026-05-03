from datetime import UTC, datetime, timedelta

from app.models import FoundItem, LostReport, RiskLevel
from app.services.matching_engine import matching_engine


def test_unique_identifier_exact_match_boosts_to_high_confidence() -> None:
    lost = LostReport(
        item_title="Black laptop",
        category="Laptop",
        raw_description="Dell laptop with asset tag",
        color="black",
        lost_location="Gate B7",
        lost_datetime=datetime.now(UTC),
        ai_extracted_attributes_json={"unique_identifiers": ["ASSET-12345"]},
    )
    found = FoundItem(
        item_title="Dell laptop",
        category="Laptop",
        raw_description="Black Dell laptop",
        color="black",
        found_location="Gate B7",
        found_datetime=datetime.now(UTC) + timedelta(hours=1),
        risk_level=RiskLevel.normal,
        ai_extracted_attributes_json={"unique_identifiers": ["ASSET-12345"]},
    )

    score = matching_engine.score(lost, found, azure_search_score=60)

    assert score["match_score"] >= 90
    assert score["confidence_level"].value == "high"


def test_identifier_conflict_heavily_caps_score() -> None:
    lost = LostReport(
        item_title="Phone",
        category="Phone",
        raw_description="Blue iPhone",
        color="blue",
        lost_datetime=datetime.now(UTC),
        ai_extracted_attributes_json={"unique_identifiers": ["IMEI-111"]},
    )
    found = FoundItem(
        item_title="Phone",
        category="Phone",
        raw_description="Blue iPhone",
        color="blue",
        found_datetime=datetime.now(UTC) + timedelta(hours=1),
        risk_level=RiskLevel.sensitive,
        ai_extracted_attributes_json={"unique_identifiers": ["IMEI-999"]},
    )

    score = matching_engine.score(lost, found, azure_search_score=100)

    assert score["identifier_conflict"] is True
    assert score["match_score"] <= 35
    assert score["manual_approval_required"] is True


def test_redacted_identifiers_do_not_create_false_conflicts() -> None:
    lost = LostReport(
        item_title="Passport",
        category="Passport",
        raw_description="Passport in black holder",
        color="black",
        lost_datetime=datetime.now(UTC),
        ai_extracted_attributes_json={"unique_identifiers": ["[REDACTED]"]},
    )
    found = FoundItem(
        item_title="Passport",
        category="Passport",
        raw_description="Passport in black holder",
        color="black",
        found_datetime=datetime.now(UTC) + timedelta(hours=1),
        risk_level=RiskLevel.sensitive,
        ai_extracted_attributes_json={"unique_identifiers": ["[REDACTED]"]},
    )

    score = matching_engine.score(lost, found, azure_search_score=80)

    assert score["identifier_conflict"] is False
    assert score["unique_identifier_score"] == 0
