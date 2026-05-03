from __future__ import annotations

from app.models import GraphEvidence, TextEvidence
from app.services.hybrid_retriever import HybridRetriever


class FakeLLM:
    def chat_json(self, *args, **kwargs):
        return {"entities": ["Artificial Intelligence"], "concepts": ["Academic Performance"]}

    def chat_text(self, *args, **kwargs):
        return "AI improves academic performance based on the retrieved evidence."


class FakeGraphStore:
    def get_graph_evidence(self, terms, source_pdf=None, limit=25):
        return [
            GraphEvidence(
                relationship_type="IMPROVES",
                source_name="Artificial Intelligence",
                source_type="Technology",
                target_name="Academic Performance",
                target_type="Outcome",
                source_pdf=source_pdf,
                page_numbers=[6],
                confidence=0.9,
                chunk_id="chunk-1",
            )
        ]


class FakeVectorStore:
    def similarity_search(self, query, top_k=5, source_pdf=None):
        return [
            TextEvidence(
                chunk_id="chunk-1",
                source_pdf=source_pdf or "paper.pdf",
                page_numbers=[6],
                text="AI improves academic performance.",
                score=0.9,
            ),
            TextEvidence(
                chunk_id="chunk-1",
                source_pdf=source_pdf or "paper.pdf",
                page_numbers=[6],
                text="Duplicate evidence.",
                score=0.8,
            ),
        ]


def test_hybrid_retriever_deduplicates_text_evidence(test_settings):
    retriever = HybridRetriever(
        test_settings,
        FakeLLM(),
        FakeGraphStore(),
        FakeVectorStore(),
    )

    result = retriever.answer("How does AI affect academic performance?", source_pdf="paper.pdf")

    assert result.detected_entities == ["Artificial Intelligence", "Academic Performance"]
    assert len(result.graph_evidence) == 1
    assert len(result.text_evidence) == 1
    assert result.text_evidence[0].chunk_id == "chunk-1"


class SparseLLM(FakeLLM):
    def chat_json(self, *args, **kwargs):
        return {"entities": ["Unknown Topic"], "concepts": []}


class FallbackGraphStore:
    def __init__(self):
        self.calls = []

    def get_graph_evidence(self, terms, source_pdf=None, limit=25):
        self.calls.append(terms)
        if any("Virtual Assistants" in term or "Students" in term for term in terms):
            return [
                GraphEvidence(
                    relationship_type="USES",
                    source_name="Students",
                    source_type="Actor",
                    target_name="Virtual Assistants",
                    target_type="Technology",
                    source_pdf=source_pdf,
                    page_numbers=[7],
                    confidence=0.82,
                    chunk_id="chunk-virtual-assistants",
                )
            ]
        return []


class FallbackVectorStore:
    def similarity_search(self, query, top_k=5, source_pdf=None):
        return [
            TextEvidence(
                chunk_id="chunk-virtual-assistants",
                source_pdf=source_pdf or "paper.pdf",
                page_numbers=[7],
                text="Students use Virtual Assistants for academic activities.",
                score=0.88,
            )
        ]


def test_hybrid_retriever_expands_graph_terms_from_text_evidence(test_settings):
    graph_store = FallbackGraphStore()
    retriever = HybridRetriever(
        test_settings,
        SparseLLM(),
        graph_store,
        FallbackVectorStore(),
    )

    result = retriever.answer("What tools do students use?", source_pdf="paper.pdf")

    assert len(graph_store.calls) == 2
    assert result.graph_evidence[0].relationship_type == "USES"
    assert "Unknown Topic" in result.detected_entities
