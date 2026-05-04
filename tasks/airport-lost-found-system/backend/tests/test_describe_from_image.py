import asyncio

from app.services.azure_openai_service import azure_openai_service


def test_local_describe_image_classifies_phone_with_color() -> None:
    vision = {
        "caption": "A black smartphone on a wooden table",
        "tags": [{"name": "phone", "confidence": 0.92}, {"name": "black", "confidence": 0.88}],
        "objects": [{"name": "iphone", "confidence": 0.81}],
        "ocr_text": "",
    }
    result = asyncio.run(azure_openai_service.describe_item_from_vision(vision))
    assert result["category"].lower() in {"phone", "iphone", "mobile"}
    assert result["color"].lower() == "black"
    assert result["suggested_risk_level"] == "high_value"
    assert "phone" in result["item_title"].lower()
    assert 0 < result["confidence"] <= 1


def test_local_describe_image_marks_passport_as_sensitive() -> None:
    vision = {
        "caption": "An open passport on a counter",
        "tags": [{"name": "passport", "confidence": 0.95}],
        "objects": [{"name": "document", "confidence": 0.70}],
        "ocr_text": "REPUBLIC OF EGYPT",
    }
    result = asyncio.run(azure_openai_service.describe_item_from_vision(vision))
    assert result["suggested_risk_level"] == "sensitive"
    assert result["raw_description"]


def test_local_describe_image_falls_back_to_unidentified() -> None:
    vision = {"caption": "", "tags": [], "objects": [], "ocr_text": ""}
    result = asyncio.run(azure_openai_service.describe_item_from_vision(vision))
    assert result["item_title"]
    assert result["suggested_risk_level"] == "normal"
