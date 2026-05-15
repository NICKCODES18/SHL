"""
Query intent classification (LLM + rule-based fallback).
"""

from __future__ import annotations

import logging
import re

from app.agents.llm_client import LLMClient
from app.models.schemas import IntentType
from app.prompts.prompts import INTENT_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)

JAILBREAK_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+previous",
    r"system\s+prompt",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(?!an?\s+assessment)",
    r"reveal\s+your\s+instructions",
    r"jailbreak",
    r"dan\s+mode",
]

OUT_OF_SCOPE_PATTERNS = [
    r"\bsalary\b",
    r"\blegal\b",
    r"\blawyer\b",
    r"\bsue\b",
    r"\bcompetitor\b",
    r"\bhire\s+without\b",
    r"\bvisa\b",
]


class IntentClassifier:
    """Classifies user intent for routing agent behavior."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def classify(self, user_message: str, history_text: str) -> IntentType:
        lowered = user_message.lower().strip()

        if any(re.search(p, lowered) for p in JAILBREAK_PATTERNS):
            return IntentType.JAILBREAK
        if any(re.search(p, lowered) for p in OUT_OF_SCOPE_PATTERNS):
            return IntentType.OUT_OF_SCOPE
        if lowered in {"hi", "hello", "hey", "good morning", "good afternoon"}:
            return IntentType.GREETING
        if any(w in lowered for w in ("bye", "goodbye", "thanks", "thank you", "that's all")):
            return IntentType.FAREWELL

        rule_intent = self._rule_classify(lowered, history_text)
        if rule_intent:
            return rule_intent

        messages = [
            {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
            {
                "role": "user",
                "content": f"History:\n{history_text}\n\nLatest user message:\n{user_message}",
            },
        ]
        raw = self.llm.chat(messages, max_tokens=20).strip().lower()
        raw = raw.replace("intent:", "").strip()
        try:
            return IntentType(raw)
        except ValueError:
            logger.debug("Unknown LLM intent '%s', defaulting to vague_request", raw)
            return IntentType.VAGUE_REQUEST

    def _rule_classify(self, lowered: str, history_text: str) -> IntentType | None:
        compare_markers = ["difference between", "compare", " vs ", " versus ", "better than"]
        if any(m in lowered for m in compare_markers):
            return IntentType.COMPARISON

        refinement_markers = [
            "actually",
            "instead",
            "also add",
            "add personality",
            "add cognitive",
            "remove ",
            "only show",
            "filter",
            "refine",
            "more ",
            "less ",
        ]
        if history_text and any(m in lowered for m in refinement_markers):
            return IntentType.REFINEMENT

        if any(m in lowered for m in ("why did you", "why recommend", "what does", "explain ")):
            return IntentType.EXPLANATION

        vague_markers = [
            "i need an assessment",
            "i need a test",
            "hiring assessment",
            "recommend something",
            "what should i use",
            "help me choose",
        ]
        if any(m in lowered for m in vague_markers):
            return IntentType.VAGUE_REQUEST

        detail_signals = [
            "developer",
            "engineer",
            "manager",
            "years",
            "senior",
            "junior",
            "mid-level",
            "java",
            "python",
            "personality",
            "cognitive",
            "coding",
            "stakeholder",
            "leadership",
            "entry level",
            "job description",
        ]
        if sum(1 for s in detail_signals if s in lowered) >= 2:
            return IntentType.DETAILED_REQUEST

        return None
