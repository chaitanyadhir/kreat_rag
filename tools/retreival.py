import os
import sys
import json
import math
from typing import List, Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.split_embed import FAISSVectorStore, BGEEmbedder, ChildChunk, ParentChunk


class HybridRetriever:
    """
    Hybrid retrieval pipeline that combines:
      1. Dense vector search (cosine similarity via FAISS)
      2. Sparse keyword search (BM25)
    Then fuses rankings using Reciprocal Rank Fusion (RRF).
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

        # Load embedder for query encoding
        self.embedder = BGEEmbedder(model_name=model_name)

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

        # Tokenize each child chunk text (simple whitespace + lowercase)
        self.tokenized_corpus = [
            self._tokenize(chunk.text) for chunk in self.vector_store.child_chunks
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace tokenizer with lowercasing and punctuation stripping."""
        import re
        # Lowercase, strip punctuation, split on whitespace
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

        # Get top_k indices sorted by BM25 score descending
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

        # Score from dense list (rank is 1-based position)
        for rank, item in enumerate(dense_results, start=1):
            child_id = item["child"]["id"]
            rrf_scores[child_id] = rrf_scores.get(child_id, 0.0) + (1.0 / (self.rrf_k + rank))
            chunk_data[child_id] = item

        # Score from sparse list (rank is 1-based position)
        for rank, item in enumerate(sparse_results, start=1):
            child_id = item["child"]["id"]
            rrf_scores[child_id] = rrf_scores.get(child_id, 0.0) + (1.0 / (self.rrf_k + rank))
            # Only overwrite if not already stored (dense result takes priority for data)
            if child_id not in chunk_data:
                chunk_data[child_id] = item

        # Sort by RRF score descending, take top_n
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
    # PUBLIC API: RETRIEVE
    # =========================================================
    def retrieve(self, query: str, dense_k: int = 10, sparse_k: int = 10, top_n: int = 3) -> Dict[str, Any]:
        """
        Full hybrid retrieval pipeline:
          1. Get top dense_k chunks from FAISS (cosine similarity)
          2. Get top sparse_k chunks from BM25 (keyword match)
          3. Fuse with RRF and return top_n results

        Args:
            query (str): The user question.
            dense_k (int): Number of chunks from dense search.
            sparse_k (int): Number of chunks from sparse search.
            top_n (int): Final number of top-ranked chunks to return.

        Returns:
            Dict with 'query', 'dense_results', 'sparse_results', and 'fused_top_results'.
        """
        dense_results = self._dense_search(query, top_k=dense_k)
        sparse_results = self._sparse_search(query, top_k=sparse_k)
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
#     retriever = HybridRetriever(index_directory="data/faiss_index")
#     result = retriever.retrieve("What are the constraints on Windows updates?")
#     print(json.dumps(result, indent=2))
#
#     # Output:
#     # {
#     #   "query": "What are the constraints on Windows updates?",
#     #   "dense_hits": 10,
#     #   "sparse_hits": 10,
#     #   "fused_top_results": [
#     #     {
#     #       "rrf_score": 0.032258,
#     #       "child": {"id": "parent_3_child_1", "text": "...", "metadata": {}},
#     #       "parent": {"id": "parent_3", "text": "...", "metadata": {}}
#     #     },
#     #     ...
#     #   ]
#     # }
