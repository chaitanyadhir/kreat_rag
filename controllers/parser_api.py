import os
import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add parent directory to python path to import tools package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.document_parser import ParserFactory


# ==========================================
# REQUEST / RESPONSE MODELS
# ==========================================
class ParseRequest(BaseModel):
    file_path: str


# ==========================================
# ROUTER
# ==========================================
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.post("/api/parse")
async def parse_document(payload: ParseRequest):
    """
    Parses a PDF or PPTX file and returns extracted text page-by-page or slide-by-slide.
    """
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {payload.file_path}")

    try:
        parser = ParserFactory.get_parser(payload.file_path)
        result = parser.parse(payload.file_path)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# EXAMPLE USAGE
# ==========================================
#
# Run:
#   uvicorn controllers.parser_api:app --host 0.0.0.0 --port 8000 --reload
#
# Health Check:
#   curl http://localhost:8000/health
#
# Parse a PDF:
#   curl -X POST http://localhost:8000/api/parse \
#     -H "Content-Type: application/json" \
#     -d '{"file_path": "data/example_policy.pdf"}'
#
# Parse a PPTX:
#   curl -X POST http://localhost:8000/api/parse \
#     -H "Content-Type: application/json" \
#     -d '{"file_path": "data/presentation.pptx"}'