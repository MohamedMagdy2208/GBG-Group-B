# AI-Powered Lost & Found System for Airport Operations

An intelligent, automated matching engine that replaces the manual, paper-based lost-and-found process at airports. The system creates a **Semantic Bridge** between what a passenger *says* they lost and what airport staff *actually found* — even when descriptions use different words (e.g., "blue bag" vs. "navy suitcase", "broken expensive gold watch" vs. "Rolex with surface wear").

Built with **Azure AI Services**, **Python**, and **Streamlit** as part of **GBG Group B — NTI Academy Task 4**.

---

## Architecture

```
Passenger (Lost Report) ──► AI Extraction (GPT-4o) ──► Embeddings ──► Vector Search
                                                                            │
Staff (Found Item + Photo) ──► AI Vision ──► AI Extraction ──► Embeddings ──┘
                                                                            │
                                                                    Confidence Score
                                                                            │
                                                                Human Review Dashboard
                                                                            │
                                                              Passenger Notification
```

The system follows a **RAG-inspired (Retrieval-Augmented Generation)** pattern:
1. **Ingestion** — Passengers submit text/photos; staff photograph found items
2. **Extraction** — AI extracts structured attributes (category, color, brand, features)
3. **Vectorization** — Descriptions converted to 1536-dim embeddings
4. **Matching** — Hybrid search (vector + keyword) finds candidates; GPT-4o scores them
5. **Notification** — High-confidence matches trigger passenger alerts

---

## Azure Services Used

| Service | Package | Purpose |
|---------|---------|---------|
| Azure OpenAI (GPT-4o) | `openai` | Extract attributes, reason about matches |
| Azure OpenAI (text-embedding-3-small) | `openai` | Generate vector embeddings |
| Azure AI Vision (Image Analysis 4.0) | `azure-ai-vision-imageanalysis` | Analyze found item photos |
| Azure AI Document Intelligence | `azure-ai-documentintelligence` | Parse passenger forms/PDFs |
| Azure AI Search | `azure-search-documents` | Vector + hybrid search index |
| Azure Blob Storage | `azure-storage-blob` | Store item photos |

---

## Project Structure

```
task4-lost-found-system/
├── app.py                          # Main Streamlit app (5 pages)
├── ai_pipeline.py                  # Azure AI processing functions
├── database.py                     # SQLite CRUD operations
├── models.py                       # Pydantic data models
├── config.py                       # Configuration & env vars
├── setup_azure_search.py           # One-time search index setup
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── prompts/
│   ├── attribute_extraction.txt    # GPT-4o prompt for attribute extraction
│   └── match_reasoning.txt         # GPT-4o prompt for match scoring
├── data/
│   └── lost_found.db               # SQLite database (auto-created)
├── uploads/                        # Item photos stored here
└── README.md                       # This file
```

---

## Setup

### 1. Clone & Install Dependencies

```bash
cd task4-lost-found-system
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and fill in your Azure credentials
```

> **Note:** If you don't have Azure credentials, the app runs in **Demo Mode** with simulated AI responses and pre-seeded sample data. All UI features are fully functional.

### 3. (Optional) Set Up Azure AI Search Index

Only needed if you have Azure AI Search credentials:

```bash
python setup_azure_search.py
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Application Pages

| Page | Description |
|------|-------------|
| **Report Lost Item** | Passenger submits a lost item report with description, category, photo |
| **Register Found Item** | Staff uploads a photo of a found item; AI auto-extracts attributes |
| **Check Matches** | Staff dashboard to run AI matching and confirm/reject results |
| **Analytics Dashboard** | Charts: top categories, high-risk zones, resolution time, KPIs |
| **Notifications** | Log of passenger notifications with simulation capability |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_GPT4O` | GPT-4o deployment name (default: `gpt-4o`) |
| `AZURE_OPENAI_DEPLOYMENT_EMBEDDING` | Embedding model deployment (default: `text-embedding-3-small`) |
| `AZURE_VISION_ENDPOINT` | Azure AI Vision endpoint URL |
| `AZURE_VISION_KEY` | Azure AI Vision API key |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint URL |
| `AZURE_SEARCH_KEY` | Azure AI Search admin key |
| `AZURE_SEARCH_INDEX_NAME` | Search index name (default: `lost-found-items`) |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Document Intelligence endpoint |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | Document Intelligence key |
| `AZURE_BLOB_CONNECTION_STRING` | Azure Blob Storage connection string |
| `AZURE_BLOB_CONTAINER_NAME` | Blob container name (default: `lost-found-photos`) |

---

## Confidence Thresholds

| Score | Color | Action |
|-------|-------|--------|
| >= 85% | Green | Auto-flag for notification |
| 60% - 84% | Yellow | Needs human review |
| < 60% | Red | Low probability — keep searching |

---

## Demo Data

The system auto-seeds 5 sample lost reports and 5 found items on first run:
- **Lost:** wallet (Montblanc), laptop (MacBook), watch (gold/Rolex), luggage (Samsonite), headphones (AirPods)
- **Found:** matching items with realistic staff descriptions and locations

---

## Team

**GBG Group B — NTI Academy**
