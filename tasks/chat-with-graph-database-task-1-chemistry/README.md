# Chemistry Graph Chat

A local Streamlit app that connects to Neo4j and answers questions about a small chemistry graph by generating safe, read-only Cypher with GPT-4o.

## Setup

1. Create and activate a Python environment.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your Neo4j and OpenAI values.

   ```powershell
   Copy-Item .env.example .env
   ```

   The app does not need an embedding model for this version. It asks GPT-4o to produce Cypher, validates that query, runs it against Neo4j, and then asks GPT-4o to summarize the returned rows.

   For Azure OpenAI, set `OPENAI_PROVIDER=azure`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and `AZURE_OPENAI_DEPLOYMENT`. Azure mode uses Chat Completions because the Azure Responses API is not available in every region. The Azure deployment name is used as the model value.

3. Optional: seed the demo graph into your existing Neo4j database.

   ```powershell
   python scripts/seed_graph.py
   ```

4. Run the app.

   ```powershell
   streamlit run app.py
   ```

## Example Questions

- Which drugs treat diseases affecting humans?
- What compound is produced by C + O2?
- Which elements are reactants for methane?
- What organisms are affected by headache?

## Safety Model

The chat flow is read-only. The model can suggest a Cypher query, but the app validates it before execution:

- only one statement is allowed
- comments are rejected
- write/admin clauses are rejected
- unsafe `CALL` usage is rejected
- `RETURN` is required
- a safe `LIMIT` is enforced
- queries run through Neo4j read transactions

The seed script is the only project command that writes graph data.
