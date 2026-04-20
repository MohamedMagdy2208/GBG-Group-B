from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.models import DocumentMetadata, PageText, TextChunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TextUnit:
    text: str
    page_number: int


class SemanticChunker:
    """Builds page-aware chunks from paragraph and sentence units."""

    def __init__(self, target_chars: int = 1800, overlap_chars: int = 250):
        if target_chars < 500:
            raise ValueError("target_chars should be at least 500 for useful retrieval chunks.")
        self.target_chars = target_chars
        self.overlap_chars = max(0, overlap_chars)

    def chunk(self, metadata: DocumentMetadata, pages: list[PageText]) -> list[TextChunk]:
        units = self._page_units(pages)
        chunks: list[TextChunk] = []
        current: list[TextUnit] = []
        current_len = 0

        for unit in units:
            if current and current_len + len(unit.text) + 2 > self.target_chars:
                chunks.append(self._build_chunk(metadata, current, len(chunks)))
                current = self._overlap_units(current)
                current_len = sum(len(item.text) + 2 for item in current)

            current.append(unit)
            current_len += len(unit.text) + 2

        if current:
            chunks.append(self._build_chunk(metadata, current, len(chunks)))

        logger.info("Created %s chunks for %s", len(chunks), metadata.source_pdf)
        return chunks

    def save_chunks(self, chunks: list[TextChunk], output_dir: Path, document_id: str) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{document_id}_chunks.json"
        payload = [chunk.to_dict() for chunk in chunks]
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved chunks to %s", output_path)
        return output_path

    def _page_units(self, pages: list[PageText]) -> list[TextUnit]:
        units: list[TextUnit] = []
        for page in pages:
            page_text = _normalize_page_text(page.text)
            paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", page_text) if part.strip()]
            if not paragraphs:
                paragraphs = [page_text] if page_text else []

            for paragraph in paragraphs:
                paragraph = _collapse_inline_whitespace(paragraph)
                if not paragraph:
                    continue
                if len(paragraph) <= self.target_chars:
                    units.append(TextUnit(text=paragraph, page_number=page.page_number))
                else:
                    units.extend(
                        TextUnit(text=piece, page_number=page.page_number)
                        for piece in _split_long_text(paragraph, self.target_chars)
                    )
        return units

    def _overlap_units(self, current: list[TextUnit]) -> list[TextUnit]:
        if self.overlap_chars <= 0:
            return []
        selected: list[TextUnit] = []
        total = 0
        for unit in reversed(current):
            selected.append(unit)
            total += len(unit.text)
            if total >= self.overlap_chars:
                break
        return list(reversed(selected))

    def _build_chunk(
        self,
        metadata: DocumentMetadata,
        units: list[TextUnit],
        chunk_index: int,
    ) -> TextChunk:
        text = "\n\n".join(unit.text for unit in units).strip()
        page_numbers = sorted({unit.page_number for unit in units})
        stable_key = f"{metadata.document_id}:{chunk_index}:{text[:80]}"
        digest = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()[:10]
        return TextChunk(
            chunk_id=f"{metadata.document_id}-chunk-{chunk_index:04d}-{digest}",
            document_id=metadata.document_id,
            source_pdf=metadata.source_pdf,
            title=metadata.title,
            text=text,
            page_numbers=page_numbers,
            chunk_index=chunk_index,
            char_count=len(text),
            token_estimate=max(1, len(text) // 4),
        )


def _normalize_page_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    return text.strip()


def _collapse_inline_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _split_long_text(text: str, target_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    pieces: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if current and current_len + len(sentence) + 1 > target_chars:
            pieces.append(" ".join(current).strip())
            current = []
            current_len = 0
        current.append(sentence)
        current_len += len(sentence) + 1

    if current:
        pieces.append(" ".join(current).strip())
    return [piece for piece in pieces if piece]

