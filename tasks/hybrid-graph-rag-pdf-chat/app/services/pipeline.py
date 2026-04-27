from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.models import DocumentMetadata, GraphExtraction, TextChunk
from app.services.azure_openai_client import AzureOpenAIService
from app.services.chunker import SemanticChunker
from app.services.entity_normalizer import EntityNormalizer
from app.services.extractor import GraphExtractor
from app.services.graph_store import Neo4jGraphStore
from app.services.pdf_parser import PDFParser
from app.services.vector_store import AzureEmbeddingProvider, ChromaVectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    metadata: DocumentMetadata
    chunks: list[TextChunk]
    extractions: list[GraphExtraction]
    raw_path: Path
    chunks_path: Path
    extractions_path: Path


class IngestionPipeline:
    """End-to-end pipeline from PDF to graph and vector indexes."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.parser = PDFParser()
        self.chunker = SemanticChunker(
            target_chars=settings.chunk_target_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
        self.normalizer = EntityNormalizer()

    def run(self, pdf_path: Path, rebuild: bool = False) -> IngestionResult:
        self.settings.require_chat()
        self.settings.require_embeddings()
        self.settings.require_neo4j()

        metadata, pages = self.parser.parse(pdf_path)
        self._ensure_data_dirs()

        llm = AzureOpenAIService(self.settings)
        graph_store = Neo4jGraphStore(self.settings)
        vector_store = ChromaVectorStore(
            self.settings,
            embedding_provider=AzureEmbeddingProvider(llm),
        )

        try:
            graph_store.init_schema()
            if rebuild:
                graph_store.reset_source(metadata.source_pdf)
                vector_store.delete_source(metadata.source_pdf)

            raw_path = self.parser.save_raw(metadata, pages, self.settings.raw_dir)
            chunks = self.chunker.chunk(metadata, pages)
            chunks_path = self.chunker.save_chunks(
                chunks,
                self.settings.processed_dir,
                metadata.document_id,
            )

            extractor = GraphExtractor(self.settings, llm, self.normalizer)
            extractions = extractor.extract_chunks(chunks)
            extractions_path = extractor.save_extractions(
                extractions,
                self.settings.processed_dir,
                metadata.document_id,
            )

            graph_store.upsert_document(metadata, chunks)
            graph_store.upsert_extractions(extractions)
            vector_store.upsert_chunks(chunks)
        finally:
            graph_store.close()

        logger.info("Completed ingestion for %s", metadata.source_pdf)
        return IngestionResult(
            metadata=metadata,
            chunks=chunks,
            extractions=extractions,
            raw_path=raw_path,
            chunks_path=chunks_path,
            extractions_path=extractions_path,
        )

    def _ensure_data_dirs(self) -> None:
        for path in (
            self.settings.data_dir,
            self.settings.raw_dir,
            self.settings.processed_dir,
            self.settings.vector_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

