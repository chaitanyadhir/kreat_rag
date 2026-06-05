import os
import sys
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager

# Add parent directory to python path to import tools package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.document_parser import ParserFactory

# ==========================================
# 1. INITIALIZE FASTMCP SERVER
# ==========================================
# We configure stateless_http=True and json_response=True for seamless FastAPI hosting
mcp_server = FastMCP(
    "Document Parser MCP Server",
    stateless_http=True,
    json_response=True
)

# ==========================================
# 2. DEFINE MCP TOOLS
# ==========================================
@mcp_server.tool()
async def parse_document(file_path: str) -> list:
    """
    Parses a PDF or PPTX file and returns its extracted text page-by-page or slide-by-slide.
    
    Args:
        file_path (str): Path to the document (e.g. "data/policy.pdf").
        
    Returns:
        list: Extracted pages/slides with text and metadata.
    """
    try:
        parser = ParserFactory.get_parser(file_path)
        return parser.parse(file_path)
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
    title="Document Parser MCP FastAPI Service",
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
#    pip install fastapi uvicorn mcp pypdf python-pptx
#
# 2. Start the server using uvicorn:
#    uvicorn controllers.parser_mcp:app --host 0.0.0.0 --port 8000 --reload
#
# How to Interact with the MCP Endpoints:
# ---------------------------------------
# - Health Check:
#   curl http://localhost:8000/health
#
# - List Available Tools:
#   curl http://localhost:8000/mcp/tools
#
# - Call the 'parse_document' Tool:
#   curl -X POST http://localhost:8000/mcp/tools/call \
#     -H "Content-Type: application/json" \
#     -d '{
#       "name": "parse_document",
#       "arguments": {
#         "file_path": "data/example_policy.pdf"
#       }
#     }'
