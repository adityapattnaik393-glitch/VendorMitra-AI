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
- 🤖 **IBM Granite** — configurable chat model via watsonx.ai
- 🌐 **Multilingual** — supports Hindi and English queries
- ⚡ **FastAPI** backend with a customer chat page at `/` and API routes for `/health`, `/granite/test`, `/chat`, and `/ingest`
- 🗄️ **ChromaDB** vector store with multilingual sentence embeddings

---

## Project Structure

```
street-vendor-agent/
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI app & routes
│   │   ├── chat.html       # Customer chat page served at /
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

- Python 3.12 (recommended for the pinned model/runtime wheels)
- IBM Cloud account (Lite tier is sufficient)
- watsonx.ai project with Granite model enabled

### 1. Clone & enter the backend

```bash
git clone <repo-url>
cd street-vendor-agent/backend
```

### 2. Set up the backend (Windows PowerShell)

```bash
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

The script recreates `backend/.venv`, installs CPU-only PyTorch first, then the
backend requirements. It creates `.env` only if one does not already exist.

### 3. Configure IBM credentials

Edit `backend/.env` and set `IBM_API_KEY`, `IBM_PROJECT_ID`, and `IBM_REGION`.
`IBM_MODEL_ID` defaults to `ibm/granite-4-h-small`; change it only if the
preflight reports that the model is unavailable for your region/project.

### 4. Check IBM access and start the backend

```bash
\.venv\Scripts\Activate.ps1
python -m app.check_granite
python -m app.ingest
uvicorn app.main:app --reload
```

PDF conversion uses `pypdf` by default. For improved table/layout extraction,
install the optional `pip install -r requirements-docling.txt` before ingestion.
With the server running, check `http://127.0.0.1:8000/health`, then
`http://127.0.0.1:8000/granite/test`, and call `POST /ingest` once to index the
processed documents.

Open `http://127.0.0.1:8000` in your browser to use the customer chat. Open
`http://127.0.0.1:8000/docs` to try the API directly.

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
| GET  | `/`        | Service message |
| GET  | `/health`  | IBM configuration and indexed chunk count |
| GET  | `/granite/test` | Test a real IBM Granite chat request |
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
| Language model | IBM Granite chat model (`IBM_MODEL_ID`, default `ibm/granite-4-h-small`) |
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
