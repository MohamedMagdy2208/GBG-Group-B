import asyncio

from app.services.azure_openai_service import azure_openai_service


def test_local_questions_for_phone_mention_case_or_scratches() -> None:
    result = asyncio.run(
        azure_openai_service.generate_verification_questions(
            found_attributes={"color": "black", "brand": "Apple"},
            vision_tags=[{"name": "phone"}, {"name": "case"}],
            ocr_text=None,
            category="Phone",
        )
    )
    assert 1 <= len(result) <= 3
    text = " ".join(item["question"].lower() for item in result)
    assert "case" in text or "scratch" in text


def test_local_questions_use_ocr_text_when_present() -> None:
    result = asyncio.run(
        azure_openai_service.generate_verification_questions(
            found_attributes={},
            vision_tags=[{"name": "passport"}],
            ocr_text="REPUBLIC OF EGYPT",
            category="Passport",
        )
    )
    assert any("text" in item["question"].lower() for item in result)


def test_local_questions_default_to_three_max() -> None:
    result = asyncio.run(
        azure_openai_service.generate_verification_questions(
            found_attributes={"color": "red"},
            vision_tags=[],
            ocr_text=None,
            category="Bag",
        )
    )
    assert len(result) <= 3
    assert all("question" in item and "expected_keywords" in item for item in result)
