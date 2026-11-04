# VendorMitra AI

VendorMitra is a bilingual assistant for Indian street vendors and
micro-entrepreneurs. It retrieves passages from indexed government documents and
uses IBM Granite on watsonx.ai to answer practical business questions.

## What it does

- Answers questions using a ChromaDB knowledge base built from local PDFs.
- Provides a responsive chat interface with English/Hindi response selection.
- Automatically replies in Hindi when a question contains Devanagari text,
  even if English is selected. For Romanized Hindi/Hinglish, select Hindi.
- Offers focused prompts for UPI setup, business profiles, local visibility,
  customer engagement, and government schemes.
- Returns the filenames of retrieved source documents with each answer.

The assistant uses one retrieve-then-answer pass. It does not browse the web,
call external business tools, or verify changing scheme details in real time.
Confirm current eligibility, fees, dates, and application steps with official
sources.

## Requirements

- Python 3.12
- An IBM Cloud API key and a watsonx.ai project with a chat model available
- Network access to IBM IAM and watsonx.ai for chat responses

## Set up

From the repository root:

```bash
cd street-vendor-agent/backend
python3.12 -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Install dependencies and create the local environment file:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env                 # macOS/Linux
# Copy-Item .env.example .env        # Windows PowerShell
```

The Windows-only `setup.ps1` script creates the Python 3.12 environment and
installs CPU-only PyTorch before the backend requirements. It also creates
`.env` if it is not already present.

Edit `.env` and set `IBM_API_KEY` and `IBM_PROJECT_ID`. `IBM_REGION`
defaults to `us-south`; `IBM_MODEL_ID` defaults to
`ibm/granite-4-h-small`. If the model is unavailable for your project or region,
use `python -m app.check_granite` to see the available chat models.

## Extract and index documents

The repository's source PDFs are in `backend/data/raw/`. Convert them to
Markdown:

```bash
python -m app.ingest
```

By default, conversion uses `pypdf`. For improved layout and table extraction,
install the optional Docling dependency before conversion:

```bash
python -m pip install -r requirements-docling.txt
python -m app.ingest
```

Conversion and vector indexing are separate operations. After conversion,
start the server and call `POST /ingest` to index the converted Markdown files.

The ingest command reports documents that fail or produce no text and exits
unsuccessfully if any need attention. For scanned PDFs, create a searchable
OCR copy next to the original with the `.ocr.pdf` suffix. For example, with
OCRmyPDF, Tesseract, and Hindi language data installed:

```bash
ocrmypdf --skip-text -l hin+eng \
  data/raw/FAQHindi.pdf data/raw/FAQHindi.ocr.pdf
python -m app.ingest
```

Ingestion prefers the `.ocr.pdf` copy and writes to the original document's
Markdown filename. Installing Docling alone does not guarantee that scanned
pages will be recognized. Check the command output before relying on answers
from a document.

## Run and use

Run the app from `backend/`:

```bash
python -m app.main
```

The server binds to `0.0.0.0` and uses `PORT` (default `8000`), which supports
forwarded and hosted ports. Open `http://127.0.0.1:8000/` locally. The UI offers
English and Hindi response choices; Hindi written in Devanagari takes priority
over the selected choice.

After extraction, index or refresh the knowledge base from another terminal:

```bash
curl -X POST http://127.0.0.1:8000/ingest
```

Check service status at `GET /health`, IBM connectivity at `GET /granite/test`,
and the interactive API at `/docs`.

Example Hindi request:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"मैं UPI से भुगतान कैसे स्वीकार करूं?","response_language":"English"}'
```

The response is in Hindi because the question uses Devanagari. To select Hindi
for an English or Romanized Hinglish query, set `"response_language":"Hindi"`.

Example response:

```json
{
  "answer": "…",
  "sources": ["BHIM_UPI_Guidelines_2026_012a0b1bce.md"]
}
```

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Serve the chat interface |
| `GET` | `/health` | Report IBM configuration and vector-store status |
| `GET` | `/granite/test` | Make a real IBM Granite test request |
| `POST` | `/ingest` | Index Markdown documents in ChromaDB |
| `POST` | `/chat` | Retrieve context and generate a response |

`POST /chat` accepts a question, optional task, optional vendor profile, and
optional response language:

```json
{
  "question": "How can I accept UPI payments?",
  "response_language": "Hindi",
  "task": "upi_setup"
}
```

Supported `response_language` values are `English` and `Hindi`; when omitted,
the request uses the vendor profile language or defaults to `English`.
Questions written in Devanagari are answered in Hindi regardless of this
setting.

## Configuration and deployment

| Variable | Default | Description |
|---|---|---|
| `IBM_API_KEY` | — | IBM Cloud IAM API key |
| `IBM_PROJECT_ID` | — | watsonx.ai project ID |
| `IBM_REGION` | `us-south` | watsonx.ai deployment region |
| `IBM_MODEL_ID` | `ibm/granite-4-h-small` | Chat model ID |
| `PORT` | `8000` | HTTP port when started with `python -m app.main` |
| `CORS_ORIGINS` | empty | Comma-separated allowed origins for a separate frontend |

The chat page is served by this backend, so CORS is disabled by default.
Configure `CORS_ORIGINS` only when a frontend is hosted on another origin. Keep
`.env` private and never commit IBM credentials.

## Troubleshooting

- **Chat reports an IBM error:** check `/health`, then run
  `python -m app.check_granite`. Confirm the API key, project ID, region, model
  availability, and account limits.
- **A PDF is skipped for having no text:** create a searchable `.ocr.pdf` copy
  with OCRmyPDF and the right language data, rerun `python -m app.ingest`, then
  call `POST /ingest` to update ChromaDB.
- **No documents are indexed:** make sure extraction produced non-empty `.md`
  files under `backend/data/processed/`, then call `POST /ingest`.
- **Port is already in use:** start with another `PORT`, for example
  `PORT=8080 python -m app.main` on macOS/Linux.
- **Hindi query is Romanized:** choose Hindi from the response-language menu;
  automatic detection is based on Devanagari characters.

## Tests

From `street-vendor-agent/backend/`:

```bash
python -m unittest discover -s tests
```

## License

MIT
