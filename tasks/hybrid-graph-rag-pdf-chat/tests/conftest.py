from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def sample_pdf(project_root: Path) -> Path:
    return project_root / "education-15-00343-v2.pdf"


@pytest.fixture()
def test_settings(tmp_path: Path, sample_pdf: Path) -> Settings:
    return Settings(
        project_root=tmp_path,
        data_dir=tmp_path / "data",
        raw_dir=tmp_path / "data" / "raw",
        processed_dir=tmp_path / "data" / "processed",
        vector_dir=tmp_path / "data" / "vector",
        sample_pdf_path=sample_pdf,
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="test-key",
        azure_openai_api_version="2024-02-15-preview",
        azure_openai_chat_deployment="gpt-4o",
        azure_openai_embedding_deployment="embedding",
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="password",
        neo4j_database="neo4j",
        chroma_collection=f"test_chunks_{tmp_path.name}".replace("-", "_"),
        chunk_target_chars=1200,
        chunk_overlap_chars=100,
        extraction_max_chars=4000,
        retrieval_top_k=3,
        graph_limit=10,
    )

