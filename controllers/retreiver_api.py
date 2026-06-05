import os
import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.retreival import HybridRetriever


# ==========================================
# REQUEST MODEL
# ==========================================
class RetrievalRequest(BaseModel):
    query: str
    index_directory: Optional[str] = "data/faiss_index"
    top_n: Optional[int] = 3


# ==========================================
# ROUTER
# ==========================================
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.post("/api/retrieve")
async def retrieve_chunks(payload: RetrievalRequest):
    """
    Takes a question string, runs hybrid retrieval (10 dense + 10 sparse BM25),
    fuses with Reciprocal Rank Fusion (RRF), and returns top N chunks.
    """
    if not os.path.exists(payload.index_directory):
        raise HTTPException(
            status_code=404,
            detail=f"FAISS index directory not found: {payload.index_directory}. Run /api/ingest first."
        )

    try:
        retriever = HybridRetriever(index_directory=payload.index_directory)
        result = retriever.retrieve(
            query=payload.query,
            dense_k=10,
            sparse_k=10,
            top_n=payload.top_n
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# EXAMPLE USAGE
# ==========================================
#
# Run:
#   uvicorn controllers.retreiver_api:app --host 0.0.0.0 --port 8002 --reload
#
# Retrieve top 3 chunks for a question:
#   curl -X POST http://localhost:8002/api/retrieve \
#     -H "Content-Type: application/json" \
#     -d '{"query": "What are the constraints on Windows updates?"}'
#
# With custom index directory and top_n:
#   curl -X POST http://localhost:8002/api/retrieve \
#     -H "Content-Type: application/json" \
#     -d '{"query": "What audit logs do I need for BYOD?", "index_directory": "data/faiss_index", "top_n": 5}'
