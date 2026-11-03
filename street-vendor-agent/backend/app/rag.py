from pathlib import Path
import chromadb

from sentence_transformers import SentenceTransformer
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

# Resolve paths relative to this file so they work regardless of
# the working directory uvicorn is launched from.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(_BACKEND_DIR / "chroma_db")
PROCESSED_DIR = _BACKEND_DIR / "data" / "processed"

client = chromadb.PersistentClient(path=DB_PATH)

collection = client.get_or_create_collection(
    name="vendor_knowledge"
)

embedding_model = SentenceTransformer(
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=120
)


def ingest_documents():

    files = list(PROCESSED_DIR.glob("*.md"))

    for file in files:

        text = file.read_text(encoding="utf-8")

        chunks = splitter.split_text(text)

        vectors = embedding_model.encode(
            chunks,
            normalize_embeddings=True
        ).tolist()

        ids = [
            f"{file.stem}_{i}"
            for i in range(len(chunks))
        ]

        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=vectors,
            metadatas=[
                {
                    "source": file.name
                }
                for _ in chunks
            ]
        )

        print(f"Indexed {file.name}: {len(chunks)} chunks")


def retrieve_context(question, top_k=3):

    query_vector = embedding_model.encode(
        [question],
        normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=query_vector,
        n_results=top_k
    )

    documents = results.get("documents", [[]])[0]
    metadata = results.get("metadatas", [[]])[0]

    return [
        {
            "content": document,
            "source": meta["source"]
        }
        for document, meta in zip(documents, metadata)
    ]
