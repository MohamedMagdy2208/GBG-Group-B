from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.models import AnswerResult, GraphEvidence, TextEvidence
from app.services.answer_generator import AnswerGenerator
from app.services.azure_openai_client import AzureOpenAIService
from app.services.graph_store import Neo4jGraphStore
from app.services.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines query entity detection, graph retrieval, vector retrieval, and answering."""

    def __init__(
        self,
        settings: Settings,
        llm: AzureOpenAIService,
        graph_store: Neo4jGraphStore,
        vector_store: ChromaVectorStore,
    ):
        self.settings = settings
        self.llm = llm
        self.graph_store = graph_store
        self.vector_store = vector_store
        self.answer_generator = AnswerGenerator(llm)
        self.query_prompt = _load_prompt("query_entity_detection.md")

    def answer(self, question: str, source_pdf: str | None = None) -> AnswerResult:
        detected_terms = self.detect_terms(question)
        text_evidence = self.vector_store.similarity_search(
            question,
            top_k=self.settings.retrieval_top_k,
            source_pdf=source_pdf,
        )
        text_evidence = _dedupe_text_evidence(text_evidence)
        graph_evidence = self.graph_store.get_graph_evidence(
            detected_terms,
            source_pdf=source_pdf,
            limit=self.settings.graph_limit,
        )
        if not graph_evidence and text_evidence:
            expanded_terms = _unique(detected_terms + _keywords_from_text_evidence(text_evidence))
            graph_evidence = self.graph_store.get_graph_evidence(
                expanded_terms,
                source_pdf=source_pdf,
                limit=self.settings.graph_limit,
            )
            detected_terms = expanded_terms
        graph_evidence = _dedupe_graph_evidence(graph_evidence)
        return self.answer_generator.generate(
            question=question,
            text_evidence=text_evidence,
            graph_evidence=graph_evidence,
            detected_entities=detected_terms,
        )

    def detect_terms(self, question: str) -> list[str]:
        try:
            payload = self.llm.chat_json(self.query_prompt, f"Question: {question}", temperature=0.0)
            terms = _terms_from_payload(payload)
            if terms:
                return terms
        except Exception:
            logger.warning("Query entity detection failed; using keyword fallback", exc_info=True)
        return _keyword_fallback(question)


def _terms_from_payload(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("entities", "concepts", "keywords"):
        item = payload.get(key, [])
        if isinstance(item, list):
            values.extend(str(value) for value in item if str(value).strip())
    return _unique(values)[:8]


def _keyword_fallback(question: str) -> list[str]:
    stopwords = {
        "what",
        "which",
        "where",
        "when",
        "does",
        "about",
        "paper",
        "study",
        "students",
        "student",
        "using",
        "used",
        "with",
        "from",
        "that",
        "this",
        "have",
        "were",
        "their",
        "identify",
        "identified",
    }
    words = re.findall(r"[A-Za-z][A-Za-z-]{2,}", question.lower())
    terms = [word for word in words if word not in stopwords]
    if "ai" in question.lower() or "artificial intelligence" in question.lower():
        terms.insert(0, "Artificial Intelligence")
    return _unique(terms)[:8]


def _keywords_from_text_evidence(items: list[TextEvidence]) -> list[str]:
    joined = " ".join(item.text[:600] for item in items)
    candidates = re.findall(r"\b[A-Z][A-Za-z][A-Za-z -]{2,}\b", joined)
    short_terms = []
    for phrase in candidates:
        cleaned = re.sub(r"\s+", " ", phrase).strip(" .,;:()[]")
        if 3 <= len(cleaned) <= 60:
            short_terms.append(cleaned)
    return _unique(short_terms)[:8]


def _dedupe_text_evidence(items: list[TextEvidence]) -> list[TextEvidence]:
    seen: set[str] = set()
    deduped: list[TextEvidence] = []
    for item in items:
        if item.chunk_id in seen:
            continue
        seen.add(item.chunk_id)
        deduped.append(item)
    return deduped


def _dedupe_graph_evidence(items: list[GraphEvidence]) -> list[GraphEvidence]:
    seen: set[tuple[str, str, str, str | None]] = set()
    deduped: list[GraphEvidence] = []
    for item in items:
        key = (
            item.source_name.lower(),
            item.relationship_type,
            item.target_name.lower(),
            item.chunk_id,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parents[1] / "prompts" / name
    return path.read_text(encoding="utf-8")
