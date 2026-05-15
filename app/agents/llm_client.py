"""
OpenRouter-compatible LLM client with retry and fallback handling.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback models if primary is unavailable (404/429)
FALLBACK_MODELS = [
    "mistralai/mistral-small-3.1-24b-instruct",
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
]


class LLMClient:
    """Thin wrapper around OpenRouter chat completions API."""

    def __init__(self) -> None:
        self.base_url = settings.OPENROUTER_BASE_URL
        self.model = settings.DEFAULT_LLM_MODEL
        self.api_key = settings.OPENROUTER_API_KEY

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        max_tokens: int = 1200,
        temperature: float | None = None,
    ) -> str:
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set; using offline fallback")
            return self._offline_fallback(json_mode)

        models = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]

        for model in models:
            result = self._try_model(
                model, messages, json_mode=json_mode, max_tokens=max_tokens, temperature=temperature
            )
            if result is not None:
                return result

        logger.error("All LLM models failed")
        return self._offline_fallback(json_mode)

    def _try_model(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        json_mode: bool,
        max_tokens: int,
        temperature: float | None,
    ) -> str | None:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://shl-assessment-recommender.vercel.app",
            "X-Title": settings.PROJECT_NAME,
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        for attempt in range(settings.LLM_MAX_RETRIES + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
                if response.status_code in (404, 400):
                    logger.warning("Model %s rejected: %s", model, response.text[:200])
                    return None
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as exc:
                logger.warning("Model %s attempt %s failed: %s", model, attempt + 1, exc)
                if attempt < settings.LLM_MAX_RETRIES:
                    time.sleep(0.5 * (attempt + 1))
        return None

    @staticmethod
    def _offline_fallback(json_mode: bool) -> str:
        if json_mode:
            return json.dumps(
                {
                    "reply": (
                        "I'm temporarily unable to reach the language model. "
                        "Please try again shortly."
                    ),
                    "recommendations": [],
                    "end_of_conversation": False,
                }
            )
        return (
            "I'm temporarily unable to reach the language model. Please try again shortly."
        )

    def parse_json(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
