# vector_tools.py — pgvector-backed vector store (Supabase)

from __future__ import annotations

import logging
from typing import List, Dict, Any

from langchain_core.documents import Document  # type: ignore
from langchain.tools import tool  # type: ignore
from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore

from app.clients.supabase_client import _get_client  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------
# Embedding model config (same BGE model, runs locally)
# ---------------------------------------------------------------------

import os

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "BAAI/bge-small-en-v1.5",
)

_EMBEDDINGS: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Lazy-load the embedding model."""
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        _EMBEDDINGS = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _EMBEDDINGS


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

EMBEDDINGS_TABLE = "document_embeddings"
BATCH_SIZE = 50  # rows per insert batch


def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts using the local BGE model."""
    return get_embeddings().embed_documents(texts)


def _embed_query(text: str) -> List[float]:
    """Generate embedding for a single query string."""
    return get_embeddings().embed_query(text)


# ---------------------------------------------------------------------
# LangChain tools (same interfaces as before)
# ---------------------------------------------------------------------

@tool("upsert_project_paper_chunks")
def upsert_project_paper_chunks(
    project_id: str,
    paper_id: str,
    chunks: List[Dict[str, Any]],
) -> str:
    """
    Index / update text chunks for a given project and paper in Supabase pgvector.

    Args:
        project_id: ID of the research project.
        paper_id: ID of the paper within that project.
        chunks: List of dicts from read_pdf_tool:
            - content (str)
            - page (int, optional)
            - source (str)
            - metadata (dict)

    Returns:
        Status message.
    """
    if not chunks:
        return f"No chunks provided for paper {paper_id} in project {project_id}."

    client = _get_client()
    if client is None:
        return "Supabase not configured — cannot store embeddings."

    # 1. Prepare content and metadata
    contents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for ch in chunks:
        content = (ch.get("content") or "").strip()
        if not content:
            continue

        md = dict(ch.get("metadata") or {})
        md.update({
            "project_id": str(project_id),
            "paper_id": str(paper_id),
            "page": ch.get("page"),
            "source": ch.get("source"),
        })

        contents.append(content)
        metadatas.append(md)

    if not contents:
        return f"No valid content in chunks for paper {paper_id}."

    # 2. Generate embeddings locally (batch)
    logger.info("Generating embeddings for %d chunks...", len(contents))
    embeddings = _embed_texts(contents)
    logger.info("Embeddings generated (dim=%d)", len(embeddings[0]) if embeddings else 0)

    # 3. Insert into Supabase in batches
    inserted = 0
    for start in range(0, len(contents), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(contents))
        rows = []
        for i in range(start, end):
            rows.append({
                "project_id": project_id,
                "paper_id": paper_id,
                "content": contents[i],
                "metadata": metadatas[i],
                "embedding": embeddings[i],
            })

        try:
            client.table(EMBEDDINGS_TABLE).insert(rows).execute()
            inserted += len(rows)
        except Exception as exc:
            logger.error("Failed to insert embeddings batch %d-%d: %s", start, end, exc)
            raise

    msg = f"Indexed {inserted} chunks for paper {paper_id} in project {project_id} (pgvector)."
    logger.info(msg)
    return msg


@tool("query_project_papers")
def query_project_papers(
    project_id: str,
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant chunks for a question from a project's papers.

    Args:
        project_id: ID of the project.
        query: Natural language query.
        top_k: Number of chunks to return.

    Returns:
        List of dicts:
        - content: text
        - metadata: includes project_id, paper_id, page, source
        - score: L2 distance (lower = more similar)
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")

    client = _get_client()
    if client is None:
        logger.warning("Supabase not configured — cannot query embeddings.")
        return []

    # 1. Generate query embedding
    query_embedding = _embed_query(query)

    # 2. Call the match_documents RPC function
    try:
        result = client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_project_id": project_id,
                "match_count": top_k,
            },
        ).execute()
    except Exception as exc:
        logger.error("pgvector similarity search failed: %s", exc)
        return []

    rows = result.data or []

    # 3. Format results to match the existing interface
    results: List[Dict[str, Any]] = []
    for row in rows:
        metadata = row.get("metadata") or {}
        results.append({
            "content": row.get("content", ""),
            "metadata": metadata,
            "score": float(row.get("similarity", 0)),  # L2 distance
        })

    logger.info(
        "Retrieved %d chunks for project %s with query %r (scores: %s)",
        len(results),
        project_id,
        query,
        [f"{r['score']:.3f}" for r in results[:5]],
    )
    return results


@tool("list_project_documents")
def list_project_documents(project_id: str) -> List[Dict[str, Any]]:
    """List unique documents indexed for a project based on stored embeddings."""
    client = _get_client()
    if client is None:
        logger.warning("Supabase not configured — cannot list documents.")
        return []

    try:
        result = (
            client.table(EMBEDDINGS_TABLE)
            .select("paper_id, metadata")
            .eq("project_id", project_id)
            .execute()
        )
        rows = result.data or []
    except Exception as exc:
        logger.warning("Failed to list project documents for %s: %s", project_id, exc)
        return []

    # Deduplicate by paper_id
    documents: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        paper_id = row.get("paper_id", "")
        if not paper_id or paper_id in documents:
            continue

        md = row.get("metadata") or {}
        title = md.get("title") or md.get("source") or paper_id
        documents[paper_id] = {
            "paper_id": paper_id,
            "title": title,
            "origin": md.get("origin"),
            "source": md.get("source"),
            "pdf_url": md.get("pdf_url"),
        }

    return list(documents.values())


def clear_project_index(project_id: str) -> bool:
    """
    Delete all embeddings for a project from Supabase.
    Returns True if deleted, False if nothing existed or Supabase is not configured.
    """
    client = _get_client()
    if client is None:
        return False

    try:
        result = (
            client.table(EMBEDDINGS_TABLE)
            .delete()
            .eq("project_id", project_id)
            .execute()
        )
        deleted_count = len(result.data) if result.data else 0
        logger.info(
            "Cleared %d embedding rows for project %s from Supabase",
            deleted_count,
            project_id,
        )
        return deleted_count > 0
    except Exception as exc:
        logger.error("Failed to clear embeddings for project %s: %s", project_id, exc)
        return False
