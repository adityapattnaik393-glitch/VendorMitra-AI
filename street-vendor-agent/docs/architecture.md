# VendorMitra AI — Architecture

## Overview

VendorMitra is a single-pass retrieval-augmented generation (RAG) chat
application. The FastAPI backend serves the browser UI and API, retrieves
relevant text from a local ChromaDB collection, and asks IBM Granite on
watsonx.ai to compose a grounded response.

This is not a multi-step autonomous agent: it does not plan tasks, browse the
web, or invoke external business tools. The selected task only provides prompt
guidance.

## System diagram

```text
Browser
  ├─ Chat UI (English/Hindi selector, profile, saved-chat sidebar)
  ├─ Browser localStorage (chat history, profile, language preference)
  └─ POST /chat
       ├─ FastAPI validates question, task, profile, response language
       └─ app.agent
            ├─ app.rag: multilingual embedding → ChromaDB top-3 passages
            └─ app.granite: prompt + passages → IBM watsonx.ai chat endpoint
                  └─ answer + unique source filenames → Browser

Source PDFs → app.ingest → Markdown → POST /ingest
                                      └─ chunks + embeddings → ChromaDB
```

## Request flow

1. The browser sends the question, selected response language, task, and
   optional vendor details to `POST /chat`.
2. FastAPI validates the request. The assistant appends vendor context to the
   retrieval query when provided.
3. `app.rag.retrieve_context` embeds the query with
   `paraphrase-multilingual-MiniLM-L12-v2` and asks ChromaDB for up to three
   matching chunks.
4. `app.agent` builds the context and calls `app.granite.generate_answer`.
5. A question containing Devanagari characters selects Hindi output regardless
   of the UI selection. Otherwise, the chosen response language is passed into
   the system prompt. Hindi output is requested in Devanagari script.
6. The API returns the answer and de-duplicated source filenames.

The browser stores up to 40 recent conversations, the saved profile fields,
and the selected language in localStorage. Profile edits are not sent to the
assistant until the user selects **Save profile**; saved profile fields are
included in each `/chat` request and used as context for tailored responses.
The profile editor opens from the person icon at the bottom of the sidebar.
Chat history is specific to the browser profile and site origin; it is not
synchronized to the backend or other devices. A New chat action starts a blank
conversation, and selecting a previous chat restores its messages locally.

If the vector collection is empty, the assistant still answers but is told that
no verified source material is indexed. Its prompt directs it to avoid
unsupported government-policy claims and to recommend checking official
sources.

## Document ingestion and indexing

```text
backend/data/raw/*.pdf
        │
        ▼
app.ingest: Docling when installed, otherwise pypdf
        │
        ▼
backend/data/processed/*.md
        │
        ▼
POST /ingest → RecursiveCharacterTextSplitter
        │         chunk size 800, overlap 120
        ▼
SentenceTransformer embeddings → ChromaDB persistent collection
```

Text extraction and vector indexing are intentionally separate steps. Empty
PDF extraction is reported as skipped and causes the conversion command to
exit unsuccessfully; this helps identify scanned PDFs that need OCR. When a
same-basename `.ocr.pdf` sidecar exists, ingestion uses it instead of the
original and keeps the original Markdown filename. The optional Docling
dependency can improve layout extraction but does not guarantee OCR for every
scanned document.

ChromaDB uses a persistent directory at `backend/chroma_db/`. Re-running
`POST /ingest` upserts chunks with stable document-based IDs.

## Components

| Path | Responsibility |
|---|---|
| `backend/app/main.py` | FastAPI routes, request validation, CORS configuration, server entry point |
| `backend/app/chat.html` | Responsive bilingual chat UI |
| `backend/app/agent.py` | Retrieve-then-answer orchestration and Hindi-script detection |
| `backend/app/rag.py` | PDF Markdown chunking, embeddings, ChromaDB indexing and retrieval |
| `backend/app/ingest.py` | Convert source PDFs to Markdown and report extraction failures |
| `backend/app/granite.py` | IBM IAM token handling and watsonx.ai chat requests |
| `backend/app/check_granite.py` | Credential, model-availability, and live-call preflight |
| `backend/tests/` | Unit tests for response language and Granite requests |

## IBM integration

- watsonx.ai base URL: `https://{IBM_REGION}.ml.cloud.ibm.com`
- Chat endpoint: `/ml/v1/text/chat?version=2024-10-08`
- Default model: `ibm/granite-4-h-small`
- Authentication: IBM IAM API key exchanged for a cached bearer token; a `401`
  response triggers one token refresh and retry.
- `python -m app.check_granite` checks configuration, lists chat models in the
  configured region, and performs a real test request.

The endpoint, version, and default model above reflect the current backend
configuration. If the selected model is not enabled for the project or region,
set `IBM_MODEL_ID` to an available chat model.

## Routes and runtime

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/` | Return the chat page |
| `GET` | `/health` | Report IBM config and ChromaDB status; does not call IBM |
| `GET` | `/granite/test` | Test an IBM Granite request |
| `POST` | `/ingest` | Convert processed Markdown to ChromaDB chunks |
| `POST` | `/chat` | Retrieve context and generate an answer |

Run from `backend/` with `python -m app.main`. The server binds to `0.0.0.0`
and reads its port from `PORT` (default `8000`). The HTML UI is same-origin;
CORS is off by default. A separate frontend may set `CORS_ORIGINS` to a
comma-separated allowlist.

## Configuration

| Variable | Default | Use |
|---|---|---|
| `IBM_API_KEY` | unset | IBM IAM authentication |
| `IBM_PROJECT_ID` | unset | watsonx.ai project |
| `IBM_REGION` | `us-south` | watsonx.ai region |
| `IBM_MODEL_ID` | `ibm/granite-4-h-small` | Chat model |
| `PORT` | `8000` | HTTP listen port for the module entry point |
| `CORS_ORIGINS` | empty | Allowed origins for a separately hosted browser client |

## Limitations

- Answers depend on extracted and indexed source content; an answer does not
  guarantee that every source PDF was parsed successfully.
- Retrieval returns at most three chunks and does not browse live official
  websites.
- Hindi automatic language selection detects Devanagari text. Romanized Hindi
  follows the language selected in the UI.
- Scheme rules and other time-sensitive information should be confirmed with
  the responsible official source.
- The sidebar's schemes and tips actions submit focused questions to the same
  chat endpoint; they are not separate data-backed product modules.
