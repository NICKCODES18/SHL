"""
FastAPI application entrypoint.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.endpoints import router as api_router
from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging(json_logs=os.getenv("JSON_LOGS", "false").lower() == "true")
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Conversational SHL Individual Test Solutions recommender",
        version="1.0.0",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router)

    @application.on_event("startup")
    async def startup_event() -> None:
        """
        Pre-warm retriever on always-on hosts (Render/Docker).
        Skip on Vercel so GET /health returns instantly for cold-start probes.
        """
        logger.info("Starting SHL Assessment Recommender (serverless=%s)", settings.is_serverless)
        if settings.is_serverless:
            logger.info("Serverless mode: retriever loads on first /chat (fast /health).")
            return
        from app.retrieval.factory import get_retriever

        try:
            get_retriever()
            logger.info("Retriever pre-warmed.")
        except Exception as exc:
            logger.error("Retriever pre-warm failed: %s", exc)

    return application


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
