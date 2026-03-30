# Architecture

## System Overview
The app is a SQL-first hybrid RAG system. PostgreSQL is the source of truth for business answers, while retrieval gives the model enough schema and example-query context to generate better SQL.

## Request Flow
1. Streamlit captures the user question.
2. The service layer loads or rebuilds the local vector store.
3. The retriever returns the most relevant schema and example documents.
4. OpenAI `gpt-4o` generates one read-only PostgreSQL query.
5. The SQL validator blocks unsafe statements.
6. The app executes the validated SQL against Railway Postgres.
7. OpenAI summarizes the returned rows into a business-friendly answer.
8. Streamlit renders the answer, SQL, result rows, and retrieved sources.

## Main Components
- UI: `app.py`
- Config: `src/config/settings.py`
- Database access: `src/database/client.py`
- Table schema definitions: `src/database/schema.py`
- CSV bootstrap: `src/ingestion/loader.py`
- Retrieval corpus generation: `src/retrieval/documents.py`
- Embeddings: `src/retrieval/embeddings.py`
- Vector store: `src/retrieval/vector_store.py`
- Prompting: `src/services/prompting.py`
- SQL guardrails: `src/services/sql_validator.py`
- Pipeline orchestration: `src/services/rag_pipeline.py`

## Data Flow
- Input data starts in `csv/`.
- Bootstrap loads the CSVs into Postgres tables.
- Schema inspection reads the live database metadata.
- Schema and example documents are embedded into a local FAISS index.
- User questions retrieve the most relevant documents before SQL generation.

## Guardrails
- Only one SQL statement is allowed.
- Only `SELECT` statements are allowed.
- Common write and DDL verbs are blocked by pattern checks.
- Query results are limited to avoid oversized UI payloads.

