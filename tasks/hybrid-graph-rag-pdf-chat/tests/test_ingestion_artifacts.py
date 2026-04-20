from __future__ import annotations

import json

from app.services.chunker import SemanticChunker
from app.services.pdf_parser import PDFParser


def test_ingestion_parsing_and_chunk_artifacts_are_written(sample_pdf, test_settings):
    parser = PDFParser()
    metadata, pages = parser.parse(sample_pdf)
    raw_path = parser.save_raw(metadata, pages, test_settings.raw_dir)

    chunker = SemanticChunker(target_chars=1200, overlap_chars=100)
    chunks = chunker.chunk(metadata, pages)
    chunks_path = chunker.save_chunks(chunks, test_settings.processed_dir, metadata.document_id)

    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    chunks_payload = json.loads(chunks_path.read_text(encoding="utf-8"))

    assert raw_payload["metadata"]["document_id"] == metadata.document_id
    assert len(raw_payload["pages"]) == 12
    assert chunks_payload
    assert {"chunk_id", "text", "page_numbers", "source_pdf"}.issubset(chunks_payload[0])

