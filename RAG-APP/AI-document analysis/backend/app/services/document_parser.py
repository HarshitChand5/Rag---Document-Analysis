# read_pdf.py

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from pypdf import PdfReader  # type: ignore
from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
from langchain_core.tools import tool  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Reasonable defaults for RAG over papers.
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200


# ---------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------

@dataclass
class PDFChunk:
    """Lightweight representation of a chunk from a PDF."""

    content: str
    page: Optional[int]
    source: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]


# ---------------------------------------------------------------------
# Core implementation
# ---------------------------------------------------------------------

def _read_pdf_impl(
    file_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """
    Internal implementation: read a PDF and split it into chunks.

    Parameters
    ----------
    file_path : str
        Path to the PDF file on disk.
    chunk_size : int
        Maximum characters per chunk (approx; good range 800–1500).
    chunk_overlap : int
        Overlap between adjacent chunks to preserve context.

    Returns
    -------
    List[Dict[str, Any]]
        Each dict has: content, page, source, metadata.
    """
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if not file_path.lower().endswith(".pdf"):
        raise ValueError(f"Expected a .pdf file, got: {file_path}")

    logger.info("Loading PDF: %s", file_path)

    # Split into overlapping chunks using RecursiveCharacterTextSplitter. [web:13][web:15]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    reader = PdfReader(file_path)
    chunks: List[PDFChunk] = []

    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            page_text = (page.extract_text() or "").strip()
        except Exception:
            page_text = ""

        if not page_text:
            continue

        for piece in splitter.split_text(page_text):
            text = (piece or "").strip()
            if not text:
                continue

            md: Dict[str, Any] = {
                "page": page_idx,
                "source": file_path,
            }
            chunk = PDFChunk(
                content=text,
                page=page_idx,
                source=file_path,
                metadata=md,
            )
            chunks.append(chunk)

    logger.info("Created %d chunks from %s", len(chunks), file_path)
    return [c.to_dict() for c in chunks]


# ---------------------------------------------------------------------
# LangChain tool wrapper
# ---------------------------------------------------------------------

@tool("read_pdf")
def read_pdf_tool(
    file_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """
    Read a local PDF file and return overlapping text chunks.

    Args:
        file_path: Path to the PDF on disk.
        chunk_size: Maximum characters per chunk (e.g., 800–1500).
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        List of dicts with:
        - content: text of the chunk
        - page: page number (if available)
        - source: file path
        - metadata: original loader metadata
    """
    return _read_pdf_impl(
        file_path=file_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


# ---------------------------------------------------------------------
# Simple CLI test
# ---------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Change this to a real PDF path in your project.
    sample_path = "sample.pdf"

    if not os.path.exists(sample_path):
        print(f"Place a test PDF at: {sample_path}")
    else:
        print(f"Reading and splitting: {sample_path}")
        chunks = _read_pdf_impl(sample_path, chunk_size=800, chunk_overlap=100)
        print(f"Total chunks: {len(chunks)}")
        for i, ch in enumerate(chunks[:5], start=1):  # type: ignore[index]
            print("-" * 80)
            print(f"Chunk {i} (page {ch['page']})")
            print(ch["content"][:600], "...")
