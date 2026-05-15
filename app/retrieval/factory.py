"""
Retriever factory — Chroma locally, TF-IDF+BM25 on Vercel.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union

from app.core.config import settings

if TYPE_CHECKING:
    from app.retrieval.light_retriever import LightHybridRetriever
    from app.retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)

_instance: Union["HybridRetriever", "LightHybridRetriever", None] = None


def get_retriever() -> Union["HybridRetriever", "LightHybridRetriever"]:
    global _instance
    if _instance is not None:
        return _instance

    if settings.is_serverless:
        from app.retrieval.light_retriever import LightHybridRetriever

        logger.info("Using light retriever (TF-IDF + BM25) for serverless")
        _instance = LightHybridRetriever()
    else:
        from app.retrieval.retriever import HybridRetriever

        logger.info("Using full hybrid retriever (Chroma + BM25)")
        _instance = HybridRetriever()

    return _instance
