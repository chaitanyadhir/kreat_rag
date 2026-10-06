"""Chat-session persistence helpers and conversation-history formatting."""

import re
from datetime import datetime, timezone

from sqlmodel import Session, select

from db.models import ChatMessage, ChatSession

HISTORY_TURNS = 6          # most recent completed messages (user + assistant) sent to the LLM
HISTORY_MSG_CHARS = 1000   # per-message cap so history can't crowd out retrieved context
TITLE_CHARS = 60

# Old answers say "[Source 1]" but those numbers refer to *that* turn's context.
# Left in, they'd collide with the current turn's labels, so strip them.
_CITE = re.compile(r"\s*\[Source \d+(?:\s*,\s*Source \d+)*\]")


def make_title(query: str) -> str:
    q = " ".join(query.split())
    return q if len(q) <= TITLE_CHARS else q[: TITLE_CHARS - 1].rstrip() + "…"


def touch(session: Session, chat: ChatSession) -> None:
    chat.updated_at = datetime.now(timezone.utc)
    session.add(chat)


def format_history(messages: list[ChatMessage]) -> str:
    """Render prior completed turns as plain text for the prompt ('' if none)."""
    done = [m for m in messages if m.status == "done" and m.content.strip()]
    lines = []
    for m in done[-HISTORY_TURNS:]:
        text = m.content if m.role == "user" else _CITE.sub("", m.content)
        text = text.strip()[:HISTORY_MSG_CHARS]
        lines.append(f"{'User' if m.role == 'user' else 'Assistant'}: {text}")
    return "\n".join(lines)


def load_history(session: Session, session_id: int) -> str:
    rows = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_TURNS * 2)  # over-fetch: failed turns are filtered out afterwards
    ).all()
    return format_history(list(reversed(rows)))
