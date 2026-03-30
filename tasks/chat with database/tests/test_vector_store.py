"""Tests for the local vector store fallback path."""

from pathlib import Path

from src.retrieval.embeddings import HashingEmbedder
from src.retrieval.vector_store import LocalVectorStore
from src.utils.types import RetrievalDocument


def test_vector_store_build_and_search(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path, HashingEmbedder())
    docs = [
        RetrievalDocument(doc_id="1", title="Revenue", kind="schema", text="Revenue lives in Invoice and InvoiceLine."),
        RetrievalDocument(doc_id="2", title="Artists", kind="schema", text="Artists connect to albums and tracks."),
    ]
    store.build(docs)
    assert store.load() is True
    results = store.similarity_search("sales revenue", top_k=1)
    assert results[0].doc_id == "1"
