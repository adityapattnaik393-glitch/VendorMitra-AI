from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import ask_vendor_mitra
from app.rag import ingest_documents

app = FastAPI(title="VendorMitra AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {
        "message": "VendorMitra AI is running"
    }


@app.post("/ingest")
def ingest():
    ingest_documents()
    return {"message": "Documents indexed successfully"}


@app.post("/chat")
def chat(request: ChatRequest):
    return ask_vendor_mitra(request.question)
