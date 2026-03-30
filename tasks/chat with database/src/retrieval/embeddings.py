"""Embedding providers used by the local vector store."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

import numpy as np
from openai import AzureOpenAI, OpenAI

from src.config.settings import Settings


class BaseEmbedder(ABC):
    """Common interface implemented by embedding providers."""

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts into a 2D float32 matrix."""


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI-backed embedder for production usage."""

    def __init__(self, settings: Settings):
        if not settings.openai_api_key_value:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings.")
        if settings.use_azure_openai:
            if not settings.azure_openai_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI embeddings.")
            self.client = AzureOpenAI(
                api_key=settings.openai_api_key_value,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
        else:
            self.client = OpenAI(api_key=settings.openai_api_key_value)
        self.model = settings.openai_embedding_model

    def embed(self, texts: list[str]) -> np.ndarray:
        response = self.client.embeddings.create(model=self.model, input=texts)
        vectors = [item.embedding for item in response.data]
        return np.array(vectors, dtype="float32")


class HashingEmbedder(BaseEmbedder):
    """Deterministic local fallback used in tests and offline development."""

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimensions), dtype="float32")
        for row_index, text in enumerate(texts):
            for token in text.lower().split():
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                slot = int.from_bytes(digest[:2], "big") % self.dimensions
                vectors[row_index, slot] += 1.0
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


def build_embedder(settings: Settings) -> BaseEmbedder:
    """Select the configured embedder."""

    if settings.openai_api_key_value:
        return OpenAIEmbedder(settings)
    return HashingEmbedder()
