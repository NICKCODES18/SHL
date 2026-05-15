"""
FastAPI routes for the SHL Assessment Recommender.
"""

from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends

from app.agents.orchestrator import OrchestratorAgent
from app.core.config import settings
from app.models.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache
def get_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent()


def _catalog_count() -> int:
    """Read catalog size without loading embeddings (safe for / and /health)."""
    path = Path(settings.CATALOG_PATH)
    if not path.exists():
        return 0
    try:
        with path.open(encoding="utf-8") as handle:
            return len(json.load(handle))
    except Exception:
        return 0


@router.get("/")
async def root() -> dict:
    """Public index — does not load ML models (stays fast for uptime checks)."""
    return {
        "service": "SHL Assessment Recommender",
        "status": "running",
        "mode": "serverless" if settings.is_serverless else "full",
        "catalog_size": _catalog_count(),
        "endpoints": {
            "health": "GET /health",
            "chat": "POST /chat",
            "docs": "GET /docs",
        },
    }


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Readiness probe — must return {\"status\": \"ok\"} with HTTP 200.
    Evaluators may wait up to 2 minutes on cold start; this responds immediately.
    """
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
) -> ChatResponse:
    """
    Stateless chat endpoint.
    Full conversation history must be sent on every request.
    """
    start = time.perf_counter()
    try:
        response = orchestrator.process_chat(request)
        elapsed = int((time.perf_counter() - start) * 1000)
        logger.info(
            "POST /chat ok recs=%s ms=%s",
            len(response.recommendations),
            elapsed,
        )
        return response
    except Exception as exc:
        logger.error("POST /chat failed: %s", exc, exc_info=True)
        return ChatResponse(
            reply=(
                "An error occurred while processing your request. "
                "Please try again."
            ),
            recommendations=[],
            end_of_conversation=False,
        )
