# Code Walkthrough

## Root Entry Points

### `app.py`
- Sets up the Streamlit page.
- Builds one cached service object for the session.
- Renders sidebar controls for health check, bootstrap, and vector rebuild.
- Stores chat history in `st.session_state`.
- Calls the pipeline and renders answer artifacts.

### `scripts/bootstrap_db.py`
- Small CLI helper for first-time setup.
- Uses the same service layer as the Streamlit app so bootstrap behavior stays consistent.

## Configuration

### `src/config/settings.py`
- Loads `.env` values with `python-dotenv`.
- Validates runtime settings with `pydantic`.
- Keeps model names, row limits, and vector-store path configurable.

## Database Layer

### `src/database/schema.py`
- Encodes the known Chinook-style tables.
- Adds primary keys and foreign keys so the live database has useful relational metadata.
- Centralizes business notes that later feed retrieval context.

### `src/database/client.py`
- Owns the SQLAlchemy engine.
- Performs health checks.
- Runs read-only queries.
- Inspects tables, columns, and foreign keys for schema-aware prompting.

## Ingestion

### `src/ingestion/loader.py`
- Creates tables from the schema metadata.
- Reads CSV files with `pandas`.
- Inserts rows into the configured database.
- Skips already existing tables unless replacement is requested.

## Retrieval

### `src/retrieval/documents.py`
- Turns live schema metadata into natural-language table documents.
- Adds curated example business questions and SQL patterns.
- Produces the retrieval corpus used during SQL generation.

### `src/retrieval/embeddings.py`
- Uses OpenAI embeddings in normal operation.
- Provides a deterministic hashing embedder for tests or offline fallback.

### `src/retrieval/vector_store.py`
- Persists document embeddings locally using FAISS.
- Saves document metadata as JSON next to the FAISS index.
- Performs similarity search at question time.

## LLM and Query Services

### `src/services/sql_validator.py`
- Normalizes SQL.
- Rejects multi-statement and non-`SELECT` queries.
- Blocks common mutation and DDL verbs.

### `src/services/prompting.py`
- Builds the SQL-generation prompt with retrieved context.
- Builds the answer-summarization prompt from returned rows.

### `src/services/llm.py`
- Wraps the OpenAI chat completions API.
- Provides a JSON response path for SQL generation and a text path for answer summaries.

### `src/services/rag_pipeline.py`
- Orchestrates database bootstrap, retrieval refresh, SQL generation, execution, retry, and final answer synthesis.
- Returns a stable `QueryResponse` object that the UI can render directly.

## Shared Types

### `src/utils/types.py`
- Defines `SourceItem`, `QueryResponse`, and `RetrievalDocument`.
- Keeps the boundary between service logic and UI explicit.

## Tests

### `tests/test_sql_validator.py`
- Covers safe and unsafe SQL paths.

### `tests/test_documents.py`
- Verifies that retrieval corpus generation includes both schema and example documents.

### `tests/test_vector_store.py`
- Validates the local vector-store build, load, and search behavior.

## Notes on Code Explanation Depth
The code uses docstrings on modules and core functions so the source stays readable. Deeper explanations live here in markdown rather than as noisy inline comments. If a future contributor adds complex logic, the best pattern is to add a short code comment plus a deeper explanation in this document.
