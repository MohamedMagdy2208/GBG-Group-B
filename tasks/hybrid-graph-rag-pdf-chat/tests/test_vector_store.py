from __future__ import annotations

from app.models import TextChunk
from app.services.vector_store import ChromaVectorStore


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            lower = text.lower()
            if "privacy" in lower:
                vectors.append([1.0, 0.0, 0.0])
            elif "performance" in lower:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


def test_vector_store_upserts_and_searches_chunks(test_settings):
    store = ChromaVectorStore(test_settings, FakeEmbeddingProvider())
    store.reset_collection()
    chunks = [
        TextChunk(
            chunk_id="privacy",
            document_id="doc",
            source_pdf="paper.pdf",
            title="Paper",
            text="AI raises data privacy concerns.",
            page_numbers=[3],
            chunk_index=0,
            char_count=32,
            token_estimate=8,
        ),
        TextChunk(
            chunk_id="performance",
            document_id="doc",
            source_pdf="paper.pdf",
            title="Paper",
            text="AI improves academic performance.",
            page_numbers=[5],
            chunk_index=1,
            char_count=33,
            token_estimate=8,
        ),
    ]

    store.upsert_chunks(chunks)
    results = store.similarity_search("privacy risks", top_k=1, source_pdf="paper.pdf")

    assert len(results) == 1
    assert results[0].chunk_id == "privacy"
    assert results[0].page_numbers == [3]

