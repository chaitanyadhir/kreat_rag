import os
import logging
import tempfile
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from sqlmodel import Session

from db.session import get_session, engine
from db.models import Document
from tools.split_embed import IngestPipeline
from tools.retriever_store import reload_retriever

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _set_status(document_id: int, status: str, chunk_count=None, error=None):
    with Session(engine) as session:
        doc = session.get(Document, document_id)
        if doc:
            doc.status = status
            doc.chunk_count = chunk_count
            doc.error_message = error
            session.add(doc)
            session.commit()


def run_ingestion_task(document_id: int, file_path: str, original_filename: str):
    try:
        result = IngestPipeline().ingest(
            file_path, original_filename=original_filename, document_id=document_id
        )
        _set_status(document_id, "success", chunk_count=result["children_created"])
    except Exception as e:
        logger.exception(f"Ingestion failed for document {document_id}")
        _set_status(document_id, "failed", error=str(e)[:500])
        return
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                logger.warning(f"Could not remove temp file {file_path}")

    # Ingest succeeded; a reload failure must not flip the status to failed
    try:
        reload_retriever()
    except Exception:
        logger.exception("Retriever reload failed after ingest")


@router.post("/api/ingest")
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in (".pdf", ".pptx"):
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files are supported")

    temp_path = None
    document = None
    try:
        size = 0
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            temp_path = tmp.name
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File too large (max 25 MB)")
                tmp.write(chunk)

        document = Document(filename=file.filename, status="processing")
        session.add(document)
        session.commit()
        session.refresh(document)

        background_tasks.add_task(run_ingestion_task, document.id, temp_path, file.filename)

    except HTTPException:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception:
        logger.exception(f"Failed to start ingestion for {file.filename}")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if document and document.id:
            _set_status(document.id, "failed", error="Failed to queue ingestion")
        raise HTTPException(status_code=500, detail="Failed to process upload")

    return {
        "success": True,
        "status": "processing",
        "document_id": document.id,
        "filename": file.filename,
    }