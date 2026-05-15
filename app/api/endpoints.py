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
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.agents.orchestrator import OrchestratorAgent
from app.core.config import settings
from app.models.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


@lru_cache
def get_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent()


def _catalog_count() -> int:
    path = Path(settings.CATALOG_PATH)
    if not path.exists():
        return 0
    try:
        with path.open(encoding="utf-8") as handle:
            return len(json.load(handle))
    except Exception:
        return 0


@router.get("/", response_class=HTMLResponse)
async def frontend() -> FileResponse:
    """Interactive UI for testing health + chat."""
    return FileResponse(INDEX_HTML, media_type="text/html")


@router.get("/chat")
async def chat_browser_redirect() -> RedirectResponse:
    """Browsers GET /chat — send users to the frontend."""
    return RedirectResponse(url="/", status_code=302)


@router.get("/api/info")
async def api_info() -> dict:
    """JSON service metadata (used by frontend status panel)."""
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
    """Readiness probe — must return {\"status\": \"ok\"} with HTTP 200."""
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
) -> ChatResponse:
    """Stateless chat endpoint."""
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
