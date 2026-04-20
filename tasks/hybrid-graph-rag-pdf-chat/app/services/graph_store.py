from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from app.config import Settings
from app.models import DocumentMetadata, GraphEvidence, GraphExtraction, TextChunk
from app.services.entity_normalizer import (
    ALLOWED_ENTITY_TYPES,
    ALLOWED_RELATIONSHIP_TYPES,
    EntityNormalizer,
    preferred_entity_type,
)

logger = logging.getLogger(__name__)
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "scripts" / "neo4j_schema.cypher"
ENTITY_LABELS = ":".join(sorted(ALLOWED_ENTITY_TYPES))


class Neo4jGraphStore:
    """Neo4j persistence and graph evidence retrieval."""

    def __init__(self, settings: Settings):
        settings.require_neo4j()
        self.settings = settings
        self.normalizer = EntityNormalizer()
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )

    def close(self) -> None:
        self.driver.close()

    def verify_connectivity(self) -> None:
        self.driver.verify_connectivity()

    def init_schema(self) -> None:
        statements = load_cypher_statements(SCHEMA_PATH)
        with self.driver.session(database=self.settings.neo4j_database) as session:
            for statement in statements:
                session.run(statement)
        logger.info("Initialized Neo4j constraints and indexes")

    def reset_source(self, source_pdf: str) -> None:
        with self.driver.session(database=self.settings.neo4j_database) as session:
            session.run(
                """
                MATCH (n)
                WHERE n.source_pdf = $source_pdf
                DETACH DELETE n
                """,
                source_pdf=source_pdf,
            )
        logger.info("Deleted Neo4j records for %s", source_pdf)

    def upsert_document(self, metadata: DocumentMetadata, chunks: list[TextChunk]) -> None:
        now = _utc_now()
        with self.driver.session(database=self.settings.neo4j_database) as session:
            session.run(
                """
                MERGE (d:Document {id: $id})
                SET d.source_pdf = $source_pdf,
                    d.title = $title,
                    d.authors = $authors,
                    d.page_count = $page_count,
                    d.metadata = $metadata,
                    d.ingested_at = $ingested_at,
                    d.updated_at = $updated_at
                """,
                id=metadata.document_id,
                source_pdf=metadata.source_pdf,
                title=metadata.title,
                authors=metadata.authors,
                page_count=metadata.page_count,
                metadata=json.dumps(metadata.metadata, ensure_ascii=False),
                ingested_at=metadata.ingested_at,
                updated_at=now,
            )
            for chunk in chunks:
                session.run(
                    """
                    MERGE (c:Chunk {id: $id})
                    SET c.document_id = $document_id,
                        c.source_pdf = $source_pdf,
                        c.title = $title,
                        c.text = $text,
                        c.page_numbers = $page_numbers,
                        c.chunk_index = $chunk_index,
                        c.char_count = $char_count,
                        c.token_estimate = $token_estimate,
                        c.updated_at = $updated_at
                    WITH c
                    MATCH (d:Document {id: $document_id})
                    MERGE (d)-[:HAS_CHUNK]->(c)
                    """,
                    id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    source_pdf=chunk.source_pdf,
                    title=chunk.title,
                    text=chunk.text,
                    page_numbers=chunk.page_numbers,
                    chunk_index=chunk.chunk_index,
                    char_count=chunk.char_count,
                    token_estimate=chunk.token_estimate,
                    updated_at=now,
                )

    def upsert_extractions(self, extractions: list[GraphExtraction]) -> None:
        merged_entities = _merge_entities(extractions)
        relationships = [rel for extraction in extractions for rel in extraction.relationships]
        now = _utc_now()

        with self.driver.session(database=self.settings.neo4j_database) as session:
            for entity in merged_entities:
                if entity.type not in ALLOWED_ENTITY_TYPES:
                    continue
                label = entity.type
                normalized_name = self.normalizer.normalize_name(entity.name)
                session.run(
                    f"""
                    MERGE (e:Entity {{id: $id}})
                    ON CREATE SET e.created_at = $created_at
                    REMOVE e:{ENTITY_LABELS}
                    SET e:{label},
                        e.name = $name,
                        e.normalized_name = $normalized_name,
                        e.type = $type,
                        e.source_pdf = $source_pdf,
                        e.page_numbers = $page_numbers,
                        e.description = $description,
                        e.stats = $stats,
                        e.aliases = $aliases,
                        e.confidence = $confidence,
                        e.evidence_chunk_ids = $evidence_chunk_ids,
                        e.updated_at = $updated_at
                    """,
                    id=entity.id,
                    name=entity.name,
                    normalized_name=normalized_name,
                    type=entity.type,
                    source_pdf=entity.source_pdf,
                    page_numbers=entity.page_numbers,
                    description=entity.description,
                    stats=json.dumps(entity.stats, ensure_ascii=False),
                    aliases=entity.aliases,
                    confidence=entity.confidence,
                    evidence_chunk_ids=entity.evidence_chunk_ids,
                    created_at=now,
                    updated_at=now,
                )
                for chunk_id in entity.evidence_chunk_ids:
                    session.run(
                        """
                        MATCH (e:Entity {id: $entity_id})
                        MATCH (c:Chunk {id: $chunk_id})
                        MERGE (e)-[:MENTIONED_IN]->(c)
                        """,
                        entity_id=entity.id,
                        chunk_id=chunk_id,
                    )

            for relationship in relationships:
                if relationship.type not in ALLOWED_RELATIONSHIP_TYPES:
                    continue
                rel_type = relationship.type
                session.run(
                    f"""
                    MATCH (source:Entity {{id: $source_id}})
                    MATCH (target:Entity {{id: $target_id}})
                    MERGE (source)-[r:{rel_type} {{id: $id}}]->(target)
                    ON CREATE SET r.created_at = $created_at
                    SET r.source_pdf = $source_pdf,
                        r.page_numbers = $page_numbers,
                        r.evidence = $evidence,
                        r.evidence_chunk_id = $evidence_chunk_id,
                        r.properties = $properties,
                        r.confidence = $confidence,
                        r.updated_at = $updated_at
                    """,
                    source_id=relationship.source_entity_id,
                    target_id=relationship.target_entity_id,
                    id=relationship.id,
                    source_pdf=relationship.source_pdf,
                    page_numbers=relationship.page_numbers,
                    evidence=relationship.evidence,
                    evidence_chunk_id=relationship.evidence_chunk_id,
                    properties=json.dumps(relationship.properties, ensure_ascii=False),
                    confidence=relationship.confidence,
                    created_at=now,
                    updated_at=now,
                )
        logger.info("Upserted %s entities and %s relationships", len(merged_entities), len(relationships))

    def get_graph_evidence(
        self,
        terms: list[str],
        source_pdf: str | None = None,
        limit: int = 25,
    ) -> list[GraphEvidence]:
        terms = [term.strip().lower() for term in terms if term.strip()]
        if not terms:
            return []

        query = """
        UNWIND $terms AS term
        MATCH (e:Entity)
        WHERE ($source_pdf IS NULL OR e.source_pdf = $source_pdf)
          AND (
            toLower(e.name) CONTAINS term
            OR coalesce(e.normalized_name, "") CONTAINS term
            OR any(alias IN coalesce(e.aliases, []) WHERE toLower(alias) CONTAINS term)
          )
        WITH DISTINCT e
        LIMIT $entity_limit
        MATCH (e)-[r]-(neighbor:Entity)
        RETURN startNode(r) AS source,
               endNode(r) AS target,
               type(r) AS relationship_type,
               properties(r) AS props
        ORDER BY coalesce(r.confidence, 0.0) DESC
        LIMIT $limit
        """
        with self.driver.session(database=self.settings.neo4j_database) as session:
            records = session.run(
                query,
                terms=terms,
                source_pdf=source_pdf,
                entity_limit=max(5, limit),
                limit=limit,
            )
            return [_record_to_graph_evidence(record) for record in records]

    def list_entities(self, source_pdf: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        query = """
        MATCH (e:Entity)
        WHERE $source_pdf IS NULL OR e.source_pdf = $source_pdf
        RETURN e
        ORDER BY e.name
        LIMIT $limit
        """
        with self.driver.session(database=self.settings.neo4j_database) as session:
            return [dict(record["e"]) for record in session.run(query, source_pdf=source_pdf, limit=limit)]

    def list_relationships(self, source_pdf: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        query = """
        MATCH (source:Entity)-[r]->(target:Entity)
        WHERE $source_pdf IS NULL OR r.source_pdf = $source_pdf
        RETURN source.name AS source,
               type(r) AS type,
               target.name AS target,
               properties(r) AS props
        ORDER BY type, source, target
        LIMIT $limit
        """
        with self.driver.session(database=self.settings.neo4j_database) as session:
            rows: list[dict[str, Any]] = []
            for record in session.run(query, source_pdf=source_pdf, limit=limit):
                props = dict(record["props"])
                rows.append(
                    {
                        "source": record["source"],
                        "type": record["type"],
                        "target": record["target"],
                        "evidence": props.get("evidence"),
                        "page_numbers": props.get("page_numbers"),
                        "confidence": props.get("confidence"),
                        "chunk_id": props.get("evidence_chunk_id"),
                    }
                )
            return rows

    def summary(self, source_pdf: str | None = None) -> dict[str, int]:
        query = """
        CALL () {
          MATCH (d:Document)
          WHERE $source_pdf IS NULL OR d.source_pdf = $source_pdf
          RETURN count(d) AS documents
        }
        CALL () {
          MATCH (c:Chunk)
          WHERE $source_pdf IS NULL OR c.source_pdf = $source_pdf
          RETURN count(c) AS chunks
        }
        CALL () {
          MATCH (e:Entity)
          WHERE $source_pdf IS NULL OR e.source_pdf = $source_pdf
          RETURN count(e) AS entities
        }
        CALL () {
          MATCH ()-[r]->()
          WHERE (($source_pdf IS NULL AND r.source_pdf IS NOT NULL) OR r.source_pdf = $source_pdf)
          RETURN count(r) AS relationships
        }
        RETURN documents, chunks, entities, relationships
        """
        with self.driver.session(database=self.settings.neo4j_database) as session:
            record = session.run(query, source_pdf=source_pdf).single()
            if not record:
                return {"documents": 0, "chunks": 0, "entities": 0, "relationships": 0}
            return {key: int(record[key]) for key in record.keys()}


def _merge_entities(extractions: list[GraphExtraction]):
    by_id: dict[str, Any] = {}
    for extraction in extractions:
        for entity in extraction.entities:
            existing = by_id.get(entity.id)
            if not existing:
                by_id[entity.id] = entity.model_copy(deep=True)
                continue
            existing.page_numbers = sorted(set(existing.page_numbers + entity.page_numbers))
            existing.aliases = sorted(set(existing.aliases + entity.aliases))
            existing.evidence_chunk_ids = sorted(
                set(existing.evidence_chunk_ids + entity.evidence_chunk_ids)
            )
            if entity.description and (
                not existing.description or len(entity.description) > len(existing.description)
            ):
                existing.description = entity.description
            existing.stats.update(entity.stats)
            existing.confidence = max(existing.confidence, entity.confidence)
            existing.type = preferred_entity_type(existing.type, entity.type)
    return list(by_id.values())


def _record_to_graph_evidence(record: Any) -> GraphEvidence:
    source = dict(record["source"])
    target = dict(record["target"])
    props = dict(record["props"])
    return GraphEvidence(
        relationship_type=record["relationship_type"],
        source_name=source.get("name", ""),
        source_type=source.get("type"),
        target_name=target.get("name", ""),
        target_type=target.get("type"),
        evidence=props.get("evidence"),
        source_pdf=props.get("source_pdf"),
        page_numbers=props.get("page_numbers") or [],
        confidence=props.get("confidence"),
        chunk_id=props.get("evidence_chunk_id"),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_cypher_statements(path: Path = SCHEMA_PATH) -> list[str]:
    """Load semicolon-delimited Cypher while ignoring line comments."""
    if not path.exists():
        raise FileNotFoundError(f"Neo4j schema file not found: {path}")
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        lines.append(line)
    text = "\n".join(lines)
    return [statement.strip() for statement in text.split(";") if statement.strip()]
