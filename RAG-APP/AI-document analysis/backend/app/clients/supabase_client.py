# supabase_client.py — Supabase operations for document metadata

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from dotenv import load_dotenv  # type: ignore

load_dotenv(override=True)

from supabase import create_client, Client  # type: ignore

from app.config import get_settings  # type: ignore

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def _get_client() -> Optional[Client]:
    """Lazy-initialize the Supabase client."""
    global _supabase_client
    settings = get_settings()
    if not settings.supabase_enabled:
        return None
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("Supabase client initialized (url=%s...)", settings.SUPABASE_URL[:30])
    return _supabase_client


def is_supabase_enabled() -> bool:
    return get_settings().supabase_enabled


# =====================================================================
# Document CRUD
# =====================================================================


def insert_document(
    project_id: str,
    paper_id: str,
    filename: str,
    file_size_bytes: int = 0,
    chunk_count: int = 0,
    status: str = "processing",
    s3_key: Optional[str] = None,
    mime_type: Optional[str] = None,
    original_filename: Optional[str] = None,
) -> Optional[str]:
    """Insert a new document record into Supabase. Returns the UUID or None."""
    client = _get_client()
    if client is None:
        logger.warning("Supabase not configured — skipping insert_document")
        return None

    row = {
        "project_id": project_id,
        "paper_id": paper_id,
        "filename": filename,
        "file_size_bytes": file_size_bytes,
        "chunk_count": chunk_count,
        "status": status,
        "s3_key": s3_key,
        "mime_type": mime_type,
        "original_filename": original_filename or filename,
    }

    try:
        result = client.table("documents").insert(row).execute()
        if result.data and len(result.data) > 0:
            doc_id = result.data[0].get("id")
            logger.info("Inserted document %s (id=%s)", filename, doc_id)
            return str(doc_id) if doc_id else None
        return None
    except Exception as exc:
        logger.error("Failed to insert document %s: %s", filename, exc)
        return None


def update_document_status(
    doc_id: str,
    status: str,
    chunk_count: Optional[int] = None,
) -> bool:
    """Update a document's status (and optionally chunk_count)."""
    client = _get_client()
    if client is None:
        return False

    updates: Dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if chunk_count is not None:
        updates["chunk_count"] = chunk_count

    try:
        client.table("documents").update(updates).eq("id", doc_id).execute()
        logger.info("Updated document %s → status=%s", doc_id, status)
        return True
    except Exception as exc:
        logger.error("Failed to update document %s: %s", doc_id, exc)
        return False


def insert_chunks_metadata(
    doc_id: str,
    project_id: str,
    paper_id: str,
    chunks: List[Dict[str, Any]],
) -> int:
    """Insert chunk-level metadata into Supabase. Returns count inserted."""
    client = _get_client()
    if client is None:
        return 0

    rows = []
    for i, ch in enumerate(chunks):
        content = (ch.get("content") or "")
        rows.append({
            "document_id": doc_id,
            "project_id": project_id,
            "paper_id": paper_id,
            "chunk_index": i,
            "page_number": ch.get("page"),
            "content_preview": content[:200] if content else "",
            "char_count": len(content),
        })

    if not rows:
        return 0

    try:
        # Insert in batches of 100
        inserted = 0
        for start in range(0, len(rows), 100):
            batch = rows[start : start + 100]  # type: ignore[index]
            client.table("document_chunks").insert(batch).execute()
            inserted += len(batch)
        logger.info("Inserted %d chunk metadata rows for doc %s", inserted, doc_id)
        return inserted
    except Exception as exc:
        logger.error("Failed to insert chunk metadata for doc %s: %s", doc_id, exc)
        return 0


def list_documents(project_id: str) -> List[Dict[str, Any]]:
    """List all documents for a project, newest first."""
    client = _get_client()
    if client is None:
        return []

    try:
        result = (
            client.table("documents")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("Failed to list documents for project %s: %s", project_id, exc)
        return []


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get a single document by ID."""
    client = _get_client()
    if client is None:
        return None

    try:
        result = client.table("documents").select("*").eq("id", doc_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as exc:
        logger.error("Failed to get document %s: %s", doc_id, exc)
        return None


def delete_document(doc_id: str) -> bool:
    """Delete a document (chunks cascade via DB foreign key)."""
    client = _get_client()
    if client is None:
        return False

    try:
        client.table("documents").delete().eq("id", doc_id).execute()
        logger.info("Deleted document %s from Supabase", doc_id)
        return True
    except Exception as exc:
        logger.error("Failed to delete document %s: %s", doc_id, exc)
        return False


def get_project_stats(project_id: str) -> Dict[str, Any]:
    """Get summary statistics for a project."""
    client = _get_client()
    if client is None:
        return {"total_documents": 0, "total_chunks": 0, "last_upload": None}

    try:
        docs_result = (
            client.table("documents")
            .select("id, chunk_count, created_at")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        docs = docs_result.data or []

        total_documents = len(docs)
        total_chunks = sum(d.get("chunk_count", 0) for d in docs)
        last_upload = docs[0]["created_at"] if docs else None

        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "last_upload": last_upload,
        }
    except Exception as exc:
        logger.error("Failed to get stats for project %s: %s", project_id, exc)
        return {"total_documents": 0, "total_chunks": 0, "last_upload": None}
