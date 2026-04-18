# 🎵 Chinook SQL Chatbot — Chat with Databases

A production-ready Streamlit chatbot that converts **natural language questions** into **PostgreSQL queries** using **LangChain + Azure OpenAI (GPT-4o)** with **34 hand-crafted few-shot examples** — including Recursive CTEs, Window Functions, specific-person lookups, unavailable-data handling, analytics patterns, and multi-table JOINs. It executes queries against the Chinook music database and returns clear, natural language answers.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.41-red)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![LangChain](https://img.shields.io/badge/LangChain-1.2-orange)
![Tests](https://img.shields.io/badge/Tests-70%2F70_Passed-brightgreen)

---

## 📌 Features

- **Natural Language to SQL** — Ask questions in plain English, get accurate PostgreSQL queries
- **Few-Shot Prompting** — 34 curated examples covering simple SELECTs, JOINs, subqueries, HAVING, person lookups, unavailable-data handling, analytics patterns, Window Functions (RANK, PARTITION BY), and Recursive CTEs
- **Optional Embedding Retrieval** — Selects the most relevant few-shot examples with Azure OpenAI embeddings when enabled
- **Chat History Context** — Uses recent conversation turns to resolve follow-up questions without weakening SQL safety rules
- **Read-Only Security** — All write operations (DROP, DELETE, INSERT, UPDATE, ALTER, CREATE, TRUNCATE) are blocked at multiple layers
- **Input Validation** — Prompt injection protection, max character limits
- **Schema Viewer** — Sidebar shows all tables and columns from the live database
- **Clickable Examples** — 6 pre-built example questions in the sidebar
- **Collapsible SQL** — Generated SQL shown in expandable sections, not cluttering the chat
- **Smart Error Handling** — Friendly messages when queries fail, with suggestions to rephrase
- **Result Row Limiting** — Large query results capped at 50 rows to prevent token overflow
- **Schema Caching** — Database schema cached for 1 hour (not fetched on every query)
- **Query Timeout** — 30-second timeout on SQL execution to prevent long-running queries

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────────────────────────┐
│   User       │────▶│  Streamlit UI                     │
│  (Browser)   │◀────│  - Chat interface                 │
└──────────────┘     │  - Sidebar (schema + examples)    │
                     └──────────┬───────────────────────┘
                                │
                     ┌──────────▼───────────────────────┐
                     │  LangChain Pipeline               │
                     │                                   │
                     │  1. Few-Shot Prompt (34 examples)  │
                     │  2. Azure OpenAI GPT-4o            │
                     │  3. SQL Validation (read-only)     │
                     │  4. Query Execution (PostgreSQL)   │
                     │  5. Natural Language Response       │
                     └──────────┬───────────────────────┘
                                │
                     ┌──────────▼───────────────────────┐
                     │  PostgreSQL (Railway)              │
                     │  11 tables · 15,607 total rows    │
                     │  Chinook Music Database            │
                     └──────────────────────────────────┘
```

---

## 📁 Project Structure

```
chinook-chatbot/
├── app.py                  # Streamlit entry point (UI + chat logic)
├── src/
│   ├── __init__.py
│   ├── config.py           # Environment variables & constants
│   ├── database.py         # DB connection, schema caching, query execution
│   ├── history.py          # Compact chat history formatting for follow-ups
│   ├── prompts.py          # Few-shot prompt builder & response template
│   ├── retrieval.py        # Optional embedding-based few-shot selection
│   ├── chains.py           # LangChain chains (SQL generation + NL response)
│   └── utils.py            # SQL cleaning, validation, input checks
├── data/
│   ├── fewshots.json       # 34 few-shot SQL examples
│   └── csv/                # 11 Chinook CSV data files
├── scripts/
│   ├── deploy_db.py        # Load CSVs → PostgreSQL
│   └── deploy_azure.sh     # Full Azure deployment script
├── tests/
│   ├── test_utils.py       # Unit tests (55 tests)
│   ├── test_integration.py # Integration tests (9 tests)
│   ├── test_benchmark.py   # LLM benchmark (12 queries)
│   └── test_full_app.py    # Complete test suite (70 tests)
├── .env.example            # Required environment variables template
├── .gitignore
├── requirements.txt        # Pinned Python dependencies
├── Dockerfile              # Production container config
└── README.md
```

---

## 🗄️ Database Schema (Chinook)

| Table | Rows | Description |
|-------|------|-------------|
| Album | 347 | Music albums |
| Artist | 275 | Music artists |
| Customer | 59 | Store customers |
| Employee | 8 | Company employees (hierarchical) |
| Genre | 25 | Music genres |
| Invoice | 412 | Customer invoices |
| InvoiceLine | 2,240 | Invoice line items |
| MediaType | 5 | Media formats |
| Playlist | 18 | Playlists |
| PlaylistTrack | 8,715 | Playlist-track associations |
| Track | 3,503 | Music tracks |

---

## ✅ Test Results

| Test Suite | Tests | Result |
|---|---|---|
| **Unit Tests** — SQL validation, cleaning, input checks | 55 | 55/55 ✅ |
| **Integration Tests** — DB connection, schema, security | 9 | 9/9 ✅ |
| **Benchmark Tests** — LLM accuracy across query types | 12 | 12/12 ✅ |
| **Full App Tests** — End-to-end correctness + edge cases | 70 | 70/70 ✅ |

**Performance:** ~2.5s average per query (Azure OpenAI GPT-4o)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Abdo1119/GBG-tasks.git
cd "GBG-tasks/Chat with databases Teams"
```

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your actual Azure OpenAI values.
# The default DATABASE_URL points to the local Docker PostgreSQL database below.
```

### 4. Start a local PostgreSQL database

```bash
docker compose up -d db
```

The local database URL is:

```bash
DATABASE_URL=postgresql://chinook:chinook@localhost:5432/chinook
```

### 5. Load data into PostgreSQL

```bash
python scripts/deploy_db.py
```

### 6. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_API_KEY` | ✅ | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | ✅ | API version (e.g., `2024-12-01-preview`) |
| `AZURE_OPENAI_DEPLOYMENT` | ✅ | Model deployment name (e.g., `gpt-4o`) |
| `USE_EMBEDDING_RETRIEVAL` | ❌ | Enable dynamic few-shot retrieval with embeddings (default: `false`) |
| `AZURE_OPENAI_EMBEDDING_API_VERSION` | ❌ | Embeddings API version (default: `2024-02-01`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | ❌ | Embedding deployment name (e.g., `text-embedding-3-small`) |
| `FEWSHOT_TOP_K` | ❌ | Number of examples retrieved when embeddings are enabled (default: `8`) |
| `DATABASE_URL` | ✅ | PostgreSQL connection string. For local Docker: `postgresql://chinook:chinook@localhost:5432/chinook` |
| `MAX_RESULT_ROWS` | ❌ | Max rows sent to the answer generator (default: `50`) |
| `MAX_CHAT_HISTORY_MESSAGES` | ❌ | Recent chat messages included for follow-up context (default: `6`) |
| `MAX_CHAT_HISTORY_CHARS` | ❌ | Max characters per history message before truncation (default: `1200`) |
| `LANGSMITH_TRACING` | ❌ | Enable LangSmith tracing (default: `true`) |
| `LANGSMITH_API_KEY` | ❌ | LangSmith API key |
| `LANGSMITH_PROJECT` | ❌ | LangSmith project name |

---

## 🐳 Docker Deployment

```bash
docker build -t chinook-chatbot .
docker run -p 8501:8501 --env-file .env chinook-chatbot
```

---

## ☁️ Azure Deployment

Full automated deployment to Azure (PostgreSQL Flexible Server + App Service):

```bash
export PG_ADMIN_PASSWORD='YourSecurePassword123!'
chmod +x scripts/deploy_azure.sh
./scripts/deploy_azure.sh
```

**Estimated monthly cost:** ~$30.50 (B1ms PostgreSQL + B1 App Service + Basic ACR)

See [scripts/deploy_azure.sh](scripts/deploy_azure.sh) for the full deployment script with step-by-step Azure CLI commands.

---

## 🛡️ Security

- **Read-only enforcement** — DROP, DELETE, INSERT, UPDATE, ALTER, CREATE, TRUNCATE all blocked
- **Input validation** — 500 character limit, SQL injection pattern detection
- **No hardcoded secrets** — All credentials loaded from environment variables
- **Query timeout** — 30-second max execution time
- **Result limiting** — Max 50 rows returned to prevent token overflow

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit |
| **LLM** | Azure OpenAI GPT-4o |
| **Orchestration** | LangChain |
| **Database** | PostgreSQL (Railway) |
| **Prompt Strategy** | Few-Shot Prompting (34 examples), optional embedding retrieval |
| **Containerization** | Docker |
| **Cloud** | Microsoft Azure |
| **Tracing** | LangSmith (optional) |

---

## 📝 Example Questions

| Question | Type |
|----------|------|
| "How many customers are in the USA?" | Simple COUNT + WHERE |
| "Find the top 5 customers by total spending" | JOIN + GROUP BY + LIMIT |
| "Which country generated the highest revenue?" | Aggregation + ORDER BY |
| "Rank customers by spending within each country" | Window Function (RANK + PARTITION BY) |
| "Find the hierarchy depth for each employee" | Recursive CTE |
| "Calculate total sales generated by each manager's team" | Recursive CTE + Aggregation |

---

*Built with LangChain, Azure OpenAI, and Streamlit*
