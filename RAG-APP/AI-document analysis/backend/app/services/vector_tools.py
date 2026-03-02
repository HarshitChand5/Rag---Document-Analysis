# vector_tools.py

from __future__ import annotations

import os
import time
import logging
from typing import List, Dict, Any, Tuple

from langchain_community.vectorstores.faiss import FAISS  # type: ignore
from langchain_core.documents import Document  # type: ignore
from langchain.tools import tool  # type: ignore
from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "faiss_indexes")

# Free local embedding model (runs via sentence-transformers, no API key). [web:166][web:157]
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
# FAISS index cache (in-memory with TTL)
# ---------------------------------------------------------------------

_faiss_cache: Dict[str, Tuple[FAISS, float]] = {}
CACHE_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _project_index_path(project_id: str) -> str:
    return os.path.join(FAISS_INDEX_DIR, f"project_{project_id}")


def _load_faiss_for_project(project_id: str) -> FAISS | None:
    """
    Load FAISS index for a project, using in-memory cache when available.
    """
    # Check cache first
    if project_id in _faiss_cache:
        vs, loaded_at = _faiss_cache[project_id]
        if time.time() - loaded_at < CACHE_TTL:
            logger.debug("FAISS cache hit for project %s", project_id)
            return vs
        else:
            _faiss_cache.pop(project_id, None)
            logger.debug("FAISS cache expired for project %s", project_id)

    # Load from disk
    index_path = _project_index_path(project_id)
    if not os.path.isdir(index_path):
        return None

    try:
        vs = FAISS.load_local(
            index_path,
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
        _faiss_cache[project_id] = (vs, time.time())
        logger.debug("Loaded FAISS index from disk and cached for project %s", project_id)
        return vs
    except Exception as exc:
        logger.warning("Failed to load FAISS index for project %s: %s", project_id, exc)
        return None


def _save_faiss_for_project(project_id: str, vs: FAISS) -> None:
    """
    Persist FAISS index for a project to disk and update the cache.
    """
    index_path = _project_index_path(project_id)
    _ensure_dir(index_path)
    vs.save_local(index_path)
    _faiss_cache[project_id] = (vs, time.time())
    logger.debug("Saved FAISS index for project %s to %s (cache updated)", project_id, index_path)


def clear_project_index(project_id: str) -> bool:
    """
    Delete the FAISS index for a project entirely.
    Call this before re-ingesting a new document so old chunks don't pollute results.
    Returns True if deleted, False if nothing existed.
    """
    import shutil
    _faiss_cache.pop(project_id, None)  # Invalidate cache
    index_path = _project_index_path(project_id)
    if os.path.isdir(index_path):
        shutil.rmtree(index_path)
        logger.info("Cleared FAISS index for project %s at %s (cache invalidated)", project_id, index_path)
        return True
    logger.info("No FAISS index to clear for project %s", project_id)
    return False


def _chunks_to_documents(
    project_id: str,
    paper_id: str,
    chunks: List[Dict[str, Any]],
) -> List[Document]:
    """
    Convert chunk dicts (from read_pdf_tool) into LangChain Documents. [web:35][web:153]
    """
    docs: List[Document] = []
    for ch in chunks:
        content = (ch.get("content") or "").strip()
        if not content:
            continue

        md = dict(ch.get("metadata") or {})
        md.update(
            {
                "project_id": str(project_id),
                "paper_id": str(paper_id),
                "page": ch.get("page"),
                "source": ch.get("source"),
            }
        )
        docs.append(Document(page_content=content, metadata=md))
    return docs


# ---------------------------------------------------------------------
# LangChain tools
# ---------------------------------------------------------------------

@tool("upsert_project_paper_chunks")
def upsert_project_paper_chunks(
    project_id: str,
    paper_id: str,
    chunks: List[Dict[str, Any]],
) -> str:
    """
    Index / update text chunks for a given project and paper in a FAISS vector store.

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

    docs = _chunks_to_documents(project_id, paper_id, chunks)

    vs = _load_faiss_for_project(project_id)
    if vs is None:
        logger.info("Creating new FAISS index for project %s", project_id)
        vs = FAISS.from_documents(docs, get_embeddings())  # builds index with local BGE embeddings. [web:38][web:166]
    else:
        logger.info("Adding documents to existing FAISS index for project %s", project_id)
        vs.add_documents(docs)

    _save_faiss_for_project(project_id, vs)

    msg = f"Indexed {len(docs)} chunks for paper {paper_id} in project {project_id}."
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
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")

    vs = _load_faiss_for_project(project_id)
    if vs is None:
        logger.warning("No FAISS index found for project %s", project_id)
        return []

    # Use similarity_search_with_score to get distance scores for relevance filtering
    docs_with_scores = vs.similarity_search_with_score(query, k=top_k)

    results: List[Dict[str, Any]] = []
    for doc, score in docs_with_scores:
        results.append(
            {
                "content": doc.page_content,
                "metadata": dict(doc.metadata or {}),
                "score": float(score),  # L2 distance; lower = more similar
            }
        )
    logger.info(
        "Retrieved %d chunks for project %s with query %r (scores: %s)",
        len(results),
        project_id,
        query,
        [f"{r['score']:.3f}" for r in results[:5]],  # type: ignore[index]
    )
    return results


@tool("list_project_documents")
def list_project_documents(project_id: str) -> List[Dict[str, Any]]:
    """List unique documents indexed for a project based on stored chunk metadata."""
    vs = _load_faiss_for_project(project_id)
    if vs is None:
        logger.warning("No FAISS index found for project %s", project_id)
        return []

    documents: Dict[str, Dict[str, Any]] = {}
    try:
        for doc in vs.docstore._dict.values():  # type: ignore[attr-defined]
            md = dict(getattr(doc, "metadata", {}) or {})
            paper_id = str(md.get("paper_id") or "")
            if not paper_id:
                continue

            title = md.get("title") or md.get("source") or paper_id
            origin = md.get("origin")
            source = md.get("source")
            pdf_url = md.get("pdf_url")

            if paper_id not in documents:
                documents[paper_id] = {
                    "paper_id": paper_id,
                    "title": title,
                    "origin": origin,
                    "source": source,
                    "pdf_url": pdf_url,
                }
    except Exception as exc:
        logger.warning("Failed to list project documents for %s: %s", project_id, exc)
        return []

    return list(documents.values())


# ---------------------------------------------------------------------
# Simple CLI test
# ---------------------------------------------------------------------

if __name__ == "__main__":
    """
    Manual test in uv project:

    1. Run `uv add ...` as shown in README / above.
    2. Place 'sample.pdf' in project root.
    3. Run: `uv run python vector_tools.py`
    """
    import json
    from app.services.document_parser import _read_pdf_impl  # type: ignore

    logging.basicConfig(level=logging.INFO)

    project_id = "demo_project"
    paper_id = "sample_paper"
    pdf_path = "sample.pdf"

    if not os.path.exists(pdf_path):
        print(f"Place a test PDF at: {pdf_path}")
        raise SystemExit(1)

    print(f"Reading PDF: {pdf_path}")
    chunks = _read_pdf_impl(pdf_path, chunk_size=800, chunk_overlap=100)
    print(f"Got {len(chunks)} chunks; indexing into FAISS with local BGE embeddings...")

    msg = upsert_project_paper_chunks.invoke(
        {
            "project_id": project_id,
            "paper_id": paper_id,
            "chunks": chunks,
        }
    )
    print(msg)

    question = "What is the main contribution of this paper?"
    print(f"\nQuerying with: {question!r}")
    hits = query_project_papers.invoke(
        {
            "project_id": project_id,
            "query": question,
            "top_k": 3,
        }
    )

    print("\nTop chunks:")
    for i, hit in enumerate(hits, start=1):
        print("-" * 80)
        print(f"Hit {i}")
        print("Metadata:", json.dumps(hit["metadata"], indent=2))
        print(hit["content"][:400], "...")
