from __future__ import annotations

from app.models import GraphEvidence, TextEvidence
from app.services.answer_generator import AnswerGenerator


class CapturingLLM:
    def __init__(self):
        self.prompt = ""

    def chat_text(self, system_prompt, user_prompt, temperature=0.1):
        self.prompt = user_prompt
        return "Grounded answer."


def test_answer_prompt_includes_graph_and_text_grounding():
    llm = CapturingLLM()
    generator = AnswerGenerator(llm)

    result = generator.generate(
        question="What improves academic performance?",
        detected_entities=["Artificial Intelligence", "Academic Performance"],
        graph_evidence=[
            GraphEvidence(
                relationship_type="IMPROVES",
                source_name="Artificial Intelligence",
                target_name="Academic Performance",
                page_numbers=[5],
                chunk_id="chunk-a",
                confidence=0.9,
                evidence="AI improves academic performance.",
            )
        ],
        text_evidence=[
            TextEvidence(
                chunk_id="chunk-a",
                source_pdf="paper.pdf",
                page_numbers=[5],
                text="82.4% think AI improves academic performance.",
                score=0.91,
            )
        ],
    )

    assert result.answer == "Grounded answer."
    assert "Graph Evidence G1" in llm.prompt
    assert "Text Evidence T1" in llm.prompt
    assert "Prefer claims supported by both" in llm.prompt

