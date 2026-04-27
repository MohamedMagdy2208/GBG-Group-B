from __future__ import annotations

import pytest

from app.models import TextChunk
from app.services.azure_openai_client import parse_json_content
from app.services.extractor import GraphExtractor


class DummyLLM:
    pass


def test_extractor_parses_structured_graph_response(test_settings):
    chunk = TextChunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        source_pdf="paper.pdf",
        title="Paper",
        text="AI improves academic performance.",
        page_numbers=[1],
        chunk_index=0,
        char_count=33,
        token_estimate=8,
    )
    payload = {
        "entities": [
            {
                "name": "AI",
                "type": "Technology",
                "aliases": ["Artificial Intelligence"],
                "description": "AI tools used in education.",
                "confidence": 0.9,
            },
            {"name": "Academic Performance", "type": "Outcome", "confidence": 0.8},
        ],
        "relationships": [
            {
                "source": "AI",
                "type": "IMPROVES",
                "target": "Academic Performance",
                "evidence": "AI improves academic performance.",
                "confidence": 0.84,
            }
        ],
    }

    extraction = GraphExtractor(test_settings, DummyLLM()).parse_extraction_response(payload, chunk)

    assert len(extraction.entities) == 2
    assert len(extraction.relationships) == 1
    assert extraction.entities[0].name == "Artificial Intelligence"
    assert extraction.relationships[0].type == "IMPROVES"
    assert extraction.relationships[0].evidence_chunk_id == "chunk-1"


def test_parse_json_content_rejects_malformed_json():
    with pytest.raises(ValueError):
        parse_json_content("{not valid json")

