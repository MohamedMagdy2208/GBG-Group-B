import hashlib
import inspect
import json
import logging
import math
import re
from difflib import SequenceMatcher
from types import SimpleNamespace
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.security import mask_sensitive_text
from app.services.ai_usage_service import ai_usage_service
from app.services.cache_service import cache_service


logger = logging.getLogger(__name__)


REASONING_OPERATIONS = {"summarize_match_evidence", "summarize_graph_context"}


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

    def _cache_key(self, prefix: str, payload: str, *, namespace: str | None = None) -> str:
        cache_payload = {
            "namespace": namespace or "default",
            "payload": mask_sensitive_text(payload or "") or "",
        }
        digest = hashlib.sha256(json.dumps(cache_payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"ai:{prefix}:{digest}"

    def _operation_cache_key(self, prefix: str, payload: str, operation: str) -> str:
        if not self.settings.use_azure_services:
            return self._cache_key(prefix, payload, namespace="local")
        route = self._route_for_operation(operation)
        return self._cache_key(prefix, payload, namespace=route["deployment"])

    async def _client(self, *, endpoint: str | None = None, api_key: str | None = None):
        from openai import AsyncAzureOpenAI

        resolved_endpoint = endpoint or self.settings.azure_openai_endpoint
        resolved_api_key = api_key or self._api_key_for_endpoint(resolved_endpoint)

        if self.settings.azure_use_managed_identity and not resolved_api_key:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            return AsyncAzureOpenAI(
                azure_endpoint=resolved_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.settings.azure_openai_api_version,
            )
        return AsyncAzureOpenAI(
            azure_endpoint=resolved_endpoint,
            api_key=resolved_api_key,
            api_version=self.settings.azure_openai_api_version,
        )

    async def _chat_client(self, route: dict[str, str | None] | None = None):
        return await self._client(
            endpoint=(route or {}).get("endpoint"),
            api_key=(route or {}).get("api_key"),
        )

    async def _embedding_client(self):
        return await self._client(
            endpoint=self.settings.azure_openai_embedding_endpoint,
            api_key=self.settings.azure_openai_embedding_api_key,
        )

    def _api_key_for_endpoint(self, endpoint: str | None) -> str | None:
        if self._same_endpoint(endpoint, self.settings.azure_openai_embedding_endpoint):
            return self.settings.azure_openai_embedding_api_key or self.settings.azure_openai_api_key
        return self.settings.azure_openai_api_key

    @staticmethod
    def _same_endpoint(left: str | None, right: str | None) -> bool:
        if not left or not right:
            return False
        return left.rstrip("/").lower() == right.rstrip("/").lower()

    def _route_for_operation(self, operation: str) -> dict[str, str | None]:
        route_name = "reasoning" if operation in REASONING_OPERATIONS else "fast"
        if route_name == "reasoning":
            deployment = self.settings.azure_openai_reasoning_deployment or self.settings.azure_openai_fast_deployment
            endpoint = self.settings.azure_openai_reasoning_endpoint or self.settings.azure_openai_fast_endpoint
            api_key = self.settings.azure_openai_reasoning_api_key or self.settings.azure_openai_fast_api_key
        elif route_name == "deep":
            deployment = self.settings.azure_openai_deep_reasoning_deployment
            endpoint = self.settings.azure_openai_deep_reasoning_endpoint
            api_key = self.settings.azure_openai_deep_reasoning_api_key
        else:
            deployment = self.settings.azure_openai_fast_deployment
            endpoint = self.settings.azure_openai_fast_endpoint
            api_key = self.settings.azure_openai_fast_api_key
        deployment = deployment or self.settings.azure_openai_chat_deployment
        endpoint = endpoint or self.settings.azure_openai_endpoint
        api_key = api_key or self._api_key_for_endpoint(endpoint)
        return {"name": route_name, "deployment": deployment, "endpoint": endpoint, "api_key": api_key}

    def route_deployments(self) -> dict[str, str | None]:
        return {
            "fast": self._route_for_operation("extract_structured_attributes")["deployment"],
            "reasoning": self._route_for_operation("summarize_match_evidence")["deployment"],
            "deep": self.settings.azure_openai_deep_reasoning_deployment,
            "embedding": self.settings.azure_openai_embedding_deployment,
        }

    def _should_use_responses_api(self, deployment: str | None) -> bool:
        if not self.settings.azure_openai_use_responses_api:
            return False
        deployment = (deployment or "").lower()
        return deployment.startswith("gpt-5")

    async def _generate_text(
        self,
        *,
        operation: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 350,
    ) -> str:
        route = self._route_for_operation(operation)
        deployment = route["deployment"]
        if self._should_use_responses_api(deployment):
            try:
                text, usage = await self._responses_text(
                    system_prompt,
                    user_prompt,
                    route=route,
                    json_mode=json_mode,
                    max_output_tokens=max_output_tokens,
                )
                await ai_usage_service.record(operation, deployment, usage)
                return text
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {400, 401, 404, 405}:
                    raise
                logger.warning(
                    "Responses API unavailable for deployment; trying Chat Completions",
                    extra={
                        "event": "responses_api_fallback",
                        "status_code": exc.response.status_code,
                        "deployment": deployment,
                        "route": route["name"],
                    },
                )

        return await self._chat_completions_text(
            operation=operation,
            route=route,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=json_mode,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    async def _chat_completions_text(
        self,
        *,
        operation: str,
        route: dict[str, str | None],
        system_prompt: str,
        user_prompt: str,
        json_mode: bool,
        temperature: float,
        max_output_tokens: int,
    ) -> str:
        client = await self._chat_client(route)
        deployment = route["deployment"]
        kwargs: dict[str, Any] = {
            "model": deployment,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if (deployment or "").lower().startswith("gpt-5"):
            kwargs["max_completion_tokens"] = max_output_tokens
        else:
            kwargs["temperature"] = temperature
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as exc:
            if "unsupported" not in str(exc).lower():
                raise
            text, usage = await self._responses_text(
                system_prompt,
                user_prompt,
                route=route,
                json_mode=json_mode,
                max_output_tokens=max_output_tokens,
            )
            await ai_usage_service.record(operation, deployment, usage)
            return text
        finally:
            await self._close_client(client)
        await ai_usage_service.record(operation, deployment, response.usage)
        return response.choices[0].message.content or ""

    async def _close_client(self, client: Any) -> None:
        close = getattr(client, "close", None) or getattr(client, "aclose", None)
        if not close:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    async def _responses_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        route: dict[str, str | None],
        json_mode: bool = False,
        max_output_tokens: int = 350,
    ) -> tuple[str, SimpleNamespace]:
        endpoint = route.get("endpoint")
        api_key = route.get("api_key") or self._api_key_for_endpoint(endpoint)
        deployment = route.get("deployment")
        if not endpoint or not api_key or not deployment:
            raise RuntimeError("Azure OpenAI endpoint and API key are required for Responses API calls")
        instruction = system_prompt
        if json_mode:
            instruction = f"{instruction}\nReturn only one valid JSON object. Do not wrap it in markdown."
        url = f"{endpoint.rstrip('/')}/openai/responses"
        body = {
            "model": deployment,
            "input": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_prompt},
            ],
            "max_output_tokens": max_output_tokens,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                params={"api-version": self.settings.azure_openai_responses_api_version},
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
        return self._extract_responses_text(payload), self._usage_from_response_payload(payload)

    @staticmethod
    def _extract_responses_text(payload: dict[str, Any]) -> str:
        if payload.get("output_text"):
            return str(payload["output_text"])
        chunks: list[str] = []
        for item in payload.get("output", []) or []:
            if isinstance(item, dict):
                for content in item.get("content", []) or []:
                    if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                        chunks.append(str(content.get("text") or ""))
        return "\n".join(chunk for chunk in chunks if chunk).strip()

    @staticmethod
    def _usage_from_response_payload(payload: dict[str, Any]) -> SimpleNamespace:
        usage = payload.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        completion_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens) or 0
        return SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        try:
            data = json.loads(text or "{}")
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text or "", re.DOTALL)
            data = json.loads(match.group(0)) if match else {}
        return data if isinstance(data, dict) else {}

    async def clean_item_description(self, text: str) -> str:
        key = self._operation_cache_key("clean", text, "clean_item_description")
        cached = await cache_service.get_json(key)
        if cached:
            return cached["value"]
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            value = await self._generate_text(
                operation="clean_item_description",
                system_prompt="Clean airport lost and found item descriptions. Remove unnecessary PII.",
                user_prompt=mask_sensitive_text(text) or "",
                temperature=0.1,
                max_output_tokens=120,
            )
            value = value or text
        else:
            value = " ".join((text or "").strip().split()).capitalize()
        await cache_service.set_json(key, {"value": value}, self.settings.cache_ai_ttl_seconds)
        return value

    async def extract_structured_attributes(self, text: str) -> dict[str, Any]:
        key = self._operation_cache_key("attrs", text, "extract_structured_attributes")
        cached = await cache_service.get_json(key)
        if cached:
            return cached
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            content = await self._generate_text(
                operation="extract_structured_attributes",
                system_prompt=(
                    "Extract item_type, brand, model, color, unique_identifiers, "
                    "location_hints, flight_number from sanitized lost and found text as JSON."
                ),
                user_prompt=mask_sensitive_text(text) or "",
                json_mode=True,
                temperature=0,
                max_output_tokens=220,
            )
            data = self._parse_json_object(content)
        else:
            data = self._local_extract(text)
        await cache_service.set_json(key, data, self.settings.cache_ai_ttl_seconds)
        return data

    async def generate_embedding(self, text: str) -> tuple[str, list[float]]:
        namespace = self.settings.azure_openai_embedding_deployment if self.settings.use_azure_services else "local"
        key = self._cache_key("embed", text, namespace=namespace)
        cached = await cache_service.get_json(key)
        if cached:
            return cached["vector_id"], cached["embedding"]
        if self.settings.use_azure_services and self.settings.azure_openai_embedding_deployment:
            client = await self._embedding_client()
            try:
                response = await client.embeddings.create(
                    model=self.settings.azure_openai_embedding_deployment,
                    input=mask_sensitive_text(text) or "",
                )
            finally:
                await self._close_client(client)
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
        key = self._operation_cache_key("summary", payload, "summarize_match_evidence")
        cached = await cache_service.get_json(key)
        if cached:
            return cached["value"]
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            value = await self._generate_text(
                operation="summarize_match_evidence",
                system_prompt="Summarize match evidence for airport staff. Do not reveal unnecessary PII.",
                user_prompt=mask_sensitive_text(payload) or "",
                temperature=0.2,
                max_output_tokens=180,
            )
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
        key = self._operation_cache_key("graph-summary", payload, "summarize_graph_context")
        cached = await cache_service.get_json(key)
        if cached:
            return cached["value"]
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            value = await self._generate_text(
                operation="summarize_graph_context",
                system_prompt=(
                    "You explain graph RAG evidence for airport lost-and-found staff. "
                    "Use only the supplied graph nodes, edges, evidence, and risk signals. "
                    "Do not reveal unnecessary PII. Be concise and operational."
                ),
                user_prompt=payload,
                temperature=0.2,
                max_output_tokens=220,
            )
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
        payload = json.dumps(collected_data, sort_keys=True, default=str)
        key = self._operation_cache_key("followups", payload, "generate_passenger_follow_up_questions")
        cached = await cache_service.get_json(key)
        if cached:
            return cached["questions"]
        if self.settings.use_azure_services and self.settings.azure_openai_chat_deployment:
            content = await self._generate_text(
                operation="generate_passenger_follow_up_questions",
                system_prompt=(
                    "You are an airport lost-and-found intake assistant. "
                    "Return JSON with a questions array of at most three concise follow-up questions. "
                    "Ask only for missing or unclear fields needed to create a lost item report. "
                    "Do not request unnecessary PII."
                ),
                user_prompt=json.dumps(collected_data, default=str),
                json_mode=True,
                temperature=0.2,
                max_output_tokens=180,
            )
            data = self._parse_json_object(content)
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

    def fallback_extract_structured_attributes(self, text: str) -> dict[str, Any]:
        return self._local_extract(text)

    def _local_embedding(self, text: str, size: int = 128) -> list[float]:
        tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
        vector = [0.0] * size
        for token in tokens:
            index = int(hashlib.sha256(token.encode()).hexdigest(), 16) % size
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 6) for value in vector]

    def fallback_embedding(self, text: str) -> tuple[str, list[float]]:
        embedding = self._local_embedding(text)
        vector_id = f"local-vec-{hashlib.sha256(json.dumps(embedding[:16]).encode()).hexdigest()[:16]}"
        return vector_id, embedding

    @staticmethod
    def text_similarity(left: str, right: str) -> float:
        return SequenceMatcher(None, (left or "").lower(), (right or "").lower()).ratio()


azure_openai_service = AzureOpenAIService()
