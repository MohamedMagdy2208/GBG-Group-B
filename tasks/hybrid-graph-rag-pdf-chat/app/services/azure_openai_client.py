from __future__ import annotations

import json
import logging
from typing import Any

from openai import AzureOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import ConfigurationError, Settings

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """Thin wrapper around Azure OpenAI chat and embedding deployments."""

    def __init__(self, settings: Settings):
        if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
            raise ConfigurationError(
                "Azure OpenAI endpoint/key are missing. Set AZURE_OPENAI_ENDPOINT "
                "and AZURE_OPENAI_API_KEY in .env."
            )
        self.settings = settings
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=12),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        self.settings.require_chat()
        response = self._client.chat.completions.create(
            model=self.settings.azure_openai_chat_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return parse_json_content(content)

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=12),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        self.settings.require_chat()
        response = self._client.chat.completions.create(
            model=self.settings.azure_openai_chat_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=12),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.settings.require_embeddings()
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self.settings.azure_openai_embedding_deployment,
            input=texts,
        )
        return [item.embedding for item in response.data]


def parse_json_content(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.exception("Azure OpenAI returned invalid JSON: %s", content[:500])
        raise ValueError("Azure OpenAI returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Azure OpenAI JSON response must be an object.")
    return payload
