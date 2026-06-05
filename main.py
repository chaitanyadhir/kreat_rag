import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Add project root to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import routers from controllers
from controllers.parser_api import router as parser_router
from controllers.split_embed_api import router as split_embed_router
from controllers.retreiver_api import router as retriever_router, warmup_retriever

logger = logging.getLogger("kreat_rag")


# ==========================================
# LIFESPAN: Pre-load heavy resources at startup
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the server starts. We use this to pre-load the BGE model
    weights and FAISS index so the first /api/retrieve request is fast.
    
    Without this, every cold request would wait 5-15s while SentenceTransformer:
      1. Reads ~1.3GB of model weights from disk
      2. Deserializes PyTorch tensors
      3. Moves them to the compute device (CPU or GPU)
    
    With the lifespan hook, this happens ONCE at boot, and all subsequent
    requests reuse the warm model in memory (~50ms inference).
    """
    index_dir = os.environ.get("FAISS_INDEX_DIR", "data/faiss_index")
    if os.path.exists(index_dir):
        logger.info("Warming up HybridRetriever (loading BGE model + FAISS index)...")
        try:
            warmup_retriever(index_directory=index_dir)
            logger.info("HybridRetriever warm-up complete.")
        except Exception as e:
            logger.warning(f"Could not warm up retriever (index may not exist yet): {e}")
    else:
        logger.info(f"No FAISS index found at '{index_dir}'. Skipping warm-up. Run /api/ingest first.")
    yield


# ==========================================
# MAIN FASTAPI APP
# ==========================================
app = FastAPI(title="Kreat RAG API", lifespan=lifespan)


# Health check for the main app
@app.get("/health")
async def health():
    return {"status": "healthy"}


# Include all controller routers
app.include_router(parser_router, tags=["Parser"])
app.include_router(split_embed_router, tags=["Split & Embed"])
app.include_router(retriever_router, tags=["Retrieval"])


# ==========================================
# EXAMPLE USAGE
# ==========================================
#
# Run:
#   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
#
# All endpoints available at http://localhost:8000:
#
#   GET  /health                - Health check
#   POST /api/parse             - Parse a PDF/PPTX file
#   POST /api/ingest            - Parse, split, embed, and save to FAISS
#   POST /api/retrieve          - Hybrid retrieval (dense + BM25 + RRF)
#
# Swagger docs at: http://localhost:8000/docs
