"""
Application configuration via environment variables.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "SHL Assessment Recommender API"
    OPENROUTER_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "mistralai/mistral-small-3.1-24b-instruct"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Retrieval
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIRECTORY: str = str(PROJECT_ROOT / "data" / "chroma_db")
    CATALOG_PATH: str = str(PROJECT_ROOT / "data" / "catalog.json")
    BM25_INDEX_PATH: str = str(PROJECT_ROOT / "data" / "bm25_corpus.json")
    TFIDF_INDEX_PATH: str = str(PROJECT_ROOT / "data" / "tfidf.joblib")

    # Force light retrieval (BM25 + TF-IDF) — auto on Vercel
    USE_LIGHT_RETRIEVAL: bool = False

    # Retrieval tuning
    DENSE_TOP_K: int = 40
    SPARSE_TOP_K: int = 40
    RRF_K: int = 60
    RERANK_TOP_K: int = 25
    FINAL_TOP_K: int = 10

    # LLM
    LLM_TIMEOUT_SECONDS: int = 28
    LLM_MAX_RETRIES: int = 2
    LLM_TEMPERATURE: float = 0.1

    # Agent policy
    MAX_CLARIFICATION_TURNS: int = 2
    MIN_RECOMMENDATION_COUNT: int = 1
    MAX_RECOMMENDATION_COUNT: int = 10

    # Allowed URL domain
    ALLOWED_URL_PREFIX: str = "https://www.shl.com"

    @property
    def is_serverless(self) -> bool:
        """True on Vercel / when heavy Chroma stack should be skipped."""
        if self.USE_LIGHT_RETRIEVAL:
            return True
        return bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
