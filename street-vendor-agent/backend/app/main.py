from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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


class VendorProfile(BaseModel):
    business_name: str | None = None
    business_type: str | None = None
    products: list[str] = Field(default_factory=list, max_length=20)
    location: str | None = None
    preferred_language: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    task: Literal[
        "general",
        "business_profile",
        "upi_setup",
        "local_seo",
        "customer_engagement",
    ] = "general"
    vendor: VendorProfile | None = None


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
    vendor_profile = (
        request.vendor.model_dump(exclude_none=True, exclude_defaults=True)
        if request.vendor
        else None
    )
    return ask_vendor_mitra(
        request.question,
        task=request.task,
        vendor_profile=vendor_profile,
    )
