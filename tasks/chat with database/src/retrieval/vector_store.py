"""Simple FAISS-backed vector store for retrieval documents."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

try:
    import faiss  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised indirectly in test environments
    faiss = None

from src.retrieval.embeddings import BaseEmbedder
from src.utils.types import RetrievalDocument


class LocalVectorStore:
    """Persist retrieval documents and their embeddings on local disk."""

    def __init__(self, store_path: Path, embedder: BaseEmbedder):
        self.store_path = store_path
        self.embedder = embedder
        self.index_path = store_path / "index.faiss"
        self.docs_path = store_path / "documents.json"
        self.numpy_index_path = store_path / "index.npy"
        self._index = None
        self._documents: list[RetrievalDocument] = []

    def build(self, documents: list[RetrievalDocument]) -> None:
        """Create and persist a fresh retrieval index."""

        self.store_path.mkdir(parents=True, exist_ok=True)
        embeddings = self.embedder.embed([doc.text for doc in documents]).astype("float32")
        embeddings = self._normalize(embeddings)
        if faiss is not None:
            index = faiss.IndexFlatIP(embeddings.shape[1])
            index.add(embeddings)
            faiss.write_index(index, str(self.index_path))
            self._index = index
        else:
            np.save(self.numpy_index_path, embeddings)
            self._index = embeddings
        self.docs_path.write_text(
            json.dumps([asdict(doc) for doc in documents], indent=2),
            encoding="utf-8",
        )
        self._documents = documents

    def load(self) -> bool:
        """Load an existing vector store from disk."""

        has_faiss_index = self.index_path.exists()
        has_numpy_index = self.numpy_index_path.exists()
        if not self.docs_path.exists() or not (has_faiss_index or has_numpy_index):
            return False
        if faiss is not None and has_faiss_index:
            self._index = faiss.read_index(str(self.index_path))
        else:
            self._index = np.load(self.numpy_index_path)
        raw_docs = json.loads(self.docs_path.read_text(encoding="utf-8"))
        self._documents = [RetrievalDocument(**doc) for doc in raw_docs]
        return True

    def similarity_search(self, query: str, top_k: int = 5) -> list[RetrievalDocument]:
        """Return the most similar documents for the user query."""

        if self._index is None:
            raise RuntimeError("Vector store is not initialized.")

        vector = self.embedder.embed([query]).astype("float32")
        vector = self._normalize(vector)

        if faiss is not None and hasattr(self._index, "search"):
            _, indexes = self._index.search(vector, top_k)
            selected_indexes = [index for index in indexes[0] if index >= 0]
        else:
            scores = np.dot(self._index, vector[0])
            selected_indexes = np.argsort(scores)[::-1][:top_k].tolist()
        return [self._documents[index] for index in selected_indexes]

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        """Apply L2 normalization for either FAISS or NumPy search."""

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms
