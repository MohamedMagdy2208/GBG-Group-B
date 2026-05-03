from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Protocol

import chromadb

from app.config import Settings
from app.models import TextChunk, TextEvidence
from app.services.azure_openai_client import AzureOpenAIService

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class AzureEmbeddingProvider:
    def __init__(self, llm: AzureOpenAIService):
        self.llm = llm

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.llm.embed_texts(texts)


class ChromaVectorStore:
    """Persistent local vector store for semantic chunk retrieval."""

    def __init__(
        self,
        settings: Settings,
        embedding_provider: EmbeddingProvider,
        persist_dir: Path | None = None,
        collection_name: str | None = None,
    ):
        settings.require_embeddings()
        self.settings = settings
        self.embedding_provider = embedding_provider
        self.persist_dir = persist_dir or settings.vector_dir
        self.collection_name = collection_name or settings.chroma_collection
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def reset_collection(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            logger.debug("Collection %s did not exist before reset", self.collection_name)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        logger.info("Reset Chroma collection %s", self.collection_name)

    def delete_source(self, source_pdf: str) -> None:
        try:
            self.collection.delete(where={"source_pdf": source_pdf})
            logger.info("Deleted Chroma chunks for %s", source_pdf)
        except Exception:
            logger.debug("No Chroma chunks deleted for %s", source_pdf, exc_info=True)

    def upsert_chunks(self, chunks: list[TextChunk]) -> None:
        if not chunks:
            return
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_provider.embed_texts(texts)
        metadatas = [_chunk_metadata(chunk) for chunk in chunks]
        ids = [chunk.chunk_id for chunk in chunks]
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info("Upserted %s chunks into Chroma", len(chunks))

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        source_pdf: str | None = None,
    ) -> list[TextEvidence]:
        query_embedding = self.embedding_provider.embed_texts([query])[0]
        where = {"source_pdf": source_pdf} if source_pdf else None
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        evidence: list[TextEvidence] = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] or {}
            distance = distances[index] if index < len(distances) else None
            score = None if distance is None else 1.0 / (1.0 + float(distance))
            evidence.append(
                TextEvidence(
                    chunk_id=chunk_id,
                    source_pdf=str(metadata.get("source_pdf", "")),
                    page_numbers=json.loads(metadata.get("page_numbers", "[]")),
                    text=docs[index],
                    score=score,
                    title=metadata.get("title"),
                )
            )
        return evidence


def _chunk_metadata(chunk: TextChunk) -> dict[str, str | int | float | bool]:
    return {
        "document_id": chunk.document_id,
        "source_pdf": chunk.source_pdf,
        "title": chunk.title or "",
        "page_numbers": json.dumps(chunk.page_numbers),
        "chunk_index": chunk.chunk_index,
        "char_count": chunk.char_count,
        "token_estimate": chunk.token_estimate,
    }
