from fastapi import APIRouter  # type: ignore
from app.config import get_settings  # type: ignore
from app.clients.supabase_client import is_supabase_enabled  # type: ignore
from app.models import ProjectInfoResponse  # type: ignore

router = APIRouter()

@router.get("/")
async def root():
    return {
        "message": "AI Research Assistant API v2 (FAISS + S3 + Supabase)",
        "endpoints": {
            "chat": "POST /chat",
            "chat_stream": "POST /chat-stream",
            "ingest": "POST /ingest",
            "documents": "GET /documents/{project_id}",
            "settings": "GET /settings",
            "health": "GET /health",
            "docs": "/docs",
        },
    }

@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "s3": settings.s3_enabled,
        "supabase": is_supabase_enabled(),
    }

@router.get("/settings")
async def get_rag_settings():
    """Return current RAG configuration (read-only, no secrets)."""
    return get_settings().to_dict()

@router.get("/projects/{project_id}", response_model=ProjectInfoResponse)
async def get_project_info(project_id: str):
    return ProjectInfoResponse(
        project_id=project_id,
        description=f"Research project '{project_id}'",
    )
