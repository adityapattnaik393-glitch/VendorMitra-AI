# VendorMitra AI 🛒

> **Street Vendor Digitalization Agent** — powered by RAG + IBM Granite

VendorMitra AI helps Indian street vendors and micro-entrepreneurs become
digitally visible by generating business profiles, UPI setup guides, local SEO
strategies, and customer engagement tips — all grounded in real government
documents and policies.

---

## Features

- 🏛️ **RAG pipeline** — answers retrieved from official government PDFs
  (PM SVANidhi, Street Vendors Act, BHIM UPI, MSME schemes)
- 🤖 **IBM Granite** — `ibm/granite-3-8b-instruct` via watsonx.ai
- 🌐 **Multilingual** — supports Hindi and English queries
- ⚡ **FastAPI** backend with `/chat` and `/ingest` endpoints
- 🗄️ **ChromaDB** vector store with multilingual sentence embeddings

---

## Project Structure

```
street-vendor-agent/
├── frontend/               # React / HTML chat UI (coming soon)
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI app & routes
│   │   ├── agent.py        # RAG → Granite orchestration
│   │   ├── granite.py      # IBM watsonx.ai Granite client
│   │   ├── rag.py          # ChromaDB ingest & retrieval
│   │   └── ingest.py       # PDF → Markdown (Docling)
│   ├── data/
│   │   ├── raw/            # Source government PDFs
│   │   └── processed/      # Extracted Markdown files
│   ├── chroma_db/          # Persistent vector store
│   ├── requirements.txt
│   └── .env.example
└── docs/
    └── architecture.md
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- IBM Cloud account (Lite tier is sufficient)
- watsonx.ai project with Granite model enabled

### 1. Clone & enter the backend

```bash
git clone <repo-url>
cd street-vendor-agent/backend
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn requests python-dotenv
pip install chromadb sentence-transformers
pip install langchain-text-splitters docling
```

Or all at once:

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and fill in:

```env
IBM_API_KEY=your_ibm_api_key_here
IBM_PROJECT_ID=your_watsonx_project_id_here
IBM_REGION=us-south
```

Get your API key at https://cloud.ibm.com/iam/apikeys  
Get your project ID from the watsonx.ai project settings page.

### 5. Ingest government documents

```bash
# Step 1 — Convert PDFs to Markdown
python -m app.ingest

# Step 2 — Start the server
uvicorn app.main:app --reload

# Step 3 — Index chunks into ChromaDB (one-time)
curl -X POST http://localhost:8000/ingest
```

### 6. Ask a question

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "I sell fruit in Pune Camp area, how do I set up UPI?"}'
```

Response:
```json
{
  "answer": "To set up UPI as a street vendor, you need to ...",
  "sources": ["BHIM_UPI_Guidelines_2026.md", "FAQEng.md"]
}
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/`        | Health check |
| POST | `/ingest`  | Index all processed documents into ChromaDB |
| POST | `/chat`    | Ask a vendor question; returns answer + sources |

### POST `/chat` — Request body

```json
{ "question": "string" }
```

### POST `/chat` — Response

```json
{
  "answer": "string",
  "sources": ["filename1.md", "filename2.md"]
}
```

---

## IBM Technology Stack

| Component | IBM Service |
|-----------|-------------|
| Language model | IBM Granite 3 8B Instruct (`ibm/granite-3-8b-instruct`) |
| Platform | IBM watsonx.ai (IBM Cloud Lite) |
| Auth | IBM IAM API Key |

---

## Government Documents (RAG Knowledge Base)

| Document | Coverage |
|----------|----------|
| BHIM UPI Guidelines 2026 | UPI merchant setup, QR codes |
| FAQ English / Hindi | Digital payment common questions |
| Onboarding API Guidelines | Digital service onboarding steps |
| Portal User Manual | Government portal usage |
| Scheme Guidelines | PM SVANidhi micro-credit scheme |
| Street Vendors Policy | Protection of Livelihood & Regulation Act |

---

## License

MIT
