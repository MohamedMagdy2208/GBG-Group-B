from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.config import Settings
from app.models import Entity, GraphExtraction, Relationship, TextChunk
from app.services.azure_openai_client import AzureOpenAIService
from app.services.entity_normalizer import (
    EntityNormalizer,
    coerce_float,
    coerce_int_list,
    coerce_str_list,
    preferred_entity_type,
)

logger = logging.getLogger(__name__)


class ExtractionParseError(ValueError):
    """Raised when a model extraction response cannot be parsed."""


class GraphExtractor:
    """Extracts graph facts from chunks with Azure OpenAI."""

    def __init__(
        self,
        settings: Settings,
        llm: AzureOpenAIService,
        normalizer: EntityNormalizer | None = None,
    ):
        self.settings = settings
        self.llm = llm
        self.normalizer = normalizer or EntityNormalizer()
        self.system_prompt = _load_prompt("graph_extraction.md")

    def extract_chunks(self, chunks: list[TextChunk]) -> list[GraphExtraction]:
        extractions: list[GraphExtraction] = []
        for index, chunk in enumerate(chunks, start=1):
            logger.info("Extracting graph facts from chunk %s/%s", index, len(chunks))
            payload = self.llm.chat_json(self.system_prompt, self._chunk_prompt(chunk))
            extractions.append(self.parse_extraction_response(payload, chunk))
        return extractions

    def parse_extraction_response(self, payload: dict[str, Any], chunk: TextChunk) -> GraphExtraction:
        raw_entities = _payload_list(payload, "entities")
        raw_relationships = _payload_list(payload, "relationships")

        entities: list[Entity] = []
        entity_id_by_name: dict[str, str] = {}

        for item in raw_entities:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            entity_type = self.normalizer.normalize_entity_type(item.get("type"))
            entity_id = self.normalizer.entity_id(entity_type, name)
            canonical_name = self.normalizer.display_name(name)
            aliases = coerce_str_list(item.get("aliases"))
            if name != canonical_name:
                aliases.append(name)
            page_numbers = coerce_int_list(item.get("page_numbers"), chunk.page_numbers)

            try:
                entity = Entity(
                    id=entity_id,
                    name=canonical_name,
                    type=entity_type,
                    source_pdf=chunk.source_pdf,
                    page_numbers=page_numbers,
                    description=_optional_str(item.get("description")),
                    aliases=coerce_str_list(aliases),
                    stats=_dict_or_empty(item.get("stats")),
                    confidence=coerce_float(item.get("confidence")),
                    evidence_chunk_ids=[chunk.chunk_id],
                )
            except ValidationError as exc:
                logger.warning("Skipping invalid entity %s: %s", name, exc)
                continue
            _merge_entity_into_list(entities, entity)
            entity_id_by_name[self.normalizer.normalize_name(name)] = entity_id
            entity_id_by_name[self.normalizer.normalize_name(canonical_name)] = entity_id
            for alias in aliases:
                entity_id_by_name[self.normalizer.normalize_name(alias)] = entity_id

        relationships: list[Relationship] = []
        for item in raw_relationships:
            if not isinstance(item, dict):
                continue
            rel_type = self.normalizer.normalize_relationship_type(item.get("type"))
            if not rel_type:
                continue

            source_name = str(item.get("source") or item.get("source_entity") or "").strip()
            target_name = str(item.get("target") or item.get("target_entity") or "").strip()
            if not source_name or not target_name:
                continue

            source_id = entity_id_by_name.get(self.normalizer.normalize_name(source_name))
            target_id = entity_id_by_name.get(self.normalizer.normalize_name(target_name))
            if not source_id:
                source_id = self._ensure_entity(
                    entities,
                    entity_id_by_name,
                    source_name,
                    "Concept",
                    chunk,
                )
            if not target_id:
                target_id = self._ensure_entity(
                    entities,
                    entity_id_by_name,
                    target_name,
                    "Concept",
                    chunk,
                )

            relationship_id = self.normalizer.relationship_id(
                source_id,
                rel_type,
                target_id,
                chunk.chunk_id,
            )
            try:
                relationship = Relationship(
                    id=relationship_id,
                    source_entity_id=source_id,
                    source_entity_name=self.normalizer.display_name(source_name),
                    target_entity_id=target_id,
                    target_entity_name=self.normalizer.display_name(target_name),
                    type=rel_type,
                    source_pdf=chunk.source_pdf,
                    page_numbers=coerce_int_list(item.get("page_numbers"), chunk.page_numbers),
                    evidence=_optional_str(item.get("evidence")),
                    evidence_chunk_id=chunk.chunk_id,
                    properties=_dict_or_empty(item.get("properties")),
                    confidence=coerce_float(item.get("confidence")),
                )
            except ValidationError as exc:
                logger.warning("Skipping invalid relationship %s -> %s: %s", source_name, target_name, exc)
                continue
            relationships.append(relationship)

        if not entities and not relationships and raw_entities:
            raise ExtractionParseError("Extraction response contained entities but none matched the schema.")

        return GraphExtraction(
            document_id=chunk.document_id,
            source_pdf=chunk.source_pdf,
            chunk_id=chunk.chunk_id,
            page_numbers=chunk.page_numbers,
            entities=entities,
            relationships=relationships,
            raw_response=payload,
        )

    def save_extractions(
        self,
        extractions: list[GraphExtraction],
        output_dir: Path,
        document_id: str,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{document_id}_extractions.json"
        payload = [extraction.to_dict() for extraction in extractions]
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved graph extraction JSON to %s", output_path)
        return output_path

    def _chunk_prompt(self, chunk: TextChunk) -> str:
        text = chunk.text[: self.settings.extraction_max_chars]
        return (
            f"Source PDF: {chunk.source_pdf}\n"
            f"Title: {chunk.title or 'Unknown'}\n"
            f"Chunk ID: {chunk.chunk_id}\n"
            f"Page numbers: {chunk.page_numbers}\n\n"
            f"Chunk text:\n{text}"
        )

    def _ensure_entity(
        self,
        entities: list[Entity],
        entity_id_by_name: dict[str, str],
        name: str,
        entity_type: str,
        chunk: TextChunk,
    ) -> str:
        normalized_type = self.normalizer.normalize_entity_type(entity_type)
        entity_id = self.normalizer.entity_id(normalized_type, name)
        entity = Entity(
            id=entity_id,
            name=self.normalizer.display_name(name),
            type=normalized_type,
            source_pdf=chunk.source_pdf,
            page_numbers=chunk.page_numbers,
            confidence=0.65,
            evidence_chunk_ids=[chunk.chunk_id],
        )
        _merge_entity_into_list(entities, entity)
        entity_id_by_name[self.normalizer.normalize_name(name)] = entity_id
        return entity_id


def _load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parents[1] / "prompts" / name
    return path.read_text(encoding="utf-8")


def _payload_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None and isinstance(payload.get("graph"), dict):
        value = payload["graph"].get(key)
    if isinstance(value, list):
        return value
    return []


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _merge_entity_into_list(entities: list[Entity], incoming: Entity) -> None:
    for existing in entities:
        if existing.id != incoming.id:
            continue
        existing.type = preferred_entity_type(existing.type, incoming.type)
        existing.page_numbers = sorted(set(existing.page_numbers + incoming.page_numbers))
        existing.aliases = coerce_str_list(existing.aliases + incoming.aliases + [incoming.name])
        existing.evidence_chunk_ids = sorted(
            set(existing.evidence_chunk_ids + incoming.evidence_chunk_ids)
        )
        if incoming.description and (
            not existing.description or len(incoming.description) > len(existing.description)
        ):
            existing.description = incoming.description
        existing.stats.update(incoming.stats)
        existing.confidence = max(existing.confidence, incoming.confidence)
        return
    entities.append(incoming)
