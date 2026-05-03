from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


EntityType = Literal[
    "Concept",
    "Actor",
    "Technology",
    "Outcome",
    "Risk",
    "Study",
    "Method",
    "Metric",
]

RelationshipType = Literal[
    "IMPROVES",
    "INCREASES",
    "CAUSES",
    "RAISES",
    "USES",
    "INCLUDES",
    "STUDIES",
    "IDENTIFIES",
    "REPORTS",
    "RECOMMENDS",
    "ENABLES",
]


class AppModel(BaseModel):
    """Base model with JSON helpers that work on Pydantic v2."""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class DocumentMetadata(AppModel):
    document_id: str
    source_pdf: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    page_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PageText(AppModel):
    page_number: int
    text: str
    source_pdf: str


class TextChunk(AppModel):
    chunk_id: str
    document_id: str
    source_pdf: str
    title: str | None = None
    text: str
    page_numbers: list[int]
    chunk_index: int
    char_count: int
    token_estimate: int


class Entity(AppModel):
    id: str
    name: str
    type: EntityType
    source_pdf: str
    page_numbers: list[int] = Field(default_factory=list)
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    evidence_chunk_ids: list[str] = Field(default_factory=list)


class Relationship(AppModel):
    id: str
    source_entity_id: str
    source_entity_name: str
    target_entity_id: str
    target_entity_name: str
    type: RelationshipType
    source_pdf: str
    page_numbers: list[int] = Field(default_factory=list)
    evidence: str | None = None
    evidence_chunk_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)


class GraphExtraction(AppModel):
    document_id: str
    source_pdf: str
    chunk_id: str
    page_numbers: list[int]
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class GraphEvidence(AppModel):
    relationship_type: str
    source_name: str
    source_type: str | None = None
    target_name: str
    target_type: str | None = None
    evidence: str | None = None
    source_pdf: str | None = None
    page_numbers: list[int] = Field(default_factory=list)
    confidence: float | None = None
    chunk_id: str | None = None


class TextEvidence(AppModel):
    chunk_id: str
    source_pdf: str
    page_numbers: list[int]
    text: str
    score: float | None = None
    title: str | None = None


class AnswerResult(AppModel):
    answer: str
    question: str
    text_evidence: list[TextEvidence] = Field(default_factory=list)
    graph_evidence: list[GraphEvidence] = Field(default_factory=list)
    detected_entities: list[str] = Field(default_factory=list)

