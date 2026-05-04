import asyncio

from app.services.azure_openai_service import azure_openai_service


def test_local_rerank_prefers_same_category_and_color() -> None:
    query = {
        "title": "Black iPhone 14",
        "category": "Phone",
        "color": "black",
        "location": "Terminal 2 Gate B12",
        "time": "2026-05-01T10:00:00",
        "flight": "MS123",
        "description": "Lost a black iphone 14 at gate B12, terminal 2",
    }
    candidates = [
        {
            "id": 1,
            "title": "Black smartphone",
            "category": "Phone",
            "color": "black",
            "location": "Terminal 2 Gate B12",
            "time": "2026-05-01T11:00:00",
            "flight": "MS123",
            "description": "Smartphone with cracked screen, dark case",
        },
        {
            "id": 2,
            "title": "Red passport",
            "category": "Passport",
            "color": "red",
            "location": "Security Checkpoint A",
            "time": "2026-05-01T11:00:00",
            "flight": None,
            "description": "Egyptian passport found at security",
        },
        {
            "id": 3,
            "title": "Phone in case",
            "category": "Phone",
            "color": None,
            "location": "Terminal 1",
            "time": "2026-05-01T09:00:00",
            "flight": None,
            "description": "Phone with leather case",
        },
    ]
    result = asyncio.run(azure_openai_service.rerank_candidates(query, candidates))
    assert set(result.keys()) == {1, 2, 3}
    assert result[1]["rerank_score"] > result[2]["rerank_score"]
    assert result[1]["rerank_score"] > result[3]["rerank_score"]
    assert all(0 <= row["rerank_score"] <= 100 for row in result.values())


def test_local_rerank_handles_empty_candidates() -> None:
    result = asyncio.run(azure_openai_service.rerank_candidates({"title": "x"}, []))
    assert result == {}


def test_local_rerank_score_is_deterministic() -> None:
    query = {"title": "Black bag", "category": "Bag", "color": "black", "description": "small black backpack"}
    candidates = [
        {"id": 1, "title": "Black backpack", "category": "Bag", "color": "black", "description": "small black backpack"},
    ]
    first = asyncio.run(azure_openai_service.rerank_candidates(query, candidates))
    second = asyncio.run(azure_openai_service.rerank_candidates(query, candidates))
    assert first[1]["rerank_score"] == second[1]["rerank_score"]
