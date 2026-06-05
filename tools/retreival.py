import os
import sys
import re
import json
import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.split_embed import FAISSVectorStore, BGEEmbedder, ChildChunk, ParentChunk


# =====================================================================
# WHY MODEL LOADING IS SLOW & THE WORKAROUND
# =====================================================================
#
# Problem:
#   BGE-large-en-v1.5 is a ~1.3GB transformer model. Every time HybridRetriever
#   is instantiated, SentenceTransformer downloads (first run) or loads the model
#   weights from disk into RAM, then moves tensors to the compute device (CPU/GPU).
#   This takes 5-15 seconds per cold start.
#
#   If you create a new HybridRetriever per request (like the old code did),
#   you pay that 5-15s penalty on EVERY request — completely unacceptable.
#
# Workaround (Singleton Pattern):
#   We load the HybridRetriever ONCE at application startup using FastAPI's
#   lifespan event, then reuse that single instance across all requests.
#   The BGE model weights stay warm in memory, so subsequent queries only
#   pay the ~50ms inference cost, not the multi-second loading cost.
#
#   See main.py for the lifespan startup hook.
# =====================================================================


# Thread pool for running CPU-bound search operations in parallel
_thread_pool = ThreadPoolExecutor(max_workers=2)


class HybridRetriever:
    """
    Hybrid retrieval pipeline that combines:
      1. Dense vector search (cosine similarity via FAISS)
      2. Sparse keyword search (BM25)
    Then fuses rankings using Reciprocal Rank Fusion (RRF).

    Optimized with:
      - Singleton pattern: load model weights once, reuse across requests.
      - Async parallel search: dense and sparse searches run concurrently
        via asyncio.gather + ThreadPoolExecutor.
    """

    def __init__(
        self,
        index_directory: str = "data/faiss_index",
        model_name: str = "BAAI/bge-large-en-v1.5",
        embedding_dimension: int = 1024,
        rrf_k: int = 60
    ):
        self.index_directory = index_directory
        self.model_name = model_name
        self.embedding_dimension = embedding_dimension
        self.rrf_k = rrf_k

        # Load FAISS index and metadata from disk
        self.vector_store = FAISSVectorStore(dimension=embedding_dimension)
        self.vector_store.load(index_directory)

        # Load embedder for query encoding (this is the expensive step)
        self.embedder = BGEEmbedder(model_name=model_name)

        # Force-load model weights NOW so first request is fast
        self.embedder.embed_query("warmup")

        # Build BM25 index over child chunk texts
        self.bm25 = None
        self._build_bm25_index()

    # =========================================================
    # BM25 INDEX CONSTRUCTION
    # =========================================================
    def _build_bm25_index(self):
        """Builds an in-memory BM25 index over all child chunks."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            raise ImportError(
                "The 'rank_bm25' library is required for BM25 retrieval. "
                "Please install it using: pip install rank_bm25"
            )

        self.tokenized_corpus = [
            self._tokenize(chunk.text) for chunk in self.vector_store.child_chunks
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace tokenizer with lowercasing and punctuation stripping."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()

    # =========================================================
    # DENSE RETRIEVAL (FAISS Cosine Similarity)
    # =========================================================
    def _dense_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Returns top_k child chunks ranked by cosine similarity (via FAISS)."""
        query_emb = self.embedder.embed_query(query)
        results = self.vector_store.similarity_search(query_emb, k=top_k)
        return results

    # =========================================================
    # SPARSE RETRIEVAL (BM25 Keyword Search)
    # =========================================================
    def _sparse_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Returns top_k child chunks ranked by BM25 keyword relevance."""
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in ranked_indices:
            child = self.vector_store.child_chunks[idx]
            parent = self.vector_store.parent_chunks.get(child.parent_id)
            results.append({
                "score": float(scores[idx]),
                "child": {
                    "id": child.id,
                    "text": child.text,
                    "metadata": child.metadata
                },
                "parent": {
                    "id": parent.id if parent else None,
                    "text": parent.text if parent else "",
                    "metadata": parent.metadata if parent else {}
                }
            })
        return results

    # =========================================================
    # RECIPROCAL RANK FUSION (RRF)
    # =========================================================
    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Combines dense and sparse ranked lists using Reciprocal Rank Fusion.

        RRF_Score(d) = SUM over each list m: 1 / (k + rank_m(d))

        - k is a constant (default 60) to prevent a single high rank from dominating.
        - rank_m(d) is the 1-based rank of document d in list m.
        """
        rrf_scores: Dict[str, float] = {}
        chunk_data: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(dense_results, start=1):
            child_id = item["child"]["id"]
            rrf_scores[child_id] = rrf_scores.get(child_id, 0.0) + (1.0 / (self.rrf_k + rank))
            chunk_data[child_id] = item

        for rank, item in enumerate(sparse_results, start=1):
            child_id = item["child"]["id"]
            rrf_scores[child_id] = rrf_scores.get(child_id, 0.0) + (1.0 / (self.rrf_k + rank))
            if child_id not in chunk_data:
                chunk_data[child_id] = item

        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_n]

        fused_results = []
        for child_id in sorted_ids:
            item = chunk_data[child_id]
            fused_results.append({
                "rrf_score": round(rrf_scores[child_id], 6),
                "child": item["child"],
                "parent": item["parent"]
            })

        return fused_results

    # =========================================================
    # PUBLIC API: ASYNC RETRIEVE (parallel dense + sparse)
    # =========================================================
    async def retrieve(self, query: str, dense_k: int = 10, sparse_k: int = 10, top_n: int = 3) -> Dict[str, Any]:
        """
        Full hybrid retrieval pipeline with PARALLEL search:
          1. Fires dense search (FAISS) and sparse search (BM25) concurrently
          2. Waits for both to finish
          3. Fuses with RRF and returns top_n results

        Both searches are CPU-bound, so we offload them to a ThreadPoolExecutor
        and await them concurrently using asyncio.gather.
        """
        loop = asyncio.get_event_loop()

        # Run both searches in parallel on separate threads
        dense_future = loop.run_in_executor(_thread_pool, self._dense_search, query, dense_k)
        sparse_future = loop.run_in_executor(_thread_pool, self._sparse_search, query, sparse_k)

        dense_results, sparse_results = await asyncio.gather(dense_future, sparse_future)

        # RRF fusion is lightweight, runs on the main thread
        fused = self._reciprocal_rank_fusion(dense_results, sparse_results, top_n=top_n)

        return {
            "query": query,
            "dense_hits": len(dense_results),
            "sparse_hits": len(sparse_results),
            "fused_top_results": fused
        }


# ==========================================
# EXAMPLE USAGE
# ==========================================
#
# if __name__ == "__main__":
#     import asyncio
#     retriever = HybridRetriever(index_directory="data/faiss_index")
#     result = asyncio.run(retriever.retrieve("What are the constraints on Windows updates?"))
#     print(json.dumps(result, indent=2))
