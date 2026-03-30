"""End-to-end service that powers chat with the database."""

from __future__ import annotations

from pathlib import Path

from src.config.settings import Settings
from src.database.client import DatabaseManager
from src.ingestion.loader import bootstrap_database, bootstrap_required
from src.retrieval.documents import build_all_documents
from src.retrieval.embeddings import build_embedder
from src.retrieval.vector_store import LocalVectorStore
from src.services.llm import OpenAIChatService
from src.services.prompting import build_answer_messages, build_sql_generation_messages
from src.services.sql_validator import validate_read_only_sql
from src.utils.types import QueryResponse, SourceItem


class ChatWithDatabaseService:
    """Coordinates retrieval, SQL generation, execution, and answer synthesis."""

    def __init__(self, settings: Settings, db: DatabaseManager, data_dir: Path):
        self.settings = settings
        self.db = db
        self.data_dir = data_dir
        self.embedder = build_embedder(settings)
        self.vector_store = LocalVectorStore(settings.vector_store_path, self.embedder)
        self.llm = OpenAIChatService(settings) if settings.openai_api_key_value else None

    def ensure_bootstrap(self, replace_existing: bool = False) -> dict:
        """Bootstrap database tables and refresh the vector store."""

        if replace_existing or bootstrap_required(self.db):
            result = bootstrap_database(self.db, self.data_dir, replace_existing=replace_existing)
        else:
            result = {"status": "skipped", "reason": "Database tables already exist."}
        self.refresh_knowledge_base()
        return result

    def refresh_knowledge_base(self) -> None:
        """Rebuild schema and example documents used by retrieval."""

        documents = build_all_documents(self.db.get_schema_snapshot())
        self.vector_store.build(documents)

    def ensure_knowledge_base(self) -> None:
        """Load the local vector store, or rebuild it if missing."""

        if not self.vector_store.load():
            self.refresh_knowledge_base()

    def answer_question(self, question: str) -> QueryResponse:
        """Answer a business question using retrieval, SQL, and a final summary step."""

        if not self.llm:
            return QueryResponse(
                answer="The app is missing OPENAI_API_KEY, so SQL generation is not available yet.",
                error="Missing OPENAI_API_KEY",
            )

        self.ensure_knowledge_base()
        try:
            retrieved_docs = self.vector_store.similarity_search(question, top_k=self.settings.top_k_docs)
        except Exception:
            self.refresh_knowledge_base()
            retrieved_docs = self.vector_store.similarity_search(question, top_k=self.settings.top_k_docs)
        source_items = [
            SourceItem(kind=doc.kind, title=doc.title, snippet=doc.text[:300]) for doc in retrieved_docs
        ]

        sql_messages = build_sql_generation_messages(
            question=question,
            retrieved_docs=retrieved_docs,
            max_rows=self.settings.max_result_rows,
        )
        generation = self.llm.complete_json(sql_messages)
        clarification_needed = self._extract_clarification_request(generation.get("clarification_needed"))
        if clarification_needed:
            return QueryResponse(answer=clarification_needed, sources=source_items)

        sql = validate_read_only_sql(generation.get("sql", ""))
        try:
            rows = self.db.execute_query(sql, limit=self.settings.max_result_rows)
        except Exception as first_error:
            retry_messages = sql_messages + [
                {
                    "role": "assistant",
                    "content": f"The previous SQL failed with: {first_error}. Return corrected JSON only.",
                }
            ]
            generation = self.llm.complete_json(retry_messages)
            sql = validate_read_only_sql(generation.get("sql", ""))
            rows = self.db.execute_query(sql, limit=self.settings.max_result_rows)

        answer = self.llm.complete_text(build_answer_messages(question, sql, rows))
        return QueryResponse(answer=answer, sql=sql, rows=rows, sources=source_items)

    @staticmethod
    def _extract_clarification_request(value: object) -> str | None:
        """Normalize common model outputs for clarification requests."""

        if value in (None, False):
            return None
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.lower() in {"", "false", "none", "null", "no"}:
                return None
            return normalized
        return str(value)
