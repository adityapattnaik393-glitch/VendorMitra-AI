from pathlib import Path

# Resolve paths relative to this file so they work regardless of
# the working directory uvicorn is launched from.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(_BACKEND_DIR / "chroma_db")
PROCESSED_DIR = _BACKEND_DIR / "data" / "processed"

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_state: dict = {}


def _collection():
    if "collection" not in _state:
        import chromadb

        client = chromadb.PersistentClient(path=DB_PATH)
        _state["collection"] = client.get_or_create_collection(name="vendor_knowledge")
    return _state["collection"]


def _model():
    if "model" not in _state:
        from sentence_transformers import SentenceTransformer

        _state["model"] = SentenceTransformer(EMBED_MODEL)
    return _state["model"]


def _splitter():
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)


def ingest_documents() -> int:
    files = sorted(PROCESSED_DIR.glob("*.md"))
    if not files:
        raise FileNotFoundError(
            f"No .md files in {PROCESSED_DIR}. Run `python -m app.ingest` first."
        )

    collection, model, splitter = _collection(), _model(), _splitter()
    total = 0
    for file in files:
        chunks = [
            chunk
            for chunk in splitter.split_text(file.read_text(encoding="utf-8"))
            if chunk.strip()
        ]
        if not chunks:
            print(f"Skipped {file.name}: no text extracted")
            continue

        vectors = model.encode(chunks, normalize_embeddings=True).tolist()
        collection.upsert(
            ids=[f"{file.stem}_{index}" for index in range(len(chunks))],
            documents=chunks,
            embeddings=vectors,
            metadatas=[{"source": file.name} for _ in chunks],
        )
        total += len(chunks)
        print(f"Indexed {file.name}: {len(chunks)} chunks")
    return total


def indexed_chunks() -> int:
    return _collection().count()


def retrieve_context(question, top_k=3):
    collection = _collection()
    count = collection.count()
    if count == 0:
        return []

    query_vector = _model().encode([question], normalize_embeddings=True).tolist()
    results = collection.query(
        query_embeddings=query_vector,
        n_results=min(top_k, count),
    )

    documents = results.get("documents", [[]])[0]
    metadata = results.get("metadatas", [[]])[0]

    return [
        {
            "content": document,
            "source": meta["source"],
        }
        for document, meta in zip(documents, metadata)
    ]
