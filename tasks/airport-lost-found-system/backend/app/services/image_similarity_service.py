"""Image-similarity helpers shared by lost / found enrichment paths.

Two strategies live here:

1. **Perceptual hash (pHash)** — works in both local and Azure mode.
   Stored as a 64-bit hex string. Hamming-distance based similarity score
   in [0, 100]. Identical images score 100; visually unrelated images score
   well under 50.

2. **Multimodal vectorize-image** — only used when ``USE_AZURE_SERVICES=true``
   *and* the Azure AI Vision endpoint+key are configured. Falls back to a
   deterministic local hash-bag vector otherwise (matched dimension to
   ``azure_search_vector_dimensions`` so it can sit beside the text vector
   inside Azure AI Search).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings


logger = logging.getLogger(__name__)


PHASH_BITS = 64
IMAGE_VECTOR_DIM = 1024  # Azure AI Vision multimodal embeddings return 1024-d.


class ImageSimilarityService:
    def __init__(self) -> None:
        self.settings = get_settings()

    # ------------------------------------------------------------------ pHash

    async def compute_phash(self, blob_url: str | None) -> str | None:
        if not blob_url:
            return None
        try:
            content = await self._fetch_bytes(blob_url)
        except Exception:
            logger.exception("phash: could not fetch image", extra={"event": "phash_fetch_failed"})
            return None
        return await asyncio.to_thread(self._phash_from_bytes, content)

    @staticmethod
    def _phash_from_bytes(content: bytes) -> str | None:
        try:
            from PIL import Image
            import imagehash

            with Image.open(BytesIO(content)) as image:
                # Convert to RGB to avoid surprises with palette/L/CMYK images.
                image = image.convert("RGB")
                hash_value = imagehash.phash(image, hash_size=8)
            return str(hash_value)
        except Exception:
            logger.exception("phash: failed to hash image", extra={"event": "phash_hash_failed"})
            return None

    @staticmethod
    def phash_similarity(left: str | None, right: str | None) -> float:
        """Return a 0-100 similarity score from two pHash hex strings."""
        if not left or not right:
            return 0.0
        try:
            left_int = int(left, 16)
            right_int = int(right, 16)
        except ValueError:
            return 0.0
        distance = bin(left_int ^ right_int).count("1")
        ratio = max(0.0, (PHASH_BITS - distance) / PHASH_BITS)
        return round(ratio * 100, 2)

    # ------------------------------------------------------ Multimodal vector

    async def compute_image_vector(self, blob_url: str | None) -> tuple[str, list[float]] | None:
        if not blob_url:
            return None
        if self.settings.use_azure_services and self.settings.azure_ai_vision_endpoint and self.settings.azure_ai_vision_key:
            try:
                vector = await self._azure_vectorize_image(blob_url)
                if vector:
                    vector_id = f"img-{hashlib.sha256(str(vector[:16]).encode()).hexdigest()[:16]}"
                    return vector_id, vector
            except Exception:
                logger.exception("image vector: Azure call failed; falling back to local", extra={"event": "image_vector_fallback"})
        try:
            content = await self._fetch_bytes(blob_url)
        except Exception:
            logger.exception("image vector: fetch failed", extra={"event": "image_vector_fetch_failed"})
            return None
        vector = await asyncio.to_thread(self._local_image_vector, content)
        vector_id = f"local-img-{hashlib.sha256(str(vector[:16]).encode()).hexdigest()[:16]}"
        return vector_id, vector

    async def _azure_vectorize_image(self, blob_url: str) -> list[float] | None:
        from app.services.azure_blob_service import azure_blob_service

        secure_url = await azure_blob_service.generate_secure_url_from_blob_url(blob_url)
        endpoint = self.settings.azure_ai_vision_endpoint.rstrip("/")
        url = f"{endpoint}/computervision/retrieval:vectorizeImage"
        params = {"api-version": "2024-02-01", "model-version": "2023-04-15"}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                params=params,
                headers={
                    "Ocp-Apim-Subscription-Key": self.settings.azure_ai_vision_key,
                    "Content-Type": "application/json",
                },
                json={"url": secure_url},
            )
            response.raise_for_status()
            payload = response.json()
        vector = payload.get("vector")
        if isinstance(vector, list) and vector:
            return [float(value) for value in vector]
        return None

    def _local_image_vector(self, content: bytes) -> list[float]:
        """Deterministic placeholder vector for local mode.

        Always 1024 dimensions to match Azure AI Vision multimodal output
        (the image_vector field in Azure Search is fixed at 1024). Not a real
        similarity model — paired with pHash for actual visual matching in local mode.
        """
        size = IMAGE_VECTOR_DIM
        vector = [0.0] * size
        for index in range(0, len(content), 4):
            chunk = content[index : index + 4]
            if not chunk:
                break
            position = int(hashlib.sha256(chunk).hexdigest(), 16) % size
            vector[position] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 6) for value in vector]

    # ----------------------------------------------------------------- Helpers

    async def _fetch_bytes(self, blob_url: str) -> bytes:
        if blob_url.startswith("/uploads/"):
            relative = blob_url[len("/uploads/") :]
            local_path = self.settings.local_upload_dir / relative
            return await asyncio.to_thread(local_path.read_bytes)
        if not re.match(r"^https?://", blob_url):
            raise ValueError("unsupported blob URL")
        from app.services.azure_blob_service import azure_blob_service

        secure_url = await azure_blob_service.generate_secure_url_from_blob_url(blob_url)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(secure_url)
            response.raise_for_status()
            return response.content


image_similarity_service = ImageSimilarityService()


__all__ = ["image_similarity_service", "ImageSimilarityService", "PHASH_BITS"]
