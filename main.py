import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from db.init_db import create_db_and_tables
from tools.retriever_store import index_exists, reload_retriever
from controllers.retriever_api import router as retriever_router
# Load environment variables from .env file
load_dotenv()

# Add project root to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import routers from controllers
from controllers.parser_api import router as parser_router
from controllers.split_embed_api import router as split_embed_router

from controllers.documents_api import router as documents_router
logger = logging.getLogger("kreat_rag")


# ==========================================
# LIFESPAN: Pre-load heavy resources at startup
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    if index_exists():
        try:
            logger.info("Loading retriever...")
            reload_retriever()
        except Exception:
            logger.exception("Retriever warm-up failed")
    else:
        logger.info("No index yet. Upload a document via /api/ingest.")
    yield


# ==========================================
# MAIN FASTAPI APP
# ==========================================
app = FastAPI(title="Kreat RAG API", lifespan=lifespan)

# CORS Configuration
origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check for the main app
@app.get("/health")
async def health():
    return {"status": "healthy"}


# Include all controller routers
from controllers.parser_api import router as parser_router
from controllers.split_embed_api import router as split_embed_router
from controllers.retriever_api import router as retriever_router
from controllers.documents_api import router as documents_router

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
