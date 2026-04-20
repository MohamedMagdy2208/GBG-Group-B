from __future__ import annotations

from app.services.chunker import SemanticChunker
from app.services.pdf_parser import PDFParser


def test_chunker_creates_stable_page_aware_chunks(sample_pdf):
    metadata, pages = PDFParser().parse(sample_pdf)
    chunker = SemanticChunker(target_chars=1200, overlap_chars=100)

    chunks = chunker.chunk(metadata, pages)

    assert chunks
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert all(chunk.page_numbers for chunk in chunks)
    assert all(chunk.source_pdf == sample_pdf.name for chunk in chunks)
    assert chunks[0].document_id == metadata.document_id

