from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class ConfigurationError(RuntimeError):
    """Raised when a required runtime setting is missing."""


def _load_dotenv(path: Path) -> None:
    """Small .env loader to avoid making import-time config depend on python-dotenv."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    raw_dir: Path
    processed_dir: Path
    vector_dir: Path
    sample_pdf_path: Path

    azure_openai_endpoint: str | None
    azure_openai_api_key: str | None
    azure_openai_api_version: str
    azure_openai_chat_deployment: str | None
    azure_openai_embedding_deployment: str | None

    neo4j_uri: str | None
    neo4j_username: str
    neo4j_password: str | None
    neo4j_database: str

    chroma_collection: str
    chunk_target_chars: int
    chunk_overlap_chars: int
    extraction_max_chars: int
    retrieval_top_k: int
    graph_limit: int

    @property
    def azure_chat_configured(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_chat_deployment
        )

    @property
    def azure_embeddings_configured(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_embedding_deployment
        )

    @property
    def neo4j_configured(self) -> bool:
        return bool(self.neo4j_uri and self.neo4j_username and self.neo4j_password)

    def require_chat(self) -> None:
        if not self.azure_chat_configured:
            raise ConfigurationError(
                "Azure OpenAI chat is not configured. Set AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_CHAT_DEPLOYMENT."
            )

    def require_embeddings(self) -> None:
        if not self.azure_embeddings_configured:
            raise ConfigurationError(
                "Azure OpenAI embeddings are not configured. Set AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_EMBEDDING_DEPLOYMENT."
            )

    def require_neo4j(self) -> None:
        if not self.neo4j_configured:
            raise ConfigurationError(
                "Neo4j is not configured. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
            )


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {value!r}.") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[1]
    _load_dotenv(project_root / ".env")

    data_dir = project_root / "data"
    sample_pdf = Path(os.getenv("SAMPLE_PDF_PATH", "education-15-00343-v2.pdf"))
    if not sample_pdf.is_absolute():
        sample_pdf = project_root / sample_pdf

    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        raw_dir=data_dir / "raw",
        processed_dir=data_dir / "processed",
        vector_dir=data_dir / "vector",
        sample_pdf_path=sample_pdf,
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_openai_chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_openai_embedding_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_username=os.getenv("NEO4J_USERNAME", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "pdf_chunks"),
        chunk_target_chars=_int_env("CHUNK_TARGET_CHARS", 1800),
        chunk_overlap_chars=_int_env("CHUNK_OVERLAP_CHARS", 250),
        extraction_max_chars=_int_env("EXTRACTION_MAX_CHARS", 9000),
        retrieval_top_k=_int_env("RETRIEVAL_TOP_K", 5),
        graph_limit=_int_env("GRAPH_LIMIT", 25),
    )

