# Hybrid Graph RAG PDF Chat

Chat with a research PDF using a hybrid Graph RAG pipeline:

1. Parse a PDF into page-aware text.
2. Chunk the text for semantic retrieval.
3. Extract entities, relationships, metrics, aliases, and evidence with Azure OpenAI GPT-4o.
4. Store graph facts in Neo4j.
5. Store chunk embeddings in local ChromaDB.
6. Answer questions in Streamlit using both graph context and retrieved text chunks.

The included starter paper is `education-15-00343-v2.pdf`: **The Impact of Artificial Intelligence (AI) on Students' Academic Development**.

## Architecture

```text
app/
  main.py
  config.py
  models/
  prompts/
  services/
    pdf_parser.py
    chunker.py
    extractor.py
    entity_normalizer.py
    graph_store.py
    vector_store.py
    hybrid_retriever.py
    answer_generator.py
    pipeline.py
docs/
  GRAPH_SCHEMA.md
scripts/
  init_neo4j.py
  inspect_neo4j.py
  ingest_sample.py
  neo4j_schema.cypher
data/
  raw/
  processed/
  vector/
tests/
```

Intermediate artifacts are written as readable JSON:

- `data/raw/*_raw.json`
- `data/processed/*_chunks.json`
- `data/processed/*_extractions.json`

## Quick Start

### 1. Create an environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Bash:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure environment variables

PowerShell:

```powershell
Copy-Item .env.example .env
```

Bash:

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_CHAT_DEPLOYMENT=your-gpt-4o-deployment-name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your-text-embedding-3-small-deployment-name
```

Important: Azure uses **deployment names**, not necessarily raw model names. If your Azure embedding deployment is named `embedding-small`, set `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-small`.

### 3. Start Neo4j

Docker Compose:

```bash
docker compose up -d neo4j
```

This uses:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=graph-rag-password
NEO4J_DATABASE=neo4j
```

Neo4j Browser will be available at:

```text
http://localhost:7474
```

If you use Neo4j Desktop instead, create/start a DBMS and set `.env` to match its Bolt URI, username, password, and database name.

### 4. Initialize graph schema

```bash
python scripts/init_neo4j.py
```

To print the exact Cypher schema without connecting:

```bash
python scripts/init_neo4j.py --print-schema
```

The schema lives in `scripts/neo4j_schema.cypher` and is documented in `docs/GRAPH_SCHEMA.md`.

### 5. Ingest the sample paper

```bash
python scripts/ingest_sample.py --rebuild
```

`--rebuild` removes existing Neo4j records and Chroma chunks for the selected PDF before re-ingesting.

### 6. Inspect the graph

```bash
python scripts/inspect_neo4j.py
```

Optional PDF filter:

```bash
python scripts/inspect_neo4j.py --source-pdf education-15-00343-v2.pdf
```

### 7. Run Streamlit

```bash
streamlit run streamlit_app.py
```

Open:

```text
http://localhost:8501
```

Good demo questions:

- How does AI affect academic performance?
- What risks does the paper identify?
- What percentage of students use virtual assistants?
- What methods did the study use?

## Graph Schema

Every extracted entity has the shared `Entity` label plus one concept label:

- `Concept`
- `Actor`
- `Technology`
- `Outcome`
- `Risk`
- `Study`
- `Method`
- `Metric`

Supported semantic relationships:

- `IMPROVES`
- `INCREASES`
- `CAUSES`
- `RAISES`
- `USES`
- `INCLUDES`
- `STUDIES`
- `IDENTIFIES`
- `REPORTS`
- `RECOMMENDS`
- `ENABLES`

Important properties:

- Entity: `id`, `name`, `normalized_name`, `type`, `aliases`, `description`, `stats`, `source_pdf`, `page_numbers`, `confidence`, `evidence_chunk_ids`
- Relationship: `id`, `source_pdf`, `page_numbers`, `evidence`, `evidence_chunk_id`, `properties`, `confidence`
- Provenance: `(Document)-[:HAS_CHUNK]->(Chunk)` and `(Entity)-[:MENTIONED_IN]->(Chunk)`

## Retrieval Flow

At question time:

1. Azure GPT-4o extracts likely query entities/concepts.
2. Chroma retrieves semantically similar text chunks.
3. Neo4j retrieves graph neighborhoods around detected terms.
4. If graph retrieval is sparse, the retriever expands search terms from the top text chunks.
5. GPT-4o receives both graph triples and text evidence, then answers with page/chunk citations.

## Testing

Run:

```bash
python -m pytest
```

The tests avoid live Azure and Neo4j calls. Full ingestion/chat requires `.env` plus a running Neo4j instance.

## Notes And Limits

- OCR is not included. The current parser targets text-based PDFs like the included sample.
- Azure OpenAI is required for graph extraction, query term detection, embeddings, and answer generation.
- ChromaDB is local and persistent under `data/vector/`.
- If you switch embedding deployments after indexing, rebuild vectors:

```powershell
Remove-Item -Recurse -Force data/vector
python scripts/ingest_sample.py --rebuild
```

Bash:

```bash
rm -rf data/vector
python scripts/ingest_sample.py --rebuild
```
