# Deployment Guide

## Goal
Deploy the Streamlit app with safe secret handling and a repeatable startup workflow.

## Required Secrets
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_CHAT_MODEL`
- `OPENAI_EMBEDDING_MODEL`

## Recommended Deployment Steps
1. Push the repository to GitHub.
2. Configure secrets in your deployment platform instead of committing them to the repo.
3. Install dependencies from `requirements.txt`.
4. Run the bootstrap script once against the target Postgres database.
5. Start Streamlit with `streamlit run app.py`.

## Railway Notes
- Keep Railway Postgres as the source of truth.
- Prefer running bootstrap once instead of reloading data on every app startup.
- If storage is ephemeral on the app host, rebuild the vector store on startup or move retrieval persistence to a managed store later.

## Public Repo Safety
- Commit `.env.example`, never `.env`.
- Rotate exposed credentials before publishing.
- Document all required variables in `README.md` and `docs/setup-and-run.md`.

## Future Hardening
- Move SQL validation to a stricter SQL parser
- Add authentication before exposing the app broadly
- Add observability and request logging
- Add rate limits and per-user query controls

