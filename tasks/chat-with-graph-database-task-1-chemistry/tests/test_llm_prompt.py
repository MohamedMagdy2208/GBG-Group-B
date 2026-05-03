from __future__ import annotations

from chemgraph_chat.llm import CYPHER_FEW_SHOTS


def test_cypher_few_shots_cover_core_graph_patterns() -> None:
    assert "Which drugs treat diseases affecting humans?" in CYPHER_FEW_SHOTS
    assert "What compound is produced by C + O2?" in CYPHER_FEW_SHOTS
    assert "Which elements are reactants for methane?" in CYPHER_FEW_SHOTS
    assert "Which drugs use carbon dioxide?" in CYPHER_FEW_SHOTS
    assert "What organisms are affected by headache?" in CYPHER_FEW_SHOTS


def test_cypher_few_shots_prefer_case_insensitive_filters() -> None:
    assert CYPHER_FEW_SHOTS.count("toLower(") >= 10
    assert "(o:Organism {type:" not in CYPHER_FEW_SHOTS

