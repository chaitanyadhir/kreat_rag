import os
import sys
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager

# Add parent directory to python path to import tools package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.split_embed import HierarchicalSplitter, BGEEmbedder, FAISSVectorStore

# ==========================================
# 1. INITIALIZE FASTMCP SERVER
# ==========================================
mcp_server = FastMCP(
    "Split Embed MCP Server",
    stateless_http=True,
    json_response=True
)

# ==========================================
# 2. DEFINE MCP TOOLS
# ==========================================
@mcp_server.tool()
async def split_text_hierarchically(text: str) -> dict:
    """
    Splits policy text into parent (1000-1200 tokens) and child (150-200 tokens) chunks.
    
    Args:
        text (str): The policy document text to split.
        
    Returns:
        dict: A dictionary containing lists of 'parents' and 'children'.
    """
    try:
        splitter = HierarchicalSplitter()
        parents, children = splitter.split_document(text)
        return {
            "parents": [{"id": p.id, "text": p.text, "child_ids": p.child_ids} for p in parents],
            "children": [{"id": c.id, "parent_id": c.parent_id, "text": c.text} for c in children]
        }
    except Exception as e:
        return {"error": str(e)}


@mcp_server.tool()
async def index_and_search_policy(text: str, query: str) -> list:
    """
    Performs end-to-end splitting, BGE embedding, FAISS indexing, and similarity search.
    Returns the top-matching child chunks alongside their parent context.
    
    Args:
        text (str): The policy document text.
        query (str): The query string to search for.
        
    Returns:
        list: Retrieval matches including scores, child text, and parent context.
    """
    try:
        # 1. Split text into parent-child structure
        splitter = HierarchicalSplitter()
        parents, children = splitter.split_document(text)
        
        if not children:
            return [{"error": "No child chunks were generated from the input text."}]
            
        # 2. Initialize Embedder (BGE Large defaults to 1024 dimensions)
        embedder = BGEEmbedder(model_name="BAAI/bge-large-en-v1.5")
        
        # 3. Embed child chunks
        child_texts = [c.text for c in children]
        child_embeddings = embedder.embed_documents(child_texts)
        
        # 4. Initialize FAISS Vector Store and add documents
        vector_store = FAISSVectorStore(dimension=1024)
        vector_store.add_documents(children, parents, child_embeddings)
        
        # 5. Search for query
        query_emb = embedder.embed_query(query)
        results = vector_store.similarity_search(query_emb, k=1)
        return results
        
    except Exception as e:
        return [{"error": str(e)}]


# ==========================================
# 3. DEFINE FASTAPI APP & LIFESPAN
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure MCP session manager runs during the FastAPI application lifespan
    async with mcp_server.session_manager.run():
        yield

app = FastAPI(
    title="Split Embed MCP FastAPI Service",
    lifespan=lifespan
)

# Mount the MCP server as a sub-app at "/mcp"
app.mount("/mcp", mcp_server.streamable_http_app())

@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy"}


# ==========================================
# EXAMPLE USAGE & RUN INSTRUCTIONS
# ==========================================
#
# How to Run:
# -----------
# 1. Install dependencies:
#    pip install fastapi uvicorn mcp sentence-transformers faiss-cpu numpy
#
# 2. Start the server using uvicorn:
#    uvicorn controllers.split_embed_mcp:app --host 0.0.0.0 --port 8001 --reload
#
# How to Interact with the MCP Endpoints:
# ---------------------------------------
# - Health Check:
#   curl http://localhost:8001/health
#
# - List Available Tools:
#   curl http://localhost:8001/mcp/tools
#
# - Call the 'split_text_hierarchically' Tool:
#   curl -X POST http://localhost:8001/mcp/tools/call \
#     -H "Content-Type: application/json" \
#     -d '{
#       "name": "split_text_hierarchically",
#       "arguments": {
#         "text": "🔐 1. Access Management\nRequires MFA.\n\n🛡️ 2. Endpoint Protection\nRequires antivirus."
#       }
#     }'
#
# - Call the 'index_and_search_policy' Tool:
#   curl -X POST http://localhost:8001/mcp/tools/call \
#     -H "Content-Type: application/json" \
#     -d '{
#       "name": "index_and_search_policy",
#       "arguments": {
#         "text": "🔐 1. Access Policy\nMFA is mandatory.\n\n🛡️ 2. Endpoint Policy\nAntivirus updates hourly.",
#         "query": "How frequent is antivirus updated?"
#       }
#     }'
