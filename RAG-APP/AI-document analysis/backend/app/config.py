# config.py — Centralized settings loaded from .env

from __future__ import annotations

import os
import logging
from functools import lru_cache

from dotenv import load_dotenv 

load_dotenv(override=True)

logger = logging.getLogger(__name__)


class Settings:
    """All RAG system settings, loaded once from environment variables."""

    def __init__(self) -> None:
        # ── LLM ──────────────────────────────────────────────────────
        self.GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
        self.GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

        # ── Supabase (metadata store) ────────────────────────────────
        self.SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
        self.SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

        # ── AWS S3 ───────────────────────────────────────────────────
        self.AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
        self.AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "")

        # ── Chunking ─────────────────────────────────────────────────
        self.CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1200"))
        self.CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

        # ── Embeddings ───────────────────────────────────────────────
        self.EMBEDDING_MODEL_NAME: str = os.getenv(
            "EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5"
        )

        # ── Signed URL expiry (seconds) ──────────────────────────────
        self.SIGNED_URL_EXPIRY: int = int(os.getenv("SIGNED_URL_EXPIRY", "3600"))

    # ── Helpers ──────────────────────────────────────────────────────

    @property
    def s3_enabled(self) -> bool:
        return bool(
            self.AWS_ACCESS_KEY_ID
            and self.AWS_SECRET_ACCESS_KEY
            and self.AWS_S3_BUCKET
        )

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_KEY)

    def to_dict(self) -> dict:
        """Return non-secret settings for the /settings endpoint."""
        return {
            "chunk_size": self.CHUNK_SIZE,
            "chunk_overlap": self.CHUNK_OVERLAP,
            "embedding_model": self.EMBEDDING_MODEL_NAME,
            "llm_provider": self.LLM_PROVIDER,
            "s3_enabled": self.s3_enabled,
            "supabase_enabled": self.supabase_enabled,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
