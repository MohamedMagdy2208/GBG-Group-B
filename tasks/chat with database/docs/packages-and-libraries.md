# Packages and Libraries

## `streamlit`
Used for the app UI. It provides the chat input, sidebar actions, expanders, and session state needed for a fast MVP interface.

## `pandas`
Used during ingestion to read CSV files, normalize null values, and bulk insert tabular data into the database.

## `sqlalchemy`
Used for database engine management, schema creation, metadata definitions, schema inspection, and query execution.

## `psycopg[binary]`
Used as the PostgreSQL driver under SQLAlchemy. The binary build keeps local setup simpler.

## `openai`
Used for two tasks:
- generating SQL and answer summaries with `gpt-4o`
- generating embeddings with `text-embedding-3-small`

## `faiss-cpu`
Used to store and search embedding vectors locally. It keeps retrieval lightweight and fast for a single-app deployment.

## `numpy`
Used as the numeric container for embedding vectors before they are inserted into FAISS.

## `python-dotenv`
Used to load environment variables from `.env` during local development.

## `pydantic`
Used to validate and type application settings loaded from the environment.

## `pytest`
Used for unit tests and smoke-level validation of core logic.

