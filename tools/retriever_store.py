import os
from typing import Optional

from tools.retrieval import HybridRetriever
from tools.split_embed import INDEX_LOCK

_retriever: Optional[HybridRetriever] = None


def _index_dir() -> str:
    return os.getenv("FAISS_INDEX_DIR", "data/faiss_index")


def index_exists() -> bool:
    d = _index_dir()
    return os.path.exists(os.path.join(d, "index.faiss")) and os.path.exists(
        os.path.join(d, "metadata.json")
    )


def get_retriever() -> HybridRetriever:
    if _retriever is None:
        reload_retriever()
    return _retriever


def reload_retriever() -> HybridRetriever:
    """Rebuild from disk and swap in. Call after every ingest."""
    global _retriever
    with INDEX_LOCK:  # don't read while an ingest is mid-save
        new = HybridRetriever(index_directory=_index_dir())
    _retriever = new  # atomic reference swap; in-flight requests keep the old one
    return new



def reset_retriever() -> None:
    """Drop the in-memory retriever (e.g. after the index is deleted)."""
    global _retriever
    _retriever = None