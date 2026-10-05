import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tools.llm_provider import allm_call
from tools.request_creation import create_request
from tools.retriever_store import get_retriever, index_exists

logger = logging.getLogger(__name__)
router = APIRouter()

NO_ANSWER = "I couldn't find this in the uploaded documents."


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_n: int = Field(default=4, ge=1, le=10)


@router.post("/api/ask")
async def ask(payload: AskRequest):
    if not index_exists():
        raise HTTPException(status_code=404, detail="No documents indexed yet. Upload one first.")
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="LLM is not configured (GEMINI_API_KEY missing)")

    try:
        retrieval = await get_retriever().retrieve(
            query=payload.query, dense_k=10, sparse_k=10, top_n=payload.top_n
        )
    except Exception:
        logger.exception("Retrieval failed during /api/ask")
        raise HTTPException(status_code=500, detail="Retrieval failed")

    results = retrieval.get("fused_top_results", [])
    if not results:
        return {"success": True, "answer": NO_ANSWER, "sources": []}

    try:
        prompt, sources = create_request(payload.query, results)
        answer = await allm_call(prompt)
    except Exception:
        logger.exception("LLM call failed during /api/ask")
        raise HTTPException(status_code=502, detail="Answer generation failed")

    return {"success": True, "answer": answer.strip(), "sources": sources}