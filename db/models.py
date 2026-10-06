from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    status: str
    chunk_count: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class ChatSession(SQLModel, table=True):
    """One conversation. Named ChatSession to avoid clashing with sqlmodel.Session."""
    __tablename__ = "chat_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default="New chat", max_length=200)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chat_session.id", index=True, ondelete="CASCADE")
    role: str  # "user" | "assistant"
    content: str = Field(default="")
    # "done" | "error" | "interrupted". Only "done" turns are fed back to the LLM.
    status: str = Field(default="done")
    sources: Optional[list] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
