import logging
import os

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from db.models import ChatMessage, ChatSession
from db.session import engine
from tools.chat_history import load_history, make_title, touch
from tools.llm_provider import allm_call, astream_call
from tools.request_creation import create_request
from tools.retriever_store import get_retriever, index_exists

logger = logging.getLogger(__name__)
router = APIRouter()

NO_ANSWER = "I couldn't find this in the uploaded documents."


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_n: int = Field(default=4, ge=1, le=10)
    session_id: int | None = None  # websocket only; /api/ask stays stateless


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



@router.websocket("/ws/ask")
async def ask_ws(ws: WebSocket):
    await ws.accept()
    session_id: int | None = None
    parts: list[str] = []
    sources: list = []
    final_status = "interrupted"  # overwritten on done/error; stays if the client drops mid-stream
    try:
        try:
            payload = AskRequest(**await ws.receive_json())
        except Exception:
            return await ws.send_json({"type": "error", "detail": "Invalid request"})
        if not index_exists():
            return await ws.send_json({"type": "error", "detail": "No documents indexed yet. Upload one first."})
        if not os.getenv("GEMINI_API_KEY"):
            return await ws.send_json({"type": "error", "detail": "LLM is not configured"})

        # --- session: resume an existing one, or lazily create on the first question ---
        with Session(engine) as db:
            if payload.session_id is not None:
                chat = db.get(ChatSession, payload.session_id)
                if chat is None:
                    return await ws.send_json({"type": "error", "detail": "Session not found"})
                history = load_history(db, chat.id)
            else:
                chat = ChatSession(title=make_title(payload.query))
                db.add(chat)
                db.commit()
                db.refresh(chat)
                history = ""
            session_id = chat.id
            db.add(ChatMessage(session_id=session_id, role="user", content=payload.query))
            touch(db, chat)
            db.commit()
            title = chat.title
        await ws.send_json({"type": "session", "id": session_id, "title": title})

        retrieval = await get_retriever().retrieve(
            query=payload.query, dense_k=10, sparse_k=10, top_n=payload.top_n
        )
        results = retrieval.get("fused_top_results", [])
        if not results:
            parts.append(NO_ANSWER)
            await ws.send_json({"type": "sources", "sources": []})
            await ws.send_json({"type": "token", "text": NO_ANSWER})
            final_status = "done"
            return await ws.send_json({"type": "done"})

        prompt, sources = create_request(payload.query, results, history)
        await ws.send_json({"type": "sources", "sources": sources})  # known before the LLM runs
        async for text in astream_call(prompt):
            parts.append(text)
            await ws.send_json({"type": "token", "text": text})
        final_status = "done"
        await ws.send_json({"type": "done"})
    except WebSocketDisconnect:
        logger.info("Client disconnected mid-stream")  # loop exits, generation stops
    except Exception:
        logger.exception("WS ask failed")
        final_status = "error"
        try:
            await ws.send_json({"type": "error", "detail": "Answer generation failed"})
        except Exception:
            pass
    finally:
        # Persist whatever was produced, even a partial answer, so history stays consistent.
        try:
            if session_id is not None:
                _save_assistant(session_id, "".join(parts), sources, final_status)
        except Exception:
            logger.exception("Failed to save assistant message")
        try:
            await ws.close()
        except Exception:
            pass


def _save_assistant(session_id: int, text: str, sources: list, status: str) -> None:
    with Session(engine) as db:
        db.add(ChatMessage(
            session_id=session_id, role="assistant", content=text,
            sources=sources or None, status=status,
        ))
        chat = db.get(ChatSession, session_id)
        if chat:
            touch(db, chat)
        db.commit()
