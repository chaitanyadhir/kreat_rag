from db import session
from fastapi import APIRouter, HTTPException, Depends 
from db.session import get_session
from db.models import Document
from sqlmodel import Session, select
import os

router = APIRouter()


@router.get("/api/documents")
def get_documents(
    session: Session = Depends(get_session)
):
    return session.exec(
        select(Document)
    ).all()

@router.delete("/api/documents/{id}")
def delete_document(
    id: int,
    session: Session = Depends(get_session)
):
# todo FAISS index still contains vectors for this document.
# Retrieval results from this source should be filtered post-query
# or the index should be rebuilt after deletion.
    document = session.get(Document, id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    session.delete(document)
    session.commit()
    remaining = session.exec(select(Document)).all()
    if not remaining:
        index_dir = os.getenv("FAISS_INDEX_DIR", "data/faiss_index")
        # wipe the FAISS index directory
        import shutil
        shutil.rmtree(index_dir, ignore_errors=True)
    return {
        "message": "Document deleted successfully"
    }

@router.get("/api/documents/{id}")
def get_document_by_id(
    id: int,
    session: Session = Depends(get_session)
):
    document = session.get(Document, id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    return document