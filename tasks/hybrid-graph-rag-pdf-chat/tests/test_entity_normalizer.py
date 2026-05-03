from __future__ import annotations

from app.services.entity_normalizer import EntityNormalizer


def test_normalizer_merges_ai_aliases():
    normalizer = EntityNormalizer()

    assert normalizer.normalize_name("AI") == "artificial intelligence"
    assert normalizer.normalize_name("Artificial Intelligence (AI)") == "artificial intelligence"
    assert normalizer.entity_id("Technology", "AI") == normalizer.entity_id(
        "Technology",
        "Artificial Intelligence",
    )
    assert normalizer.entity_id("Concept", "AI") == normalizer.entity_id(
        "Technology",
        "Artificial Intelligence",
    )

