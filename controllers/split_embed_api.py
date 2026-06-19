import os
import sys
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
import tempfile
import shutil
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session 
from db.session import get_session 
from db.models import Document 
# Add parent directory to python path to import tools package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.split_embed import IngestPipeline



# ==========================================
# ROUTER
# ==========================================
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.post("/api/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    index_directory: str = os.getenv("FAISS_INDEX_DIR", "data/faiss_index"),
    session: Session = Depends(get_session),
):
    allowed_extensions = [".pdf", ".pptx"]

    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and PPTX files are supported"
        )

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=file_ext
    ) as temp_file:

        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name
        
    document = Document(
        filename=file.filename,
        status="processing"
    )

    session.add(document)
    session.commit()
    session.refresh(document)
    
    try:
        pipeline = IngestPipeline(index_directory=index_directory)
        result = pipeline.ingest(temp_path)

        document.status = "success"

        document.chunk_count = (
            result.get("children_created")
            if isinstance(result, dict)
            else None
        )

        session.add(document)
        session.commit()

        return {
            "success": True,
            "document_id": document.id,
            "filename": file.filename,
            "data": result
        }

    except ValueError as e:

        document.status = "failed"

        session.add(document)
        session.commit()

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        document.status = "failed"

        session.add(document)
        session.commit()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


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
