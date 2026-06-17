import os
import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add parent directory to python path to import tools package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.split_embed import IngestPipeline


# ==========================================
# REQUEST MODELS
# ==========================================
class IngestRequest(BaseModel):
    file_path: str
    index_directory: Optional[str] = os.getenv("FAISS_INDEX_DIR", "data/faiss_index")


# ==========================================
# ROUTER
# ==========================================
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.post("/api/ingest")
async def ingest_document(payload: IngestRequest):
    """
    Takes a file_path (PDF/PPTX), parses it, splits into parent/child chunks,
    embeds with BGE, and saves the FAISS index to disk for later retrieval.
    """
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {payload.file_path}")

    try:
        pipeline = IngestPipeline(index_directory=payload.index_directory)
        result = pipeline.ingest(payload.file_path)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# EXAMPLE USAGE
# ==========================================
#
# Run:
#   uvicorn controllers.split_embed_api:app --host 0.0.0.0 --port 8001 --reload
#
# Ingest a PPTX file (parse → split → embed → save to FAISS):
#   curl -X POST http://localhost:8001/api/ingest \
#     -H "Content-Type: application/json" \
#     -d '{"file_path": "/home/chaitanyadhir/rag/kreat_rag/data/Information Security Management System (ISMS) Policy Summaries_ (1).pptx"}'
#
# With custom index directory:
#   curl -X POST http://localhost:8001/api/ingest \
#     -H "Content-Type: application/json" \
#     -d '{"file_path": "data/policy.pdf", "index_directory": "data/my_custom_index"}'
