# Chat with Database RAG

Streamlit application for asking business questions over a Railway-hosted PostgreSQL database using a SQL-first hybrid RAG workflow. The project loads the provided Chinook-style CSV files into Postgres, retrieves schema-aware context, asks OpenAI or Azure OpenAI `gpt-4o` to generate safe SQL, executes the query, and returns the answer with SQL and source evidence.

## Features
- Streamlit chat UI with session-based conversation history
- Railway Postgres bootstrap from the local `csv/` dataset
- Schema and example-query retrieval with a local FAISS vector store
- Read-only SQL validation before execution
- Answer cards that show the generated SQL, result rows, and retrieved sources
- Handoff-friendly docs for future engineers and other LLMs

## Stack
- `streamlit` for the UI
- `sqlalchemy` + `psycopg` for PostgreSQL access
- `pandas` for CSV ingestion
- `openai` for OpenAI and Azure OpenAI chat completion and embeddings
- `faiss-cpu` + `numpy` for local vector retrieval
- `pydantic` + `python-dotenv` for configuration
- `pytest` for lightweight tests

## Repository Map
- [app.py](app.py)
- [requirements.txt](requirements.txt)
- [src](src)
- [docs/architecture.md](docs/architecture.md)
- [docs/setup-and-run.md](docs/setup-and-run.md)
- [docs/code-walkthrough.md](docs/code-walkthrough.md)

## Quickstart
1. Change into this task folder and create a virtual environment.
2. Install dependencies:

```bash
cd "tasks/task 2"
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in:
   - `DATABASE_URL`
   - `OPENAI_PROVIDER`
   - `OPENAI_API_KEY`
   - `OPENAI_CHAT_MODEL`
   - `OPENAI_EMBEDDING_MODEL`
   - `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_VERSION` when using Azure OpenAI
4. Bootstrap the database:

```bash
python scripts/bootstrap_db.py
```

5. Run the app:

```bash
streamlit run app.py
```

## How It Works
1. CSV files in `csv/` are loaded into PostgreSQL if the target tables are missing.
2. The app inspects the live schema and creates retrieval documents for tables, relationships, and example SQL patterns.
3. Documents are embedded and stored in a local FAISS index.
4. For each question, the app retrieves the most relevant context, asks the LLM for one PostgreSQL `SELECT`, validates it, and executes it.
5. The model summarizes the returned rows for the business user.

## Security Notes
- Do not commit `.env` or any secret values.
- The OpenAI key previously pasted into chat should be rotated before public release.
- The SQL validator blocks write statements, but this project is still an MVP and should not be treated as a hardened production security boundary.

## Documentation
- [architecture.md](docs/architecture.md)
- [setup-and-run.md](docs/setup-and-run.md)
- [deployment.md](docs/deployment.md)
- [project-phases.md](docs/project-phases.md)
- [project-tasks.md](docs/project-tasks.md)
- [packages-and-libraries.md](docs/packages-and-libraries.md)
- [handoff-guide.md](docs/handoff-guide.md)
- [code-walkthrough.md](docs/code-walkthrough.md)

## Troubleshooting
- If `streamlit run app.py` fails at startup, confirm your `.env` file contains a valid `DATABASE_URL`.
- If chat answers report a missing API key, set `OPENAI_API_KEY`.
- If you are using Azure OpenAI, set `OPENAI_PROVIDER=azure` and `AZURE_OPENAI_ENDPOINT`.
- If retrieval fails, rebuild the vector store from the sidebar or rerun `python scripts/bootstrap_db.py`.
- If the database is already populated and you only want to refresh retrieval, use the sidebar `Rebuild Knowledge Base` action.
