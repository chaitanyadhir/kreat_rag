from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlmodel import Session, select

from db.models import ChatMessage, ChatSession
from db.session import get_session

router = APIRouter()


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


def _get_or_404(session: Session, session_id: int) -> ChatSession:
    chat = session.get(ChatSession, session_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return chat


@router.get("/api/sessions")
def list_sessions(session: Session = Depends(get_session)):
    return session.exec(
        select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(200)
    ).all()


@router.post("/api/sessions")
def create_session(session: Session = Depends(get_session)):
    chat = ChatSession()
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


@router.get("/api/sessions/{session_id}")
def get_chat(session_id: int, session: Session = Depends(get_session)):
    chat = _get_or_404(session, session_id)
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
    ).all()
    return {"session": chat, "messages": messages}


@router.patch("/api/sessions/{session_id}")
def rename_session(
    session_id: int, payload: RenameRequest, session: Session = Depends(get_session)
):
    chat = _get_or_404(session, session_id)
    chat.title = payload.title.strip() or chat.title
    session.add(chat)  # rename deliberately does NOT bump updated_at / reorder the list
    session.commit()
    session.refresh(chat)
    return chat


@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: int, session: Session = Depends(get_session)):
    chat = _get_or_404(session, session_id)
    # Explicit delete: don't rely on the FK's ON DELETE CASCADE existing on older DBs.
    session.exec(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    session.delete(chat)
    session.commit()
    return {"success": True}
