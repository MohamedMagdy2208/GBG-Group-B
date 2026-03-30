# Project Tasks

## Foundation
- `TASK-001` Create root repo files
  Description: Add README, requirements, env example, and gitignore.
  Dependencies: None
  Acceptance criteria: Repo has the minimum onboarding files.
  Suggested label: `setup`

- `TASK-002` Create Python package structure
  Description: Add `src/`, `tests/`, and `scripts/` modules with clear ownership.
  Dependencies: `TASK-001`
  Acceptance criteria: Core folders exist and import cleanly.
  Suggested label: `architecture`

## Data Layer
- `TASK-003` Define Chinook schema metadata
  Description: Encode table definitions, keys, and relationships for the CSV dataset.
  Dependencies: `TASK-002`
  Acceptance criteria: Metadata can create the target database schema.
  Suggested label: `database`

- `TASK-004` Implement Postgres client
  Description: Add health checks, schema inspection, and query execution helpers.
  Dependencies: `TASK-002`
  Acceptance criteria: App can connect and introspect the configured database.
  Suggested label: `database`

- `TASK-005` Implement CSV bootstrap
  Description: Load all CSV files into the configured database.
  Dependencies: `TASK-003`, `TASK-004`
  Acceptance criteria: All expected tables load successfully.
  Suggested label: `ingestion`

## Retrieval and LLM
- `TASK-006` Build schema and example retrieval documents
  Description: Convert live schema data into retrievable context for SQL generation.
  Dependencies: `TASK-004`
  Acceptance criteria: Schema and example docs are generated.
  Suggested label: `rag`

- `TASK-007` Implement embeddings and vector store
  Description: Add OpenAI embeddings and a local FAISS-backed store.
  Dependencies: `TASK-006`
  Acceptance criteria: Similarity search returns relevant docs.
  Suggested label: `rag`

- `TASK-008` Implement SQL prompting and validation
  Description: Generate one safe PostgreSQL query and block mutations.
  Dependencies: `TASK-006`
  Acceptance criteria: Unsafe SQL is rejected and valid SQL is normalized.
  Suggested label: `llm`

- `TASK-009` Implement end-to-end RAG pipeline
  Description: Orchestrate retrieval, SQL generation, execution, retry, and summarization.
  Dependencies: `TASK-004`, `TASK-007`, `TASK-008`
  Acceptance criteria: The service returns answer, SQL, rows, and sources.
  Suggested label: `llm`

## Product Surface
- `TASK-010` Implement Streamlit UI
  Description: Build the chat screen, setup controls, and answer rendering.
  Dependencies: `TASK-009`
  Acceptance criteria: Users can initialize the DB and ask questions in the browser.
  Suggested label: `frontend`

## Quality and Handoff
- `TASK-011` Add automated tests
  Description: Cover SQL validation, retrieval docs, and vector store behavior.
  Dependencies: `TASK-006`, `TASK-007`, `TASK-008`
  Acceptance criteria: `pytest` passes.
  Suggested label: `testing`

- `TASK-012` Write deep handoff docs
  Description: Document setup, architecture, package rationale, and continuation guidance.
  Dependencies: `TASK-001` through `TASK-011`
  Acceptance criteria: Another engineer or LLM can continue the project confidently.
  Suggested label: `documentation`

