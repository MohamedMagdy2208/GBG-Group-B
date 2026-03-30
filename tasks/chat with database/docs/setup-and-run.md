# Setup and Run Guide

## Prerequisites
- Python 3.11+ recommended
- Access to a PostgreSQL database, such as Railway Postgres
- An OpenAI or Azure OpenAI key for `gpt-4o` and `text-embedding-3-small`

## Installation
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Configuration
Create `.env` from `.env.example` and set:

```env
DATABASE_URL=postgresql://username:password@host:port/database
OPENAI_PROVIDER=openai
OPENAI_API_KEY=your-rotated-key
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-12-01-preview
APP_ENV=development
BOOTSTRAP_ON_START=false
VECTOR_STORE_PATH=vector_store
TOP_K_DOCS=6
MAX_RESULT_ROWS=50
```

For Azure OpenAI, set:

```env
OPENAI_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Bootstrap the Database
This loads the CSV files into the target database and builds the retrieval index.

```bash
python scripts/bootstrap_db.py
```

## Run the Streamlit App
```bash
streamlit run app.py
```

## First-Run Workflow
1. Click `Health Check` in the sidebar.
2. Click `Initialize Database` if the tables do not exist yet.
3. Click `Rebuild Knowledge Base` if you changed the schema or want to refresh retrieval documents.
4. Ask a business question in the chat box.

## Example Questions
- Top 5 countries by sales
- Which customers spent the most money?
- What are the most purchased genres?
- Show tracks in playlist 1
- Which artists generated the most revenue?

## Troubleshooting
- Database connection error:
  Confirm `DATABASE_URL` is valid and reachable from your machine.
- Missing LLM functionality:
  Confirm `OPENAI_API_KEY` is set.
- Azure authentication or endpoint errors:
  Confirm `OPENAI_PROVIDER=azure`, the endpoint URL is correct, and the deployment names in `OPENAI_CHAT_MODEL` and `OPENAI_EMBEDDING_MODEL` match your Azure deployments.
- Empty retrieval store:
  Run `python scripts/bootstrap_db.py` or use the sidebar rebuild action.
- Existing database already loaded:
  The bootstrap step skips existing tables unless you extend it to force replace.
