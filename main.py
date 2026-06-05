import os
import sys
from fastapi import FastAPI

# Add project root to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import routers from controllers
from controllers.parser_api import router as parser_router
from controllers.split_embed_api import router as split_embed_router
from controllers.retreiver_api import router as retriever_router


# ==========================================
# MAIN FASTAPI APP
# ==========================================
app = FastAPI(title="Kreat RAG API")


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
