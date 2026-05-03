from __future__ import annotations

import pytest

from chemgraph_chat.cypher_guard import CypherValidationError
from chemgraph_chat.llm import CypherPlan
from chemgraph_chat.pipeline import GraphChatService


class FakeAssistant:
    def __init__(self, plan: CypherPlan) -> None:
        self.plan = plan

    def generate_cypher(self, **_: object) -> CypherPlan:
        return self.plan

    def summarize_answer(self, **kwargs: object) -> str:
        rows = kwargs["rows"]
        return f"Answer from {rows}"


def test_pipeline_generates_validates_runs_and_summarizes() -> None:
    executed: dict[str, object] = {}

    def runner(query: str, parameters: dict[str, object]) -> list[dict[str, object]]:
        executed["query"] = query
        executed["parameters"] = parameters
        return [{"drug": "Paracetamol", "disease": "Fever"}]

    service = GraphChatService(
        assistant=FakeAssistant(
            CypherPlan(
                cypher="MATCH (drug:Drug)-[:TREATS]->(disease:Disease) RETURN drug.name AS drug, disease.name AS disease",
                parameters={},
                reason="Find drugs and treated diseases.",
            )
        ),
        schema_provider=lambda: "schema",
        query_runner=runner,
        max_rows=7,
    )

    result = service.ask("Which drugs treat diseases?")

    assert executed["query"] == (
        "MATCH (drug:Drug)-[:TREATS]->(disease:Disease) "
        "RETURN drug.name AS drug, disease.name AS disease LIMIT 7"
    )
    assert result.rows == [{"drug": "Paracetamol", "disease": "Fever"}]
    assert "Paracetamol" in result.answer


def test_pipeline_blocks_unsafe_generated_cypher_before_db_call() -> None:
    called = False

    def runner(_: str, __: dict[str, object]) -> list[dict[str, object]]:
        nonlocal called
        called = True
        return []

    service = GraphChatService(
        assistant=FakeAssistant(
            CypherPlan(
                cypher="MATCH (n) SET n.name = 'bad' RETURN n",
                parameters={},
                reason="Bad query.",
            )
        ),
        schema_provider=lambda: "schema",
        query_runner=runner,
    )

    with pytest.raises(CypherValidationError):
        service.ask("Change data")

    assert called is False

