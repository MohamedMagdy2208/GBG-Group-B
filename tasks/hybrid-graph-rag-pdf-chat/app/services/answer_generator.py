from __future__ import annotations

import logging
from pathlib import Path

from app.models import AnswerResult, GraphEvidence, TextEvidence
from app.services.azure_openai_client import AzureOpenAIService

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates grounded answers from graph and text evidence."""

    def __init__(self, llm: AzureOpenAIService):
        self.llm = llm
        self.system_prompt = _load_prompt("answer_generation.md")

    def generate(
        self,
        question: str,
        text_evidence: list[TextEvidence],
        graph_evidence: list[GraphEvidence],
        detected_entities: list[str],
    ) -> AnswerResult:
        prompt = self._build_prompt(question, text_evidence, graph_evidence, detected_entities)
        answer = self.llm.chat_text(self.system_prompt, prompt, temperature=0.1)
        return AnswerResult(
            answer=answer.strip(),
            question=question,
            text_evidence=text_evidence,
            graph_evidence=graph_evidence,
            detected_entities=detected_entities,
        )

    def _build_prompt(
        self,
        question: str,
        text_evidence: list[TextEvidence],
        graph_evidence: list[GraphEvidence],
        detected_entities: list[str],
    ) -> str:
        text_blocks = []
        for index, item in enumerate(text_evidence, start=1):
            pages = ", ".join(str(page) for page in item.page_numbers) or "unknown"
            text_blocks.append(
                f"Text Evidence T{index}\n"
                f"- chunk_id: {item.chunk_id}\n"
                f"- pages: {pages}\n"
                f"- relevance_score: {item.score}\n"
                f"- excerpt: {item.text}"
            )

        graph_blocks = []
        for index, item in enumerate(graph_evidence, start=1):
            pages = ", ".join(str(page) for page in item.page_numbers) or "unknown"
            graph_blocks.append(
                f"Graph Evidence G{index}\n"
                f"- triple: {item.source_name} -[{item.relationship_type}]-> {item.target_name}\n"
                f"- pages: {pages}\n"
                f"- chunk_id: {item.chunk_id}\n"
                f"- confidence: {item.confidence}\n"
                f"- evidence: {item.evidence or 'No evidence text stored.'}"
            )

        return (
            f"Question:\n{question}\n\n"
            f"Detected query entities/concepts:\n{detected_entities}\n\n"
            "Use the graph evidence for structured claims and the text evidence for "
            "verbatim grounding. Prefer claims supported by both. If graph and text "
            "disagree, trust the text excerpt and mention uncertainty.\n\n"
            f"Graph evidence:\n{chr(10).join(graph_blocks) or 'No graph evidence retrieved.'}\n\n"
            f"Text evidence:\n{chr(10).join(text_blocks) or 'No text evidence retrieved.'}\n\n"
            "Answer with concise citations using page numbers and chunk IDs, for example "
            "(pages 5-6, chunk abc)."
        )


def _load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parents[1] / "prompts" / name
    return path.read_text(encoding="utf-8")
