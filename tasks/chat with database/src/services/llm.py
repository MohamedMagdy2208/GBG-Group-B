"""OpenAI-backed chat helpers used for SQL generation and result summarization."""

from __future__ import annotations

import json
from typing import Any

from openai import AzureOpenAI, OpenAI

from src.config.settings import Settings


def _extract_json(text: str) -> dict[str, Any]:
    """Parse model output that may include a fenced JSON block."""

    payload = text.strip()
    if payload.startswith("```"):
        payload = payload.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(payload)


class OpenAIChatService:
    """Small wrapper around the OpenAI chat completions API."""

    def __init__(self, settings: Settings):
        if not settings.openai_api_key_value:
            raise ValueError("OPENAI_API_KEY is required for chat completion calls.")
        if settings.use_azure_openai:
            if not settings.azure_openai_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI chat.")
            self.client = AzureOpenAI(
                api_key=settings.openai_api_key_value,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
        else:
            self.client = OpenAI(api_key=settings.openai_api_key_value)
        self.model = settings.openai_chat_model

    def complete_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Request a JSON object and parse it."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return _extract_json(content)

    def complete_text(self, messages: list[dict[str, str]]) -> str:
        """Request a plain-text answer."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
