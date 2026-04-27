from __future__ import annotations

from app.services.pdf_parser import PDFParser


def test_pdf_parser_returns_pages_and_metadata(sample_pdf):
    metadata, pages = PDFParser().parse(sample_pdf)

    assert metadata.page_count == 12
    assert len(pages) == 12
    assert metadata.title == "The Impact of Artificial Intelligence (AI) on Students’ Academic Development"
    assert pages[0].page_number == 1
    assert "Artificial Intelligence" in pages[0].text

