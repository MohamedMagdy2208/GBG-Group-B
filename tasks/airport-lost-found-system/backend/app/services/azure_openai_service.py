import hashlib
import json
import logging
import math
import re
from difflib import SequenceMatcher
from typing import Any

from app.core.config import get_settings
from app.core.security import mask_sensitive_text
from app.services.ai_usage_service import ai_usage_service
from app.services.cache_service import cache_service


logger = logging.getLogger(__name__)


COLOR_WORDS = [
    "black",
    "white",
    "blue",
    "red",
    "green",
    "yellow",
    "silver",
    "gold",
    "gray",
    "grey",
    "brown",
    "pink",
    "purple",
    "orange",
]

CATEGORY_WORDS = {
    "phone": ["phone", "iphone", "mobile", "samsung"],
    "laptop": ["laptop", "macbook", "notebook"],
    "bag": ["bag", "backpack", "suitcase", "briefcase"],
    "wallet": ["wallet", "purse"],
    "passport": ["passport"],
    "id card": ["id", "card", "license"],
    "headphones": ["headphones", "earbuds", "airpods"],
    "keys": ["keys", "keychain"],
    "watch": ["watch"],
    "clothing": ["jacket", "shirt", "coat", "clothing"],
}


class AzureOpenAIService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _cache_key(self, prefix: str, payload: str) -> str:
        digest = hashlib.sha256((mask_sensitive_text(payload or "") or "").encode("utf-8")).hexdigest()
        return f"ai:{prefix}:{digest}"

    async def _client(self):
        from openai import AsyncAzureOpenAI

        if self.settings.azure_use_managed_identity and not self.settings.azure_openai_api_key:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            return AsyncAzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.settings.azure_openai_api_version,
            )
        return AsyncAzureOpenAI(
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version,
        )

    async def clean_item_description(self, text: str) -> str:
        key = self._cache_key("clean", text)
        cached = await cache_service.get_json(key)
        if cached:
            return cached["value"]
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            client = await self._client()
            response = await client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                messages=[
                    {"role": "system", "content": "Clean airport lost and found item descriptions. Remove unnecessary PII."},
                    {"role": "user", "content": mask_sensitive_text(text) or ""},
                ],
                temperature=0.1,
            )
            await ai_usage_service.record(
                "clean_item_description",
                self.settings.azure_openai_chat_deployment,
                response.usage,
            )
            value = response.choices[0].message.content or text
        else:
            value = " ".join((text or "").strip().split()).capitalize()
        await cache_service.set_json(key, {"value": value}, self.settings.cache_ai_ttl_seconds)
        return value

    async def extract_structured_attributes(self, text: str) -> dict[str, Any]:
        key = self._cache_key("attrs", text)
        cached = await cache_service.get_json(key)
        if cached:
            return cached
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            client = await self._client()
            response = await client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract item_type, brand, model, color, unique_identifiers, "
                            "location_hints, flight_number from sanitized lost and found text as JSON."
                        ),
                    },
                    {"role": "user", "content": mask_sensitive_text(text) or ""},
                ],
                temperature=0,
            )
            await ai_usage_service.record(
                "extract_structured_attributes",
                self.settings.azure_openai_chat_deployment,
                response.usage,
            )
            data = json.loads(response.choices[0].message.content or "{}")
        else:
            data = self._local_extract(text)
        await cache_service.set_json(key, data, self.settings.cache_ai_ttl_seconds)
        return data

    async def generate_embedding(self, text: str) -> tuple[str, list[float]]:
        key = self._cache_key("embed", text)
        cached = await cache_service.get_json(key)
        if cached:
            return cached["vector_id"], cached["embedding"]
        if self.settings.use_azure_services and self.settings.azure_openai_embedding_deployment:
            client = await self._client()
            response = await client.embeddings.create(
                model=self.settings.azure_openai_embedding_deployment,
                input=mask_sensitive_text(text) or "",
            )
            await ai_usage_service.record(
                "generate_embedding",
                self.settings.azure_openai_embedding_deployment,
                response.usage,
                is_embedding=True,
            )
            embedding = response.data[0].embedding
        else:
            embedding = self._local_embedding(text)
        vector_id = f"vec-{hashlib.sha256(json.dumps(embedding[:16]).encode()).hexdigest()[:16]}"
        await cache_service.set_json(
            key,
            {"vector_id": vector_id, "embedding": embedding},
            self.settings.cache_ai_ttl_seconds,
        )
        return vector_id, embedding

    async def summarize_match_evidence(self, lost_text: str, found_text: str, score_breakdown: dict[str, Any]) -> str:
        payload = json.dumps({"lost": lost_text, "found": found_text, "score": score_breakdown}, default=str)
        key = self._cache_key("summary", payload)
        cached = await cache_service.get_json(key)
        if cached:
            return cached["value"]
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            client = await self._client()
            response = await client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                messages=[
                    {"role": "system", "content": "Summarize match evidence for airport staff. Do not reveal unnecessary PII."},
                    {"role": "user", "content": mask_sensitive_text(payload) or ""},
                ],
                temperature=0.2,
            )
            await ai_usage_service.record(
                "summarize_match_evidence",
                self.settings.azure_openai_chat_deployment,
                response.usage,
            )
            value = response.choices[0].message.content or ""
        else:
            score = score_breakdown.get("match_score", 0)
            value = (
                f"Candidate scored {score:.1f}/100. Similarity comes from category, description, "
                "color, location, time, flight, and identifier rules. Staff approval is required before release."
            )
        await cache_service.set_json(key, {"value": value}, self.settings.cache_ai_ttl_seconds)
        return value

    async def summarize_graph_context(self, context: dict[str, Any], question: str | None = None) -> str:
        safe_context = mask_sensitive_text(json.dumps(context, default=str)) or "{}"
        payload = json.dumps({"context": safe_context, "question": question or "Explain graph evidence."}, default=str)
        key = self._cache_key("graph-summary", payload)
        cached = await cache_service.get_json(key)
        if cached:
            return cached["value"]
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            client = await self._client()
            response = await client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You explain graph RAG evidence for airport lost-and-found staff. "
                            "Use only the supplied graph nodes, edges, evidence, and risk signals. "
                            "Do not reveal unnecessary PII. Be concise and operational."
                        ),
                    },
                    {"role": "user", "content": payload},
                ],
                temperature=0.2,
            )
            await ai_usage_service.record(
                "summarize_graph_context",
                self.settings.azure_openai_chat_deployment,
                response.usage,
            )
            value = response.choices[0].message.content or ""
        else:
            signals = context.get("risk_signals") or []
            evidence = context.get("evidence") or []
            value = "Graph context connects the report, found item, custody, claims, labels, and audit activity. "
            if evidence:
                value += "Key evidence: " + "; ".join(str(item) for item in evidence[:4]) + ". "
            if signals:
                value += "Risk signals: " + "; ".join(str(item) for item in signals[:4]) + ". "
            value += "Staff should use this as supporting context, not automatic approval."
        await cache_service.set_json(key, {"value": value}, self.settings.cache_ai_ttl_seconds)
        return value

    async def generate_passenger_follow_up_questions(self, collected_data: dict[str, Any]) -> list[str]:
        key = self._cache_key("followups", json.dumps(collected_data, sort_keys=True, default=str))
        cached = await cache_service.get_json(key)
        if cached:
            return cached["questions"]
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            client = await self._client()
            response = await client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an airport lost-and-found intake assistant. "
                            "Return JSON with a questions array of at most three concise follow-up questions. "
                            "Ask only for missing or unclear fields needed to create a lost item report. "
                            "Do not request unnecessary PII."
                        ),
                    },
                    {"role": "user", "content": json.dumps(collected_data, default=str)},
                ],
                temperature=0.2,
            )
            await ai_usage_service.record(
                "generate_passenger_follow_up_questions",
                self.settings.azure_openai_chat_deployment,
                response.usage,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            questions = [str(question) for question in data.get("questions", []) if question][:3]
            if questions:
                await cache_service.set_json(key, {"questions": questions}, self.settings.cache_ai_ttl_seconds)
                return questions
        required = [
            ("category", "What type of item did you lose?"),
            ("raw_description", "Can you describe the item, including any visible marks?"),
            ("lost_location", "Where in the airport do you think you lost it?"),
            ("lost_datetime", "When did you last have the item?"),
            ("contact_email", "What email should staff use for updates?"),
        ]
        questions = [prompt for field, prompt in required if not collected_data.get(field)]
        questions = questions[:3] or ["Would you like me to submit this lost-item report now?"]
        await cache_service.set_json(key, {"questions": questions}, self.settings.cache_ai_ttl_seconds)
        return questions

    def _local_extract(self, text: str) -> dict[str, Any]:
        lowered = (text or "").lower()
        category = next((name for name, words in CATEGORY_WORDS.items() if any(word in lowered for word in words)), None)
        color = next((word for word in COLOR_WORDS if re.search(rf"\b{word}\b", lowered)), None)
        flight = re.search(r"\b([A-Z]{2}\s?\d{2,4})\b", text or "", re.IGNORECASE)
        identifiers = re.findall(r"\b(?:sn|serial|imei|passport|id)[:#\s-]*([A-Z0-9-]{5,20})\b", text or "", re.IGNORECASE)
        brands = ["apple", "samsung", "dell", "hp", "lenovo", "sony", "bose", "nike", "adidas"]
        brand = next((brand.title() for brand in brands if brand in lowered), None)
        return {
            "item_type": category,
            "brand": brand,
            "model": None,
            "color": color,
            "unique_identifiers": [mask_sensitive_text(value) for value in identifiers],
            "location_hints": [],
            "flight_number": flight.group(1).upper().replace(" ", "") if flight else None,
        }

    def _local_embedding(self, text: str, size: int = 128) -> list[float]:
        tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
        vector = [0.0] * size
        for token in tokens:
            index = int(hashlib.sha256(token.encode()).hexdigest(), 16) % size
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 6) for value in vector]

    @staticmethod
    def text_similarity(left: str, right: str) -> float:
        return SequenceMatcher(None, (left or "").lower(), (right or "").lower()).ratio()


azure_openai_service = AzureOpenAIService()
