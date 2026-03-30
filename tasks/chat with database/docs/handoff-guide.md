# Handoff Guide

## What This Repo Already Does
- Loads the Chinook-style CSV dataset into PostgreSQL
- Builds retrieval documents from the live schema
- Stores embeddings in a local FAISS index
- Uses OpenAI to generate and summarize SQL
- Serves the workflow through Streamlit

## Where to Extend It Safely
- Add richer retrieval documents in `src/retrieval/documents.py`
- Strengthen SQL safety in `src/services/sql_validator.py`
- Improve prompt strategy in `src/services/prompting.py`
- Add caching, retries, and observability in `src/services/rag_pipeline.py`
- Extend UI behavior in `app.py`

## Important Assumptions
- The dataset follows the Chinook-style schema represented in `src/database/schema.py`
- PostgreSQL is the main execution database
- The local vector store path is writable by the app host
- OpenAI is the initial provider

## Suggested Next Improvements
- Add a stricter SQL parser instead of regex-only validation
- Persist retrieval metadata in the database or another managed store
- Add integration tests against a disposable Postgres instance
- Add deployment automation and CI
- Add feedback collection and query history

## If Another LLM Continues This Project
- Read `README.md` first
- Read `docs/architecture.md` and `docs/code-walkthrough.md` next
- Confirm `.env` configuration before changing runtime behavior
- Keep the response contract stable unless the UI is updated at the same time
- Do not commit secrets or example credentials

