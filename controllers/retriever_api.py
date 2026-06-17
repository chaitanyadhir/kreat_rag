import os
import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.retrieval import HybridRetriever


# ==========================================
# REQUEST MODEL
# ==========================================
class RetrievalRequest(BaseModel):
    query: str
    index_directory: Optional[str] = os.getenv("FAISS_INDEX_DIR", "data/faiss_index")
    top_n: Optional[int] = 3


# ==========================================
# SINGLETON RETRIEVER (loaded once, reused across requests)
# ==========================================
# We store a module-level reference. main.py's lifespan hook initializes it
# once at startup so the BGE model weights are warm before first request.
_retriever: Optional[HybridRetriever] = None


def get_retriever(index_directory: str = None) -> HybridRetriever:
    """Returns the singleton retriever, creating it on first call."""
    global _retriever
    if index_directory is None:
        index_directory = os.getenv("FAISS_INDEX_DIR", "data/faiss_index")
    
    if _retriever is None:
        _retriever = HybridRetriever(index_directory=index_directory)
    return _retriever


def warmup_retriever(index_directory: str = None):
    """Called by main.py at startup to pre-load model weights."""
    global _retriever
    if index_directory is None:
        index_directory = os.getenv("FAISS_INDEX_DIR", "data/faiss_index")
    _retriever = HybridRetriever(index_directory=index_directory)


# ==========================================
# ROUTER
# ==========================================
router = APIRouter()


@router.post("/api/retrieve")
async def retrieve_chunks(payload: RetrievalRequest):
    """
    Takes a question string, runs hybrid retrieval (10 dense + 10 sparse BM25)
    in PARALLEL, fuses with Reciprocal Rank Fusion (RRF), and returns top N chunks.
    """
    if not os.path.exists(payload.index_directory):
        raise HTTPException(
            status_code=404,
            detail=f"FAISS index directory not found: {payload.index_directory}. Run /api/ingest first."
        )

    try:
        retriever = get_retriever(payload.index_directory)
        # retrieve() is now async — dense + sparse run in parallel
        result = await retriever.retrieve(
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
# Run via main.py:
#   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
#
# Retrieve top 3 chunks for a question:
#   curl -X POST http://localhost:8000/api/retrieve \
#     -H "Content-Type: application/json" \
#     -d '{"query": "What are the constraints on Windows updates?"}'
