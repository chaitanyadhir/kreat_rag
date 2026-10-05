import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tools.retriever_store import get_retriever, index_exists

logger = logging.getLogger(__name__)
router = APIRouter()


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_n: int = Field(default=3, ge=1, le=20)


@router.post("/api/retrieve")
async def retrieve_chunks(payload: RetrievalRequest):
    if not index_exists():
        raise HTTPException(status_code=404, detail="No documents indexed yet. Upload one first.")
    try:
        result = await get_retriever().retrieve(
            query=payload.query, dense_k=10, sparse_k=10, top_n=payload.top_n
        )
        return {"success": True, "data": result}
    except Exception:
        logger.exception("Retrieval failed")
        raise HTTPException(status_code=500, detail="Retrieval failed")