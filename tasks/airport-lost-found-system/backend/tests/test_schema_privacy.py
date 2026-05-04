"""The Pydantic Read schemas must not leak underscore-prefixed sidecar fields."""
from datetime import UTC, datetime

from app.models import FoundItem, FoundItemStatus, LostReport, LostReportStatus, RiskLevel
from app.schemas import FoundItemRead, LostReportRead


def test_found_item_read_strips_private_keys() -> None:
    item = FoundItem(
        item_title="Black iPhone",
        category="Phone",
        raw_description="found",
        ai_clean_description="found",
        ai_extracted_attributes_json={
            "color": "black",
            "_verification_keys": [["serial", "IMEI"]],
            "_vision_source_url": "/uploads/found-items/abc.jpg",
        },
        vision_tags_json=[],
        vision_ocr_text=None,
        color="black",
        risk_level=RiskLevel.high_value,
        status=FoundItemStatus.registered,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    item.id = 1
    read = FoundItemRead.model_validate(item)
    public = read.ai_extracted_attributes_json
    assert "_verification_keys" not in public
    assert "_vision_source_url" not in public
    assert public["color"] == "black"


def test_lost_report_read_strips_private_keys() -> None:
    report = LostReport(
        item_title="Black iPhone",
        category="Phone",
        raw_description="lost",
        ai_clean_description="lost",
        ai_extracted_attributes_json={"color": "black", "_internal": "secret"},
        color="black",
        status=LostReportStatus.open,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    report.id = 1
    report.report_code = "LR-X1"
    read = LostReportRead.model_validate(report)
    assert "_internal" not in read.ai_extracted_attributes_json
    assert read.ai_extracted_attributes_json["color"] == "black"
