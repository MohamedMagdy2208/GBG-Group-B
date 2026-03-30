# Project Phases

## Phase 1: Foundation and Repo Scaffolding
Goal: Create the repo layout, dependency file, environment templates, and basic documentation.
Outputs: `README.md`, `requirements.txt`, `.env.example`, package skeleton, docs skeleton.
Acceptance criteria: A new contributor can clone the repo and understand the project shape.

## Phase 2: Railway/Postgres Integration and Ingestion
Goal: Connect to Postgres and load the CSV dataset into real tables.
Outputs: schema definitions, database client, ingestion loader, bootstrap script.
Acceptance criteria: All expected tables exist and row counts match the source CSV files.

## Phase 3: Retrieval and Embeddings
Goal: Build schema-aware retrieval documents and persist them locally for fast lookup.
Outputs: retrieval document generator, embedder abstraction, FAISS vector store.
Acceptance criteria: A query can retrieve relevant schema or example documents.

## Phase 4: SQL Generation and Guardrails
Goal: Generate useful PostgreSQL safely.
Outputs: prompting, SQL validator, LLM wrapper, retry-on-error path.
Acceptance criteria: Representative business questions produce valid read-only SQL.

## Phase 5: Streamlit Chat UI
Goal: Deliver an easy-to-use interface for non-technical users.
Outputs: chat input, response rendering, SQL/source expanders, setup controls.
Acceptance criteria: A user can bootstrap, ask questions, and inspect the answer artifacts.

## Phase 6: Testing and Validation
Goal: Protect the MVP against basic regressions.
Outputs: unit tests for SQL validation, document generation, and vector store behavior.
Acceptance criteria: `pytest` passes locally.

## Phase 7: Documentation and Handoff
Goal: Make the project understandable to future engineers and other LLMs.
Outputs: architecture, setup, package rationale, handoff, and code walkthrough docs.
Acceptance criteria: A new contributor can run and extend the project without guesswork.

## Phase 8: Deployment Polish
Goal: Prepare the repo for GitHub publishing and hosted execution.
Outputs: deployment guide, secret-handling guidance, public repo hygiene.
Acceptance criteria: The app can be deployed without committing secrets.

