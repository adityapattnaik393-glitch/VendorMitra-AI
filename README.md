VendorMitra AI

A bilingual (English/Hindi) agentic AI assistant that helps Indian street vendors find government schemes, go digital, and grow their business.

Built with IBM Granite on watsonx.ai, a RAG pipeline (ChromaDB), and live verification against official government websites.
The problem

Millions of street vendors in India struggle to:

find and understand government schemes such as PM SVANidhi, MUDRA and Udyam
accept digital payments (UPI/QR) and build an online presence
get reliable guidance in their own language

VendorMitra answers these questions in simple English or Hindi, with sources the vendor can check.

✨ Features
Grounded answers (RAG): retrieves passages from government documents and vendor guides stored in ChromaDB.
Live verification: for scheme questions, Granite decides whether current information is needed, then searches only allowlisted official sites (myScheme, PM SVANidhi, Udyam, MUDRA, MoHUA) via Tavily.
Transparent sources: stored-document information is labeled separately from live website information, with clickable official links and retrieval dates.
Safe fallback: if live search fails, the assistant uses stored documents and says it could not verify online.
Bilingual: replies in Hindi automatically when the question uses Devanagari; English/Hindi selector in the UI.
Digital presence tools: generates business profiles, WhatsApp messages, signboard lines and QR-poster copy, plus UPI, local-listing and customer-engagement guidance.
Personalization: saved vendor profile (name, products, location) is used to tailor answers.
Private by design: chat history and profile stay in the browser (localStorage); location is never sent to a third-party service.
🏗️ How it works
POST /chat
scheme questions
Street Vendor
Chat UIEnglish / हिंदी
FastAPI backend
Agent orchestrator
RAG retrievalMiniLM embeddings →ChromaDB top-3
Live verificationTavily → official gov sites
IBM Granitewatsonx.ai
Source PDFs
Docling / pypdf →Markdown
LangChain splitter800 / 120
The browser sends the question, language and vendor profile to POST /chat.
The agent retrieves the top three matching passages from ChromaDB.
For scheme questions, Granite decides if live verification is needed; if so, Tavily searches the allowlisted official domains.
Granite writes a grounded answer from the labeled PDF and live context, in the right language.
The API returns the answer, source labels and official links.

More detail: street-vendor-agent/docs/architecture.md

🧰 Tech stack
Area	Technology
LLM	IBM Granite 4 H Small (ibm/granite-4-h-small) on IBM watsonx.ai
Auth	IBM Cloud IAM (cached bearer token, auto-refresh)
Retrieval	ChromaDB, paraphrase-multilingual-MiniLM-L12-v2, LangChain text splitters
Live search	Tavily Search API (official-domain allowlist)
Document ingestion	Docling (optional) / pypdf, OCR support via .ocr.pdf
Backend	Python 3.12, FastAPI, Uvicorn
Frontend	HTML/JavaScript chat UI, browser localStorage
Dev tools	IBM Bob, GitHub
🚀 Quick start
bash
git clone https://github.com/adityapattnaik393-glitch/VendorMitra-AI.git
cd VendorMitra-AI/street-vendor-agent/backend

python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env                 # Windows: Copy-Item .env.example .env

Edit .env and set:

env
IBM_API_KEY=your_ibm_api_key
IBM_PROJECT_ID=your_watsonx_project_id
IBM_REGION=us-south
TAVILY_API_KEY=your_tavily_key      # enables live official-site search

Check your Granite setup, convert the documents, and start the app:

bash
python -m app.check_granite          # verifies credentials and model access
python -m app.ingest                 # PDFs → Markdown
python -m app.main                   # starts the server on http://127.0.0.1:8000

In another terminal, index the documents (needed once on a fresh clone):

bash
curl -X POST http://127.0.0.1:8000/ingest

Then open http://127.0.0.1:8000 and start chatting.

💬 Try these
"Am I eligible for PM SVANidhi?"
"क्या मैं पीएम स्वनिधि योजना के लिए पात्र हूँ?"
"How can I accept UPI payments at my stall?"
"I sell fruit in Pune Camp. Write a business profile for my stall."
Use Create promotional materials for a WhatsApp message, signboard line and QR-poster copy.
🔌 API
Method	Path	Purpose
GET	/	Chat interface
GET	/health	IBM configuration and vector-store status
GET	/granite/test	Real Granite test request
POST	/ingest	Index Markdown documents in ChromaDB
POST	/chat	Retrieve context and generate an answer
bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"How can I accept UPI payments?","response_language":"Hindi","task":"upi_setup"}'

Interactive API docs are available at /docs.

🗂️ Project structure
text
street-vendor-agent/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI routes
│   │   ├── agent.py           # intent, profile extraction, retrieval orchestration
│   │   ├── rag.py             # chunking, embeddings, ChromaDB
│   │   ├── web_search.py      # Tavily + official-domain filtering
│   │   ├── granite.py         # IBM IAM + watsonx.ai requests
│   │   ├── ingest.py          # PDF → Markdown
│   │   ├── check_granite.py   # credential / model preflight
│   │   └── chat.html          # bilingual chat UI
│   ├── data/raw/              # source PDFs and datasets
│   ├── data/processed/        # Markdown for indexing
│   └── tests/                 # unit tests
└── docs/architecture.md
⚠️ Limitations
Answers depend on the indexed documents and retrieve at most three passages.
Live search needs a Tavily API key and network access; otherwise the app falls back to stored PDFs.
The PM SVANidhi dataset is historical (as of 2024-01-30), not live data.
Romanized Hindi (Hinglish) follows the language chosen in the UI; automatic detection covers Devanagari only.
Scheme rules change. Always confirm eligibility, fees and deadlines on the official website.
🧪 Tests
bash
cd street-vendor-agent/backend
python -m unittest discover -s tests
🔒 Security note

Never commit .env or your IBM/Tavily keys. The app treats retrieved text as data (not instructions) and never invents URLs or scheme rules.

📄 License

Released under the MIT License.

👤 Author

Aditya Pattnaik
