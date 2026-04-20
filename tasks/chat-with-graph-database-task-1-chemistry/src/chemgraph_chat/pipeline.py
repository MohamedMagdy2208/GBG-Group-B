from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .cypher_guard import validate_readonly_cypher
from .llm import CypherPlan


class GraphAssistant(Protocol):
    def generate_cypher(
        self,
        *,
        question: str,
        schema_summary: str,
        history: list[dict[str, str]] | None = None,
    ) -> CypherPlan:
        ...

    def summarize_answer(
        self,
        *,
        question: str,
        cypher: str,
        rows: list[dict[str, Any]],
    ) -> str:
        ...


@dataclass(frozen=True)
class ChatResult:
    answer: str
    cypher: str
    parameters: dict[str, Any]
    reason: str
    rows: list[dict[str, Any]]


class GraphChatService:
    def __init__(
        self,
        *,
        assistant: GraphAssistant,
        schema_provider: Callable[[], str],
        query_runner: Callable[[str, dict[str, Any]], list[dict[str, Any]]],
        max_rows: int = 50,
    ) -> None:
        self.assistant = assistant
        self.schema_provider = schema_provider
        self.query_runner = query_runner
        self.max_rows = max_rows

    def ask(
        self,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResult:
        schema_summary = self.schema_provider()
        plan = self.assistant.generate_cypher(
            question=question,
            schema_summary=schema_summary,
            history=history,
        )
        safe = validate_readonly_cypher(
            plan.cypher,
            plan.parameters,
            max_rows=self.max_rows,
        )
        rows = self.query_runner(safe.query, safe.parameters)
        answer = self.assistant.summarize_answer(
            question=question,
            cypher=safe.query,
            rows=rows,
        )
        return ChatResult(
            answer=answer,
            cypher=safe.query,
            parameters=safe.parameters,
            reason=plan.reason,
            rows=rows,
        )

