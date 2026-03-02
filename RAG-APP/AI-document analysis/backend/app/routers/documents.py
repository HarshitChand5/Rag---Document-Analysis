import logging
import mimetypes
import tempfile
import shutil
import asyncio
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks  # type: ignore
from app.config import get_settings  # type: ignore
from app.services.document_parser import read_pdf_tool  # type: ignore
from app.services.vector_tools import upsert_project_paper_chunks, clear_project_index  # type: ignore
from app.clients.s3_client import upload_file as s3_upload, delete_file as s3_delete, generate_presigned_url  # type: ignore
from app.clients.supabase_client import (  # type: ignore
    insert_document,
    update_document_status,
    insert_chunks_metadata,
    list_documents,
    get_document,
    delete_document,
    get_project_stats,
    is_supabase_enabled,
)
from app.models import IngestResponse  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter()

TEMP_DIR = Path(tempfile.gettempdir()) / "ai_researcher_downloads"
TEMP_DIR.mkdir(exist_ok=True)

ACCEPTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

def cleanup_temp_file(file_path: str):
    try:
        Path(file_path).unlink(missing_ok=True)
        logger.debug("Cleaned up temp file: %s", file_path)
    except Exception as exc:
        logger.warning("Failed to clean up temp file %s: %s", file_path, exc)

def _detect_mime_type(filename: str) -> str:
    """Guess MIME type from filename."""
    mt, _ = mimetypes.guess_type(filename)
    return mt or "application/octet-stream"

async def _run_ingestion_background(
    project_id: str,
    paper_id: str,
    filename: str,
    temp_file_path: Path,
    doc_id: Optional[str],
    mime_type: str,
):
    """Heavy lift of ingestion running in the background."""
    settings = get_settings()
    try:
        # 1. S3 Upload (from disk)
        s3_key: Optional[str] = None
        if settings.s3_enabled:
            with open(temp_file_path, "rb") as f:
                s3_key = s3_upload(
                    project_id, filename, f.read(), content_type=mime_type
                )
            logger.info("Uploaded to S3: %s", s3_key)
        
        # 2. Chunking (PDF Parsing)
        # Using to_thread because PDF parsing and FAISS indexing are CPU bound
        chunks_raw = await asyncio.to_thread(
            read_pdf_tool.invoke,
            {
                "file_path": str(temp_file_path),
                "chunk_size": settings.CHUNK_SIZE,
                "chunk_overlap": settings.CHUNK_OVERLAP,
            }
        )
        chunks: List[Dict[str, Any]] = chunks_raw # type: ignore
        logger.info("Created %d chunks from %s", len(chunks), filename)

        for ch in chunks:
            md = ch.get("metadata") or {}  # type: ignore[union-attr]
            md["title"] = md.get("title") or paper_id  # type: ignore[index]
            md["source"] = md.get("source") or filename  # type: ignore[index]
            md["origin"] = md.get("origin") or "upload"  # type: ignore[index]
            if s3_key:
                md["s3_key"] = s3_key  # type: ignore[index]
            ch["metadata"] = md

        # 3. FAISS Indexing (CPU bound, use to_thread)
        msg = await asyncio.to_thread(
            upsert_project_paper_chunks.invoke,
            {
                "project_id": project_id,
                "paper_id": paper_id,
                "chunks": chunks,
            }
        )
        logger.info(msg)

        # 4. Final Metadata Update
        if doc_id:
            update_document_status(doc_id, "ready", chunk_count=len(chunks))
            insert_chunks_metadata(doc_id, project_id, paper_id, chunks)
            
    except Exception as exc:
        logger.error("Background ingestion error for %s: %s", filename, exc)
        if doc_id:
            update_document_status(doc_id, "error")
    finally:
        cleanup_temp_file(str(temp_file_path))

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Ingest a document: stream to disk, track in DB, then process in background.
    """
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    if not file.filename:
        raise HTTPException(status_code=400, detail="filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(ACCEPTED_EXTENSIONS)}",
        )

    logger.info("Starting ingestion for %s (project: %s)", file.filename, project_id)

    paper_id = Path(file.filename).stem
    ext = Path(file.filename).suffix.lower()
    temp_file_path = TEMP_DIR / f"{uuid.uuid4().hex}{ext}"
    mime_type = _detect_mime_type(file.filename)

    try:
        # 1. Read file and write to disk
        contents = await file.read()
        file_size = len(contents)
        
        with open(temp_file_path, "wb") as buffer:
            buffer.write(contents)

        # 2. Initial record in Supabase (status: processing)
        doc_id = insert_document(
            project_id=project_id,
            paper_id=paper_id,
            filename=file.filename,
            file_size_bytes=file_size,
            chunk_count=0,
            status="processing",
            s3_key=None,  # Will be updated in background
            mime_type=mime_type,
            original_filename=file.filename,
        )

        # 3. Offload heavy work to background
        background_tasks.add_task(
            _run_ingestion_background,
            project_id=project_id,
            paper_id=paper_id,
            filename=file.filename,
            temp_file_path=temp_file_path,
            doc_id=doc_id,
            mime_type=mime_type,
        )

        return IngestResponse(
            status="processing",
            paper_id=paper_id,
            message="Document upload successful. Processing in background.",
        )

    except Exception as exc:
        logger.error("Ingestion setup failed for %s: %s", file.filename, exc)
        cleanup_temp_file(str(temp_file_path))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")

@router.post("/ingest-pdf", response_model=IngestResponse)
async def ingest_pdf(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Legacy endpoint — redirects to /ingest."""
    return await ingest_document(project_id=project_id, background_tasks=background_tasks, file=file)

@router.delete("/clear-project/{project_id}")
async def clear_project(project_id: str):
    """Clear all indexed documents for a project."""
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    cleared = clear_project_index(project_id)
    return {"cleared": cleared, "project_id": project_id}

@router.get("/documents/{project_id}")
async def get_documents(project_id: str):
    """List all documents stored in Supabase for a project."""
    if not is_supabase_enabled():
        return {"documents": [], "supabase_enabled": False}
    docs = list_documents(project_id)
    return {"documents": docs, "supabase_enabled": True}

@router.delete("/documents/{doc_id}")
async def remove_document(doc_id: str):
    """Delete a document from Supabase, S3, and FAISS."""
    if not is_supabase_enabled():
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    project_id = doc.get("project_id")
    s3_key = doc.get("s3_key")

    if s3_key and get_settings().s3_enabled:
        s3_delete(s3_key)

    if project_id:
        clear_project_index(project_id)

    deleted = delete_document(doc_id)
    return {"deleted": deleted, "doc_id": doc_id}

@router.get("/documents/{project_id}/stats")
async def get_doc_stats(project_id: str):
    """Get summary statistics for a project's documents."""
    if not is_supabase_enabled():
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "last_upload": None,
            "supabase_enabled": False,
        }
    stats = get_project_stats(project_id)
    stats["supabase_enabled"] = True
    return stats

@router.get("/documents/download/{doc_id}")
async def download_document(doc_id: str):
    """
    Return a presigned S3 URL for downloading/previewing a document.
    """
    if not is_supabase_enabled():
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    s3_key = doc.get("s3_key")
    if not s3_key:
        raise HTTPException(status_code=404, detail="No S3 file stored for this document")

    url = generate_presigned_url(s3_key)

    return {
        "doc_id": doc_id,
        "filename": doc.get("original_filename") or doc.get("filename"),
        "mime_type": doc.get("mime_type"),
        "url": url,
    }
