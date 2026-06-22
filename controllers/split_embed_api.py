import os
import sys
import tempfile
import shutil
from db.session import get_session 
from db.models import Document 
from db.session import engine
from sqlmodel import Session
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.split_embed import IngestPipeline


def run_ingestion_task(document_id: int, file_path: str, index_directory: str, original_filename: str):
    with Session(engine) as session:
        document = session.get(Document, document_id)

        try:
            pipeline = IngestPipeline(index_directory=index_directory)
            result = pipeline.ingest(file_path, original_filename=original_filename)

            document.status = "success"
            document.chunk_count = result.get("children_created")

            session.add(document)
            session.commit()

        except Exception as e:
            document.status = "failed"
            session.add(document)
            session.commit()
            # No raise here — this runs in the background, nothing is listening for an HTTP error

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
# ==========================================
# ROUTER
# ==========================================
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.post("/api/ingest")
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    index_directory: str = os.getenv("FAISS_INDEX_DIR", "data/faiss_index"),
    session: Session = Depends(get_session)
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
    background_tasks.add_task(run_ingestion_task, document.id, temp_path, index_directory, file.filename)
    
    return {
        "success": True,
        "status": "processing",
        "document_id": document.id,
        "filename": file.filename
    }



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
