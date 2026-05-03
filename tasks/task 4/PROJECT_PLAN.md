# AI-Powered Lost & Found System — Complete Project Plan & Documentation

## GBG Group B — NTI Academy — Task 4

---

## 1. The Problem (المشكلة)

Airports handle **thousands** of lost items daily. The current process is:

```
❌ CURRENT (Manual) PROCESS:
1. Passenger fills out a PAPER form: "I lost my blue bag near gate B12"
2. Staff manually registers found items in a spreadsheet
3. Staff MANUALLY reads through ALL lost reports trying to match
4. If the passenger says "blue bag" but staff wrote "navy suitcase" → NO MATCH
5. Items pile up unclaimed. Passengers never get their stuff back.
```

**The core problem:** Humans describe the same item using **different words**.
- "blue bag" vs. "navy suitcase"
- "broken expensive gold watch" vs. "Rolex Submariner with surface wear"
- "scratched silver laptop" vs. "MacBook Pro with surface damage"

---

## 2. The Solution (الحل)

We built an **AI-Powered Matching Engine** that creates a **Semantic Bridge** — it understands that different words can mean the same thing.

```
✅ OUR AI PROCESS:
1. Passenger types: "I lost my expensive gold watch with scratches"
2. AI (GPT-4o) understands → category: watch, color: gold, brand: probably Rolex
3. Staff photographs a found watch → AI Vision extracts attributes
4. AI generates vector embeddings (mathematical meaning representations)
5. System runs hybrid search (vector + keyword) across ALL found items
6. GPT-4o acts as a "claims adjuster" and scores each match (0-100%)
7. Staff confirms/rejects with one click → Passenger gets notified automatically
```

---

## 3. Architecture (البنية التقنية)

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PASSENGER SIDE                           │
│                                                             │
│   Passenger fills form:                                     │
│   "I lost my scratched gold watch near Security"            │
│          │                                                  │
│          ▼                                                  │
│   ┌─────────────────┐                                       │
│   │  GPT-4o Extract │──► category: watch                    │
│   │  Attributes     │    color: gold                        │
│   │                 │    brand: Rolex (inferred!)            │
│   │                 │    features: ["scratches on face"]     │
│   └────────┬────────┘                                       │
│            │                                                │
│            ▼                                                │
│   ┌─────────────────┐                                       │
│   │ text-embedding-  │──► 1536-dimensional vector            │
│   │ 3-small          │    (mathematical representation      │
│   │                  │     of the MEANING)                   │
│   └────────┬─────────┘                                      │
│            │                                                │
└────────────┼────────────────────────────────────────────────┘
             │
             ▼
    ┌──────────────────┐
    │  Azure AI Search │ ◄── Hybrid Search:
    │  Vector Index    │     1. Vector similarity (meaning)
    │                  │     2. Keyword matching (exact words)
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  GPT-4o Reasoning│──► "85% confidence: Both are gold Rolex
    │  (Claims Adjuster│     watches with surface damage.
    │   with 20 years  │     Location matches (Security).
    │   experience)    │     Recommend: CONFIRM"
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  Staff Dashboard │──► Staff sees side-by-side comparison
    │  Confirm/Reject  │    with AI reasoning
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  Notification    │──► Passenger gets: "We found your item!
    │  (Email/SMS)     │    Confidence: 85%. Visit Lost & Found."
    └──────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     STAFF SIDE                              │
│                                                             │
│   Staff finds an item → takes photo → uploads              │
│          │                                                  │
│          ▼                                                  │
│   ┌─────────────────┐                                       │
│   │  Azure AI Vision│──► tags: ["watch", "gold", "luxury"]  │
│   │  Image Analysis │    objects: ["wristwatch"]             │
│   │                 │    OCR text: "ROLEX"                   │
│   │                 │    caption: "gold watch with scratches"│
│   └────────┬────────┘                                       │
│            │                                                │
│            ▼                                                │
│   ┌─────────────────┐                                       │
│   │  GPT-4o Extract │──► Structured attributes              │
│   │  + Embedding    │──► 1536-dim vector                    │
│   └────────┬────────┘                                       │
│            │                                                │
│            ▼                                                │
│   ┌─────────────────┐                                       │
│   │  Azure AI Search│──► Indexed & searchable instantly      │
│   │  + SQLite DB    │                                       │
│   └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

### The RAG-Inspired Pattern

This system follows a **Retrieval-Augmented Generation (RAG)** pattern:

1. **Retrieval**: When a passenger reports a lost item, the system searches the "found items" database using vector similarity (like how Google finds related pages, but for items)
2. **Augmentation**: The search results (candidate matches) are fed to GPT-4o along with both descriptions
3. **Generation**: GPT-4o reasons about whether they're the same item, outputs a confidence score with detailed justification

---

## 4. Azure Services Used (الخدمات السحابية)

| Service | Package | What It Does | Status |
|---------|---------|-------------|--------|
| **Azure OpenAI (GPT-4o)** | `openai` | Understands descriptions, extracts attributes, reasons about matches | ✅ Live |
| **Azure OpenAI (text-embedding-3-small)** | `openai` | Converts text to 1536-dim vectors that capture meaning | ✅ Live |
| **Azure AI Vision** | `azure-ai-vision-imageanalysis` | Analyzes photos of found items (tags, objects, OCR, colors) | ⚠️ Demo mode (no resource) |
| **Azure AI Search** | `azure-search-documents` | Stores vectors + enables hybrid search (vector + keyword) | ✅ Live |
| **Azure Blob Storage** | `azure-storage-blob` | Stores uploaded item photos | ✅ Available |
| **Azure Document Intelligence** | `azure-ai-documentintelligence` | Could parse passenger paper forms / PDFs | ✅ Available |

### Azure Resources in our Resource Group (`GBGAcademy-AI-GP2`):

| Resource | Type | Location |
|----------|------|----------|
| `GBGAcademy-GenAI-2` | Azure OpenAI | West Europe |
| `gbgacademy1` | Azure AI Search | West Europe |
| `gbgacademy1` | Storage Account | West Europe |
| `gbg-gr2` | Document Intelligence (FormRecognizer) | West Europe |

### Model Deployments in Azure OpenAI:

| Deployment Name | Model | Version |
|----------------|-------|---------|
| `gpt-4o` | GPT-4o | 2024-11-20 |
| `text-embedding-3-small` | text-embedding-3-small | 1 |

---

## 5. Project Files Explained (شرح كل ملف)

```
TASK 4/
├── app.py                          ← Main Streamlit app (5 pages)
├── ai_pipeline.py                  ← All AI functions (the brain)
├── database.py                     ← SQLite database operations
├── models.py                       ← Pydantic data models
├── config.py                       ← Configuration & env vars
├── setup_azure_search.py           ← One-time index creation script
├── requirements.txt                ← Python dependencies
├── .env                            ← Azure credentials (SECRET - never commit!)
├── .env.example                    ← Template for credentials
├── README.md                       ← Quick-start documentation
├── PROJECT_PLAN.md                 ← THIS FILE - full project documentation
├── prompts/
│   ├── attribute_extraction.txt    ← GPT-4o prompt: "extract item attributes"
│   └── match_reasoning.txt         ← GPT-4o prompt: "score this match"
├── data/
│   └── lost_found.db               ← SQLite database (auto-created)
└── uploads/                        ← Item photos stored here
```

### 5.1 `models.py` — Data Models

Defines the shape of our data using Pydantic:

```
LostItemReport:
  - case_id (UUID)          ← Unique ID for tracking
  - passenger_name           ← Who lost it
  - contact_email/phone      ← How to reach them
  - item_description         ← Free text: "my blue bag..."
  - item_category            ← phone/laptop/wallet/watch/etc.
  - item_color, item_brand   ← Structured attributes
  - location_last_seen       ← Terminal 1, Gates B, Security...
  - time_last_seen           ← When
  - status                   ← active → matched → closed

FoundItemRecord:
  - found_id (UUID)          ← Unique ID
  - staff_id                 ← Who found it
  - item_description         ← Staff's description
  - photo_path               ← Photo of the item
  - location_found           ← Where in the airport
  - status                   ← unclaimed → matched → claimed

MatchResult:
  - match_id (UUID)
  - lost_case_id + found_item_id  ← Links lost ↔ found
  - confidence_score (0.0-1.0)    ← AI confidence
  - match_reasons (list)          ← Why AI thinks it's a match
  - status                        ← pending → confirmed/rejected
  - reviewed_by, reviewed_at      ← Staff audit trail

NotificationLog:
  - Who was notified, when, what confidence, what message
```

### 5.2 `config.py` — Configuration

- Reads ALL Azure credentials from `.env` file
- Key function: `is_demo_mode()` — returns True if Azure keys are missing
- The app checks this and falls back to mock AI responses when needed

### 5.3 `database.py` — SQLite Database

4 tables: `lost_reports`, `found_items`, `match_results`, `notifications_log`

Full CRUD for each:
- `insert_*()`, `get_all_*()`, `get_*()`, `update_*_status()`, `delete_*()`
- `seed_demo_data()` — creates 5 realistic lost reports + 5 found items on first run

Demo data includes:
- Lost: Montblanc wallet, MacBook Pro, gold Rolex, Samsonite suitcase, AirPods Pro
- Found: matching items with realistic staff descriptions

### 5.4 `ai_pipeline.py` — The AI Brain (6 Functions)

```
1. extract_item_attributes(description) → dict
   Input:  "I lost my scratched silver laptop near gate B12"
   Output: {category: "laptop", color: "silver", brand: "Apple",
            distinctive_features: ["scratched"], normalized_description: "..."}
   How:    Sends description to GPT-4o with attribute_extraction.txt prompt

2. analyze_item_image(image_path) → dict
   Input:  Path to a photo of a found item
   Output: {tags: [...], objects: [...], ocr_text: "ROLEX", caption: "...",
            dominant_colors: [...], brand_hints: [...]}
   How:    Azure AI Vision Image Analysis 4.0 API
   Note:   Currently returns mock data (no Vision resource available)

3. generate_embedding(text) → list[float]
   Input:  "silver laptop with scratched surface"
   Output: [0.002, -0.058, -0.001, ...] (1536 numbers)
   How:    Azure OpenAI text-embedding-3-small model
   Why:    These numbers capture the MEANING of text — similar items
           have similar vectors, even with different words

4. index_found_item(found_item, attributes, embedding) → bool
   What:   Uploads a found item + its vector to Azure AI Search
   Why:    Makes it instantly searchable via hybrid (vector + keyword) search

5. find_matches(lost_report, found_items, top_k=5) → list[dict]
   What:   The MAIN matching function
   How:    
     a. Generate embedding for lost item description
     b. Run hybrid search in Azure AI Search
     c. For each candidate, call reason_about_match()
     d. Return ranked list with confidence scores
   
6. reason_about_match(lost_desc, found_desc, lost_attrs, found_attrs) → dict
   What:   GPT-4o acts as a "senior airport claims adjuster"
   Input:  Both descriptions + both attribute sets
   Output: {
     confidence_score: 0.85,
     reasoning: "Both are gold Rolex watches with surface damage...",
     matching_factors: ["Category match", "Color match", "Brand match"],
     contradicting_factors: ["Loose clasp not mentioned in lost report"],
     recommendation: "CONFIRM"
   }
```

### 5.5 `app.py` — Streamlit Application (5 Pages)

**Page 1: 🧳 Report Lost Item (Passenger View)**
- Form with: name, email, phone, description, category, color, brand, location, date
- Optional photo upload
- On submit → GPT-4o extracts attributes → stored in SQLite
- Shows confirmation with case ID

**Page 2: 📦 Register Found Item (Staff View)**
- Form with: staff ID, photo (REQUIRED), location, date, notes
- On submit → AI Vision analyzes photo → GPT-4o extracts attributes
- Staff reviews/confirms auto-extracted data
- Item indexed in Azure AI Search for matching

**Page 3: 🔍 Check Matches (Staff Dashboard)**
- Lists all active lost reports
- "Run AI Match" button for each → triggers the full matching pipeline
- Results show:
  - Confidence score with color coding (🟢 ≥85%, 🟡 60-84%, 🔴 <60%)
  - Side-by-side: lost description vs. found item
  - AI reasoning text
  - ✅ Confirm / ❌ Reject buttons
- Confirming a match → updates both statuses + creates notification

**Page 4: 📊 Analytics Dashboard**
- KPI cards: Open cases, Unclaimed found, Confirmed today, Avg confidence
- Bar chart: Top 10 most lost item categories
- Bar chart: High-risk zones (where items are found most)
- Histogram: Match confidence distribution
- Line chart: Average resolution time trend (30 days)
- Summary statistics table

**Page 5: 🔔 Notifications (Simulation)**
- Log of all notifications sent to passengers
- Each shows: email, case ID, confidence, message, timestamp
- "Simulate Send" button for testing

### 5.6 `prompts/` — System Prompts

**attribute_extraction.txt:**
Instructs GPT-4o to be an "airport lost-and-found specialist" and extract:
category, color, brand, distinctive_features, normalized_description

**match_reasoning.txt:**
Instructs GPT-4o to be a "senior airport claims adjuster with 20 years experience"
and analyze: semantic similarity, physical attributes, location/time proximity

### 5.7 `setup_azure_search.py` — Index Setup

Creates the Azure AI Search index with:
- 10 fields (id, item_type, category, color, brand, location, description, features, timestamp, embedding)
- HNSW vector search algorithm (fast approximate nearest neighbor search)
- 1536-dimension vector field for embeddings
- Run once: `python setup_azure_search.py`

---

## 6. Confidence Scoring System

| Score | Color | Action | Example |
|-------|-------|--------|---------|
| ≥ 85% | 🟢 Green | Auto-flag for notification, recommend CONFIRM | "gold Rolex with scratches" ↔ "Rolex Submariner with surface wear" |
| 60-84% | 🟡 Yellow | Needs human review | "blue bag" ↔ "navy backpack" (similar but uncertain) |
| < 60% | 🔴 Red | Low probability, keep searching | "silver laptop" ↔ "black wallet" (clearly different) |

---

## 7. How to Run (تشغيل المشروع)

### Prerequisites
- Python 3.10+
- Azure credentials in `.env` (or runs in demo mode without them)

### Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (First time only) Create the Azure AI Search index
python setup_azure_search.py

# 3. Run the app
streamlit run app.py

# 4. Open in browser
# → http://localhost:8501
```

### Demo Mode
If `.env` has no Azure keys, the app runs in **full demo mode**:
- GPT-4o → mock attribute extraction (keyword-based)
- Embeddings → deterministic mock vectors
- AI Vision → mock image analysis results
- Matching → attribute comparison (category + color + brand + location)
- All UI features work, just with simulated AI

---

## 8. Real Test Results (نتائج حقيقية)

### Test: "Expensive gold watch with scratches" vs. "Rolex Submariner with surface wear"

**GPT-4o Attribute Extraction (Lost Item):**
```json
{
  "category": "watch",
  "color": "gold",
  "brand": "Rolex",          ← Inferred from "expensive gold watch"!
  "distinctive_features": ["scratches on the face", "luxury brand"],
  "normalized_description": "A gold luxury watch, possibly a Rolex, with scratches on the face."
}
```

**GPT-4o Match Reasoning:**
```json
{
  "confidence_score": 0.85,
  "reasoning": "Both items are gold luxury watches, specifically Rolex, 
   and both mention wear on the face/crystal. The distinctive features 
   align closely, with 'scratches on the face' corresponding to 
   'minor surface wear on crystal'. Location matches (Security).",
  "matching_factors": [
    "Category match: Both are watches",
    "Color match: Both are gold",
    "Brand match: Both are Rolex",
    "Distinctive feature match: Scratches/wear on face/crystal",
    "Location proximity: Found at Security"
  ],
  "contradicting_factors": [
    "Found item has slightly loose clasp — not mentioned in lost report"
  ],
  "recommendation": "CONFIRM"
}
```

**This is the Semantic Bridge in action:**
- Passenger said "scratches" → Staff said "surface wear" → AI understood: SAME THING
- Passenger said "expensive gold" → AI inferred: "probably Rolex" → Staff confirmed: "Rolex Submariner"

---

## 9. Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Streamlit | Web UI with 5 pages |
| AI - LLM | Azure OpenAI GPT-4o | Text understanding, reasoning, scoring |
| AI - Embeddings | text-embedding-3-small | Convert text to meaning vectors (1536-dim) |
| AI - Vision | Azure AI Vision | Analyze item photos (tags, OCR, colors) |
| Search | Azure AI Search (HNSW) | Vector + keyword hybrid search |
| Storage | Azure Blob Storage | Item photos |
| Database | SQLite | Local structured data (reports, matches, notifications) |
| Data Models | Pydantic | Type-safe data validation |
| Charts | Plotly | Interactive analytics visualizations |
| Config | python-dotenv | Secure credential management |

---

## 10. Security Considerations

1. **No hardcoded secrets** — all API keys via `.env` (never committed to git)
2. **PII protection** — passenger data stays in local SQLite, not sent to search index
3. **Human-in-the-loop** — AI suggests matches, but staff must confirm before notification
4. **Graceful fallback** — demo mode runs when credentials are missing (no crashes)

---

## 11. Team

**GBG Group B — NTI Academy**
- Abdallah Hosni
- Mohamed Magdy
- Sara Hassan
- Esraa Adel
- Farah

---

## 12. What We Learned from Previous Tasks

| Previous Task | Skill Learned | Used in Task 4 |
|--------------|---------------|-----------------|
| Task 1 (Chinook Chatbot) | Azure OpenAI + prompt engineering | GPT-4o for attribute extraction and reasoning |
| Task 2 (Resume Search) | Embeddings + Azure AI Search + vector indexing | Vector-based matching pipeline |
| Task 3 (Document Intelligence) | Azure AI Vision + Document Intelligence | Image analysis for found items |
| Chat with Database | RAG pipeline + modular architecture | RAG-inspired matching architecture |

**Task 4 combines ALL skills from the previous tasks into one integrated system.**
