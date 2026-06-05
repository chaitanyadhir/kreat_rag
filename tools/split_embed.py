import os
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional

# =====================================================================
# DATA CLASSES
# =====================================================================

@dataclass
class ParentChunk:
    """
    Data class representing a large logical section of a document.
    Suitable for feeding into LLMs as context to preserve overall meaning.
    """
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    child_ids: List[str] = field(default_factory=list)


@dataclass
class ChildChunk:
    """
    Data class representing a small, hyper-focused sub-block.
    Optimized for dense vector retrieval to maximize semantic recall accuracy.
    """
    id: str
    parent_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def count_tokens(text: str) -> int:
    """
    Utility function to count tokens using tiktoken (fallback to word estimation).
    """
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback approximation: 1 word is roughly 1.3 tokens
        return int(len(text.split()) * 1.3)


# =====================================================================
# HIERARCHICAL SPLITTER
# =====================================================================

class HierarchicalSplitter:
    """
    Implements a hierarchical parent-child chunking strategy.
    
    1. Parent Chunks:
       - Split dynamically by policy headers (identifying lines starting with emojis, markdown '#', or numbers).
       - Target token size: 1000 to 1200 tokens (if sections exceed this, splits with 100 token overlap).
       
    2. Child Chunks:
       - Split by logical semantic boundaries (paragraphs, bullet points).
       - Target token size: 150 to 200 tokens with 25 to 50 token overlap.
    """
    def __init__(
        self,
        parent_target: int = 1100,
        parent_overlap: int = 100,
        child_target: int = 175,
        child_overlap: int = 35
    ):
        self.parent_target = parent_target
        self.parent_overlap = parent_overlap
        self.child_target = child_target
        self.child_overlap = child_overlap

    def split_document(self, text: str, document_metadata: Dict[str, Any] = None) -> Tuple[List[ParentChunk], List[ChildChunk]]:
        """
        Processes document text and produces a list of ParentChunks and linked ChildChunks.
        """
        doc_metadata = document_metadata or {}
        
        # 1. Identify policy headers (emojis, lists like 1.2., markdown headers #)
        # Using a regex matching Unicode emoji ranges, numbers with dots, or markdown hashes
        header_pattern = re.compile(
            r'^(?:[\U00010000-\U0010ffff]|[\u2600-\u27bf]|\d+(?:\.\d+)*\.|#+)\s+\w+',
            re.MULTILINE
        )
        
        matches = list(header_pattern.finditer(text))
        sections = []
        
        if not matches:
            # Fallback: Treat whole document as one section
            sections.append(text)
        else:
            start = 0
            for match in matches:
                end = match.start()
                if end > start:
                    section_text = text[start:end].strip()
                    if section_text:
                        sections.append(section_text)
                start = end
            # Append trailing section
            section_text = text[start:].strip()
            if section_text:
                sections.append(section_text)

        parent_chunks: List[ParentChunk] = []
        child_chunks: List[ChildChunk] = []
        parent_counter = 0

        # 2. Build Parent Chunks
        for section in sections:
            section_tokens = count_tokens(section)
            
            # If the section fits within the maximum token budget
            if section_tokens <= 1200:
                parent_id = f"parent_{parent_counter}"
                parent_counter += 1
                parent_chunks.append(ParentChunk(
                    id=parent_id,
                    text=section,
                    metadata={**doc_metadata, "split_method": "header_split"}
                ))
            else:
                # If too large, split using sliding window
                sub_sections = self._sliding_window_split(section, self.parent_target, self.parent_overlap)
                for idx, sub_sec in enumerate(sub_sections):
                    parent_id = f"parent_{parent_counter}_{idx}"
                    parent_chunks.append(ParentChunk(
                        id=parent_id,
                        text=sub_sec,
                        metadata={**doc_metadata, "split_method": "sliding_window"}
                    ))
                parent_counter += 1

        # 3. For each Parent Chunk, create associated Child Chunks
        for parent in parent_chunks:
            children = self._split_parent_into_children(parent.text, parent.id)
            parent.child_ids = [c.id for c in children]
            child_chunks.extend(children)

        return parent_chunks, child_chunks

    def _sliding_window_split(self, text: str, target_size: int, overlap: int) -> List[str]:
        """Splits a large block into chunks of approximate target_size tokens with overlap."""
        words = text.split()
        chunks = []
        i = 0
        
        while i < len(words):
            current_words = []
            current_toks = 0
            j = i
            
            while j < len(words) and current_toks < target_size:
                current_words.append(words[j])
                current_toks = count_tokens(" ".join(current_words))
                j += 1
                
            chunks.append(" ".join(current_words))
            
            # Calculate next starting position with overlap
            overlap_words = 0
            overlap_toks = 0
            k = j - 1
            while k > i and overlap_toks < overlap:
                overlap_toks = count_tokens(" ".join(words[k:j]))
                overlap_words += 1
                k -= 1
                
            next_i = j - overlap_words
            if next_i <= i:
                next_i = j  # Force progress
            i = next_i
            
        return chunks

    def _split_parent_into_children(self, parent_text: str, parent_id: str) -> List[ChildChunk]:
        """Splits parent text into child chunks along semantic boundaries (150-200 tokens, 25-50 overlap)."""
        # Split by paragraph breaks or lines starting with bullet points/numbers
        blocks = [b.strip() for b in re.split(r'\n\n|\n(?=\s*[-*•\d]+\.)', parent_text) if b.strip()]
        
        segments = []
        for block in blocks:
            if count_tokens(block) > 200:
                # If a block is too large, split by sentences
                sentences = re.split(r'(?<=[.!?])\s+', block)
                for sentence in sentences:
                    if sentence.strip():
                        segments.append(sentence.strip())
            else:
                segments.append(block)
                
        child_chunks = []
        child_counter = 0
        current_segments = []
        current_tokens = 0
        
        for seg in segments:
            seg_tokens = count_tokens(seg)
            
            if current_tokens + seg_tokens <= 200:
                current_segments.append(seg)
                current_tokens += seg_tokens
            else:
                if current_segments:
                    child_id = f"{parent_id}_child_{child_counter}"
                    child_chunks.append(ChildChunk(
                        id=child_id,
                        parent_id=parent_id,
                        text="\n".join(current_segments)
                    ))
                    child_counter += 1
                    
                    # Backtrack to build overlap segment (25 to 50 tokens)
                    overlap_segments = []
                    overlap_tokens = 0
                    for s in reversed(current_segments):
                        s_tok = count_tokens(s)
                        if overlap_tokens + s_tok <= 50:
                            overlap_segments.insert(0, s)
                            overlap_tokens += s_tok
                        else:
                            if overlap_tokens < 25 and not overlap_segments:
                                overlap_segments.insert(0, s)
                                overlap_tokens += s_tok
                            break
                    current_segments = overlap_segments
                    current_tokens = overlap_tokens
                
                current_segments.append(seg)
                current_tokens += seg_tokens
                
        # Finalize the last chunk
        if current_segments:
            child_id = f"{parent_id}_child_{child_counter}"
            child_chunks.append(ChildChunk(
                id=child_id,
                parent_id=parent_id,
                text="\n".join(current_segments)
            ))
            
        return child_chunks


# =====================================================================
# BGE EMBEDDING WRAPPER
# =====================================================================

class BGEEmbedder:
    """
    OOP Wrapper for loading BGE models (e.g. bge-large-en-v1.5 or bge-m3)
    and generating dense vector embeddings.
    """
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5", device: str = None):
        self.model_name = model_name
        self.device = device
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "The 'sentence-transformers' library is required. "
                    "Please install it using: pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for document chunks."""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """
        Generates query embedding. Adds the recommended search query instruction
        for optimal retrieval quality with BGE models.
        """
        # BGE models recommend query instruction prefix
        prefix = "Represent this sentence for searching relevant passages: "
        query_input = f"{prefix}{query}" if "bge" in self.model_name.lower() else query
        embedding = self.model.encode(query_input, normalize_embeddings=True)
        return embedding.tolist()


# =====================================================================
# FAISS VECTOR STORE INTERFACE
# =====================================================================

class FAISSVectorStore:
    """
    FAISS-based vector store that indexes child chunks and retrieves 
    their larger parent chunks to provide full LLM context.
    """
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = None
        self.child_chunks: List[ChildChunk] = []
        self.parent_chunks: Dict[str, ParentChunk] = {}
        
        try:
            import faiss
            self.index = faiss.IndexFlatIP(dimension)  # Inner Product for Cosine Similarity
        except ImportError:
            # We fail gracefully on instantiation if libraries are not yet installed
            pass

    def _check_faiss(self):
        if self.index is None:
            raise ImportError(
                "The 'faiss' library is required to use FAISSVectorStore. "
                "Please install it using: pip install faiss-cpu (or faiss-gpu)"
            )

    def add_documents(
        self,
        child_chunks: List[ChildChunk],
        parent_chunks: List[ParentChunk],
        embeddings: List[List[float]]
    ):
        """Adds parent-child chunks and dense embeddings to the index."""
        self._check_faiss()
        import numpy as np

        # Add parent chunks to the lookup dictionary
        for parent in parent_chunks:
            self.parent_chunks[parent.id] = parent

        # Record child chunks
        start_idx = len(self.child_chunks)
        self.child_chunks.extend(child_chunks)

        # Build FAISS index
        emb_arr = np.array(embeddings, dtype=np.float32)
        self.index.add(emb_arr)

    def similarity_search(self, query_embedding: List[float], k: int = 4) -> List[Dict[str, Any]]:
        """
        Performs similarity search on child chunks and returns matched 
        child chunks with their corresponding parent chunks.
        """
        self._check_faiss()
        import numpy as np

        q_arr = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(q_arr, k)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.child_chunks):
                continue

            child = self.child_chunks[idx]
            parent = self.parent_chunks.get(child.parent_id)

            results.append({
                "score": float(score),
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

    def save(self, directory: str):
        """Saves the index and mapping database to disk."""
        self._check_faiss()
        import faiss
        os.makedirs(directory, exist_ok=True)
        
        # Save FAISS Index
        faiss.write_index(self.index, os.path.join(directory, "index.faiss"))
        
        # Save metadata mapping
        metadata = {
            "parents": {
                pid: {"id": p.id, "text": p.text, "metadata": p.metadata, "child_ids": p.child_ids}
                for pid, p in self.parent_chunks.items()
            },
            "children": [
                {"id": c.id, "parent_id": c.parent_id, "text": c.text, "metadata": c.metadata}
                for c in self.child_chunks
            ]
        }
        with open(os.path.join(directory, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def load(self, directory: str):
        """Loads index and metadata mapping from disk."""
        import faiss
        
        self.index = faiss.read_index(os.path.join(directory, "index.faiss"))
        self.dimension = self.index.d

        with open(os.path.join(directory, "metadata.json"), "r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.parent_chunks = {
            pid: ParentChunk(id=p["id"], text=p["text"], metadata=p["metadata"], child_ids=p["child_ids"])
            for pid, p in metadata["parents"].items()
        }
        self.child_chunks = [
            ChildChunk(id=c["id"], parent_id=c["parent_id"], text=c["text"], metadata=c["metadata"])
            for c in metadata["children"]
        ]


# ==========================================
# EXAMPLE USAGE (Executable Example in Comments)
# ==========================================
# 
# if __name__ == "__main__":
#     # Dummy Policy Document Text
#     document_text = """
#     🔐 1. Access Management Policy
#     This policy regulates who has access to production servers. Only authorized operations personnel
#     may request administrative privileges. All requests must undergo peer approval.
#     
#     Key Highlights:
#     * All logins require MFA (Multi-Factor Authentication).
#     * Access keys must be rotated every 90 days.
#     
#     Required Records:
#     * Admin logs showing request/approval ID.
#     * Periodic access audits signed off by the Security Officer.
#     
#     🛡️ 2. Anti-Virus Policy
#     This policy regulates security controls installed on server infrastructure.
#     All endpoints must execute active background scanning.
#     
#     Key Highlights:
#     * Signatures must update hourly.
#     * Centralized alert logging to SIEM.
#     """
#     
#     # 1. Initialize splitter and split document into parent-child structure
#     splitter = HierarchicalSplitter()
#     parents, children = splitter.split_document(document_text, {"source": "test_policy.txt"})
#     
#     print(f"Split completed: Produced {len(parents)} Parents and {len(children)} Children.")
#     
#     for p in parents:
#         print(f"\nParent ID: {p.id} (Tokens: {count_tokens(p.text)})")
#         print(f"Text Preview: {p.text[:120]}...")
#         print(f"Child Chunks Linked: {p.child_ids}")
#         
#     for c in children[:3]:
#         print(f"\nChild ID: {c.id} (Parent: {c.parent_id}, Tokens: {count_tokens(c.text)})")
#         print(f"Child Text: {c.text}")
# 
#     # 2. Embedding generation and FAISS Store indexing
#     try:
#         # Embedder using default 'BAAI/bge-large-en-v1.5' (dim = 1024)
#         embedder = BGEEmbedder(model_name="BAAI/bge-large-en-v1.5")
#         
#         # Embed all child chunks
#         child_texts = [c.text for c in children]
#         child_embeddings = embedder.embed_documents(child_texts)
#         
#         # Initialize Vector Store (BGE Large dimensions is 1024)
#         vector_store = FAISSVectorStore(dimension=1024)
#         vector_store.add_documents(children, parents, child_embeddings)
#         
#         # Perform similarity search
#         query = "What is the update frequency for anti-virus signatures?"
#         query_emb = embedder.embed_query(query)
#         results = vector_store.similarity_search(query_emb, k=1)
#         
#         if results:
#             match = results[0]
#             print(f"\n--- RAG Retrieval Match (Score: {match['score']:.4f}) ---")
#             print(f"Matched Child Text: {match['child']['text']}")
#             print(f"\nRetrieved Parent Context (For LLM Synthesis):\n{match['parent']['text']}")
#             
#     except Exception as e:
#         print(f"\nSkipped full vector search run (Expected if libraries/GPU not setup): {e}")
