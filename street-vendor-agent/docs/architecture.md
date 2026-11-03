# VendorMitra AI — Architecture

## Overview

VendorMitra AI is a RAG-powered (Retrieval-Augmented Generation) agentic assistant
that helps Indian street vendors and micro-entrepreneurs become digitally visible.
It combines government document knowledge with IBM Granite's language understanding
to give grounded, actionable answers to vendor queries.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                        Frontend                          │
│              (React / plain HTML chat UI)                │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTP (REST)
                        ▼
┌──────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                          │
│  POST /chat  ──►  agent.py                               │
│                      │                                   │
│             ┌────────┴────────┐                          │
│             ▼                 ▼                          │
│          rag.py           granite.py                     │
│   (retrieve context)   (generate answer)                 │
│             │                 ▲                          │
│             ▼                 │                          │
│         ChromaDB          IBM watsonx.ai                 │
│   (vector similarity    (Granite-3-8B-Instruct)          │
│        search)                                           │
└──────────────────────────────────────────────────────────┘
```

---

## RAG Pipeline

### Ingestion (one-time / on-demand)

```
Government PDFs  →  Docling (PDF→Markdown)  →  RecursiveCharacterTextSplitter
  →  SentenceTransformer embeddings  →  ChromaDB (persistent vector store)
```

**Documents indexed:**
| File | Content |
|------|---------|
| `BHIM_UPI_Guidelines_2026_*.pdf` | BHIM UPI setup & merchant guidelines |
| `FAQEng.pdf` | Digital payment FAQs (English) |
| `FAQHindi.pdf` | Digital payment FAQs (Hindi) |
| `Guidelines-for-Onboarding-*.pdf` | API-as-a-service onboarding guide |
| `Portal User Manual.pdf` | Government portal usage manual |
| `Scheme Guidelines.pdf` | MSME / PM SVANidhi scheme details |
| `Street Vendors policy.pdf` | Street Vendors (Protection) Act policy |

### Query Flow

```
Vendor question
      │
      ▼
SentenceTransformer encode(question)
      │
      ▼
ChromaDB.query(top_k=3)  →  relevant chunks + source filenames
      │
      ▼
Prompt construction (question + context)
      │
      ▼
IBM Granite (watsonx.ai /ml/v1/text/generation)
      │
      ▼
Grounded answer + source list  →  vendor
```

---

## Component Map

| File | Responsibility |
|------|---------------|
| `app/ingest.py` | Convert raw PDFs → Markdown with Docling |
| `app/rag.py` | Chunk, embed, store (ChromaDB) & retrieve |
| `app/granite.py` | IBM IAM auth + watsonx.ai Granite inference |
| `app/agent.py` | Orchestrate RAG → Granite pipeline |
| `app/main.py` | FastAPI routes: `/`, `/ingest`, `/chat` |

---

## IBM Cloud Services Used

- **IBM watsonx.ai** (IBM Cloud Lite) — hosts IBM Granite-3-8B-Instruct
- **Model**: `ibm/granite-3-8b-instruct`
- **Auth**: IBM IAM API Key → short-lived bearer token

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `IBM_API_KEY` | IBM Cloud IAM API key |
| `IBM_PROJECT_ID` | watsonx.ai project identifier |
| `IBM_REGION` | IBM Cloud region (default: `us-south`) |

---

## Running Locally

```bash
cd street-vendor-agent/backend

# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set credentials
copy .env.example .env         # then fill in your IBM keys

# 4. Ingest government documents (one-time)
python -m app.ingest

# 5. Index chunks into ChromaDB
curl -X POST http://localhost:8000/ingest

# 6. Start the API server
uvicorn app.main:app --reload
```

Then POST to `http://localhost:8000/chat`:
```json
{ "question": "I sell fruit in Pune's Camp area. How do I set up UPI?" }
```
