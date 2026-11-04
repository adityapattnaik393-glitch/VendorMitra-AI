import os
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import granite
from app.agent import ask_vendor_mitra
from app.rag import indexed_chunks, ingest_documents

app = FastAPI(title="VendorMitra AI")
CHAT_PAGE = Path(__file__).with_name("chat.html")
ResponseLanguage = Literal["English", "Hindi"]

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class VendorProfile(BaseModel):
    business_name: str | None = None
    business_type: str | None = None
    products: list[str] = Field(default_factory=list, max_length=20)
    location: str | None = None
    preferred_language: ResponseLanguage | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    response_language: ResponseLanguage | None = None
    task: Literal[
        "general",
        "business_profile",
        "promotional_materials",
        "upi_setup",
        "local_seo",
        "customer_engagement",
    ] = "general"
    vendor: VendorProfile | None = None


@app.get("/")
def home():
    return FileResponse(CHAT_PAGE, media_type="text/html")


@app.get("/health")
def health():
    """Quick status without calling IBM: config and indexed chunk count."""
    problems = granite.config_problems()
    vector_store_error = None
    try:
        chunks = indexed_chunks()
    except Exception as error:
        chunks = None
        vector_store_error = str(error)
    return {
        "status": "degraded" if problems or vector_store_error else "ok",
        "granite_configured": not problems,
        "problems": problems,
        "model": granite.IBM_MODEL_ID,
        "region": granite.IBM_REGION,
        "indexed_chunks": chunks,
        "vector_store_error": vector_store_error,
    }


@app.get("/granite/test")
def granite_test():
    try:
        answer = granite.test_granite()
    except granite.GraniteError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"ok": True, "model": granite.IBM_MODEL_ID, "answer": answer}


@app.post("/ingest")
def ingest():
    try:
        chunks = ingest_documents()
    except FileNotFoundError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"message": "Documents indexed successfully", "chunks": chunks}


@app.post("/chat")
def chat(request: ChatRequest):
    vendor_profile = (
        request.vendor.model_dump(exclude_none=True, exclude_defaults=True)
        if request.vendor
        else None
    )
    try:
        return ask_vendor_mitra(
            request.question,
            task=request.task,
            vendor_profile=vendor_profile,
            preferred_language=(
                request.response_language
                or (
                    request.vendor.preferred_language
                    if request.vendor and request.vendor.preferred_language
                    else "English"
                )
            ),
        )
    except granite.GraniteError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
