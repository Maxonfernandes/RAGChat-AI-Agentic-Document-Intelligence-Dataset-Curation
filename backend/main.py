import os
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Ensure backend and agentify paths are importable
current_dir = Path(__file__).resolve().parent
agentify_dir = current_dir / "agentify"
struct_dir = current_dir / "structurisation"
for d in [str(current_dir), str(agentify_dir), str(struct_dir)]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config import (
    HOST,
    PORT,
    INPUT_DIR,
    OUTPUT_DIR,
    get_effective_config
)
from master_agent import MasterAgent
from vector_db import VectorDB
from embedder import VectorEmbedder
from file_processor import FileProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ragchat.api")

app = FastAPI(
    title="RAGChat Agentic API",
    description="Multi-Agent Document QA & Structured Dataset Curation API",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
vector_db = VectorDB()
master_agent = MasterAgent(vector_db=vector_db)
embedder = VectorEmbedder(vector_db=vector_db)
processor = FileProcessor(input_dir=INPUT_DIR, output_dir=OUTPUT_DIR)


# Pydantic Schemas
class ChatRequest(BaseModel):
    query: Optional[str] = None
    prompt: Optional[str] = None
    file: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class UrlRequest(BaseModel):
    url: str
    config: Optional[Dict[str, Any]] = None


class ConfigUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    astra_api_token: Optional[str] = None
    astra_endpoint: Optional[str] = None
    astra_keyspace: Optional[str] = None
    collection_name: Optional[str] = None


@app.get("/")
def health_check():
    """Basic health check."""
    return {
        "status": "online",
        "service": "RAGChat Agentic AI API",
        "version": "1.0.0",
        "documents_loaded": len(vector_db.list_documents()),
        "total_chunks": vector_db.count()
    }


@app.get("/api/config")
def get_config_status(request: Request):
    """
    Returns current configuration status (masking sensitive tokens)
    so users and the UI can check API readiness.
    """
    headers = dict(request.headers)
    eff = get_effective_config(headers=headers)

    has_gemini = bool(eff.get("gemini_api_key"))
    has_astra = bool(eff.get("astra_api_token") and eff.get("astra_endpoint"))

    status = vector_db.status()

    return {
        "gemini_configured": has_gemini,
        "gemini_model": eff.get("gemini_model", "gemini-1.5-flash"),
        "astra_configured": has_astra,
        "astra_connected": status.get("astra_connected", False),
        "astra_status_message": status.get("message", ""),
        "collection_name": eff.get("collection_name", "pdf"),
        "documents": vector_db.list_documents(),
        "total_chunks": vector_db.count()
    }


@app.post("/api/config")
def update_config(payload: ConfigUpdateRequest):
    """Update runtime configuration settings."""
    cfg = payload.model_dump(exclude_unset=True)
    master_agent.update_config(cfg)
    return {
        "status": "updated",
        "config": {k: ("***" if "token" in k or "key" in k else v) for k, v in cfg.items()}
    }


@app.post("/api/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    """
    Chat endpoint for natural language queries and dynamic dataset curation.
    Accepts both 'query' and 'prompt' keys.
    Also handles legacy payload where frontend sends {"file": url}.
    """
    headers = dict(request.headers)
    effective_cfg = get_effective_config(headers=headers, body_config=body.config)

    # Legacy file URL ingestion via chat endpoint
    if body.file:
        chunks = embedder.embed_url(body.file)
        return {
            "agent": "ingestion",
            "message": f"Successfully ingested webpage URL ({chunks} chunks embedded into vector database).",
            "prompt": f"Ingested {body.file}",
            "dataset": [],
            "sources": [{"filename": body.file, "content": f"Ingested {chunks} chunks", "score": 1.0}],
            "steps": [{"agent": "IngestionAgent", "status": "completed", "description": f"Embedded {chunks} chunks"}]
        }

    # Extract user prompt
    prompt = body.query or body.prompt or ""
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="No query or prompt provided in request body.")

    # Run multi-agent pipeline
    result = master_agent.process_prompt(prompt, override_config=effective_cfg)

    # Ensure frontend compatibility with all legacy and modern keys
    return {
        "message": result.get("message", result.get("prompt", "")),
        "prompt": result.get("prompt", result.get("message", "")),
        "agent": result.get("agent", "conversation"),
        "dataset": result.get("dataset", []),
        "sources": result.get("sources", []),
        "steps": result.get("steps", []),
        "validation": result.get("validation", {"valid": True})
    }


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None
):
    """
    Upload a document (PDF, TXT, CSV, JSON, PNG, JPG) to process,
    chunk, and embed into the vector database.
    """
    headers = dict(request.headers) if request else {}
    effective_cfg = get_effective_config(headers=headers)

    input_path = Path(INPUT_DIR)
    input_path.mkdir(parents=True, exist_ok=True)
    saved_file = input_path / file.filename

    # Save uploaded file
    try:
        with open(saved_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
    finally:
        await file.close()

    # Embed file
    try:
        chunks_embedded = embedder.embed_file(str(saved_file))
        return {
            "status": "success",
            "filename": file.filename,
            "chunks_embedded": chunks_embedded,
            "total_documents": len(vector_db.list_documents()),
            "total_chunks": vector_db.count()
        }
    except Exception as e:
        logger.error(f"Failed to embed file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process and embed file: {str(e)}")


@app.post("/api/url")
async def ingest_url(body: UrlRequest, request: Request):
    """Ingest content from a public URL."""
    headers = dict(request.headers)
    effective_cfg = get_effective_config(headers=headers, body_config=body.config)

    if not body.url or not body.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="A valid HTTP or HTTPS URL is required.")

    try:
        chunks_embedded = embedder.embed_url(body.url)
        return {
            "status": "success",
            "url": body.url,
            "chunks_embedded": chunks_embedded,
            "total_documents": len(vector_db.list_documents()),
            "total_chunks": vector_db.count()
        }
    except Exception as e:
        logger.error(f"Failed to ingest URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest URL: {str(e)}")


@app.get("/api/documents")
def list_documents():
    """List all ingested documents and chunks."""
    return {
        "documents": vector_db.list_documents(),
        "total_chunks": vector_db.count()
    }


@app.delete("/api/documents")
def clear_documents():
    """Clear all documents from the vector store."""
    vector_db.clear()
    return {
        "status": "success",
        "message": "All documents cleared from vector store.",
        "total_chunks": 0
    }


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)