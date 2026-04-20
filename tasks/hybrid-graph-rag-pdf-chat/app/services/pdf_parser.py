from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.models import DocumentMetadata, PageText

logger = logging.getLogger(__name__)


class PDFParser:
    """Extracts page-aware text and metadata from text-based PDFs."""

    def parse(self, pdf_path: Path) -> tuple[DocumentMetadata, list[PageText]]:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        reader = PdfReader(str(pdf_path))
        file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:12]
        document_id = f"{_slugify(pdf_path.stem)}-{file_hash}"
        raw_metadata = _clean_metadata(reader.metadata or {})

        title = raw_metadata.get("Title") or raw_metadata.get("/Title")
        authors = _split_authors(raw_metadata.get("Author") or raw_metadata.get("/Author"))

        pages: list[PageText] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageText(page_number=index, text=text.strip(), source_pdf=pdf_path.name))

        if not any(page.text for page in pages):
            raise ValueError(
                f"No extractable text found in {pdf_path.name}. OCR/scanned PDFs are not supported in v1."
            )

        metadata = DocumentMetadata(
            document_id=document_id,
            source_pdf=pdf_path.name,
            title=title,
            authors=authors,
            page_count=len(pages),
            metadata=raw_metadata,
        )
        logger.info("Parsed %s pages from %s", len(pages), pdf_path)
        return metadata, pages

    def save_raw(
        self,
        metadata: DocumentMetadata,
        pages: list[PageText],
        output_dir: Path,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{metadata.document_id}_raw.json"
        payload = {
            "metadata": metadata.to_dict(),
            "pages": [page.to_dict() for page in pages],
        }
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved raw PDF text to %s", output_path)
        return output_path


def _clean_metadata(metadata: Any) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in dict(metadata).items():
        clean_key = str(key).lstrip("/")
        cleaned[clean_key] = str(value)
    return cleaned


def _split_authors(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"\s+and\s+|;\s*|,\s+(?=[A-Z][a-z]+\s+[A-Z])", value)
    return [part.strip() for part in parts if part.strip()]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "document"

