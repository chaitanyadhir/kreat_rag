from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    status: str
    chunk_count: Optional[int] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )