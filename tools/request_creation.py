"""Builds the final LLM prompt from the template, the user query and retrieved chunks."""

import re
from pathlib import Path
from typing import Any

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"
MAX_CONTEXT_CHARS = 12000
_REQUIRED_PLACEHOLDERS = ("{chunks_extracted}", "{query}")


def load_prompt_template(path: Path | str = DEFAULT_PROMPT_PATH) -> str:
    """Read the template fresh each time so prompt edits apply without a restart."""
    text = Path(path).read_text(encoding="utf-8")
    missing = [p for p in _REQUIRED_PLACEHOLDERS if p not in text]
    if missing:
        raise ValueError(f"Prompt template {path} is missing placeholders: {missing}")
    return text


def format_chunks(results: list[dict[str, Any]], max_chars: int = MAX_CONTEXT_CHARS):
    """
    Turn retrieval results into a labelled context string.
    Uses the parent text (fuller context) and de-duplicates parents,
    since several top child chunks often share one parent.
    Returns (context_text, sources).
    """
    blocks: list[str] = []
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    used = 0

    for r in results:
        parent = r.get("parent") or {}
        child = r.get("child") or {}

        key = parent.get("id") or child.get("id")
        if key in seen:
            continue
        seen.add(key)

        text = (parent.get("text") or child.get("text") or "").strip()
        if not text:
            continue

        remaining = max_chars - used
        if remaining <= 0:
            break
        text = text[:remaining]
        used += len(text)

        meta = parent.get("metadata") or child.get("metadata") or {}
        source = meta.get("source", "Unknown source")
        n = len(blocks) + 1

        blocks.append(f"[Source {n}: {source}]\n{text}")
        sources.append({
            "id": n,
            "source": source,
            "score": r.get("rrf_score"),
            "snippet": (child.get("text") or text)[:200],
        })

    return "\n\n---\n\n".join(blocks), sources


def build_prompt(prompt_to_pass: str, query: str, chunks: str) -> str:
    """Fill the template. Single-pass substitution, so braces or placeholder-like
    text inside the query or documents are never re-interpreted."""
    values = {"query": query, "chunks_extracted": chunks}
    return re.sub(
        r"\{(query|chunks_extracted)\}",
        lambda m: values[m.group(1)],
        prompt_to_pass,
    )


def create_request(query: str, results: list[dict[str, Any]]):
    """Convenience wrapper: returns (final_prompt, sources)."""
    chunks_text, sources = format_chunks(results)
    prompt = build_prompt(load_prompt_template(), query, chunks_text)
    return prompt, sources