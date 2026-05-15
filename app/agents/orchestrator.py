"""
Main conversational orchestrator — retrieval-grounded, schema-safe.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import List

from app.agents.clarification import ClarificationPolicy
from app.agents.grounding import GroundingValidator
from app.agents.intent_classifier import IntentClassifier
from app.agents.llm_client import LLMClient
from app.agents.recommendation_engine import RecommendationEngine
from app.agents.state_extractor import StateExtractor
from app.core.config import settings
from app.models.schemas import (
    AssessmentRecommendation,
    ChatRequest,
    ChatResponse,
    IntentType,
    role_value,
)
from app.prompts.prompts import (
    COMPARISON_PROMPT,
    REFUSAL_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Stateless agent orchestrating intent, retrieval, and grounded responses."""

    def __init__(self) -> None:
        self.llm = LLMClient()
        self.intent_classifier = IntentClassifier(self.llm)
        self.state_extractor = StateExtractor(self.llm)
        self.recommendation_engine = RecommendationEngine()
        self.clarification = ClarificationPolicy()
        self.grounding = GroundingValidator(
            self.recommendation_engine.retriever.assessments
        )

    def process_chat(self, request: ChatRequest) -> ChatResponse:
        start = time.perf_counter()
        messages = request.messages
        history_text = self._history_text(messages)
        user_msg = messages[-1].content

        intent = self.intent_classifier.classify(user_msg, history_text)
        state = self.state_extractor.extract(messages, intent)
        logger.info("intent=%s ready=%s", intent.value, state.ready_to_recommend)

        if intent == IntentType.JAILBREAK:
            return self._refusal(
                "I can only help with SHL assessment recommendations. "
                "I cannot change my role or share internal instructions."
            )

        if intent == IntentType.OUT_OF_SCOPE:
            return self._refusal(
                "I'm focused on recommending SHL assessments from our catalog. "
                "I can't provide legal, salary, or general hiring strategy advice. "
                "Tell me about the role and skills you need to assess."
            )

        if intent == IntentType.GREETING:
            return ChatResponse(
                reply=(
                    "Hello! I'm your SHL assessment advisor. "
                    "Tell me the role, seniority, and skills you need to assess "
                    "(e.g., technical, cognitive, personality, or behavioral), "
                    "and I'll recommend assessments from the SHL Individual Test Solutions catalog."
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        if intent == IntentType.COMPARISON:
            return self._handle_comparison(user_msg, messages, state)

        should_clarify = self.clarification.should_clarify(state, intent)
        recommendations: List[AssessmentRecommendation] = []
        retrieved_context = ""
        retrieval_viz: list[dict] = []

        if not should_clarify and intent in {
            IntentType.DETAILED_REQUEST,
            IntentType.REFINEMENT,
            IntentType.EXPLANATION,
        }:
            results = self.recommendation_engine.retrieve_candidates(messages, state)
            retrieval_viz = self.recommendation_engine.retriever.get_scoring_visualization(
                self.recommendation_engine.query_builder.build(messages, state),
                state,
            )
            retrieved_context = self._format_retrieved(results)
            recommendations = self.recommendation_engine.build_recommendations(results)

            if intent == IntentType.REFINEMENT:
                prev = self._previous_recommendations(messages)
                if prev:
                    recommendations = self.recommendation_engine.refine(
                        prev, messages, state, intent
                    )
                    recommendations = self.grounding.validate_and_fix(recommendations)

        reply = self._generate_reply(
            messages=messages,
            state=state,
            intent=intent,
            retrieved_context=retrieved_context,
            recommendations=recommendations,
            should_clarify=should_clarify,
            retrieval_viz=retrieval_viz,
        )

        if should_clarify:
            recommendations = []
        elif recommendations:
            recommendations = self.grounding.validate_and_fix(recommendations)
            if not recommendations:
                results = self.recommendation_engine.retrieve_candidates(messages, state)
                recommendations = self.recommendation_engine.build_recommendations(results)

        end = intent == IntentType.FAREWELL or (
            bool(recommendations) and self._user_satisfied(user_msg)
        )

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "chat complete intent=%s recs=%s ms=%s",
            intent.value,
            len(recommendations),
            elapsed_ms,
            extra={
                "intent": intent.value,
                "recommendation_count": len(recommendations),
                "duration_ms": elapsed_ms,
            },
        )

        return ChatResponse(
            reply=reply,
            recommendations=recommendations,
            end_of_conversation=end,
        )

    def _generate_reply(
        self,
        messages: list,
        state,
        intent: IntentType,
        retrieved_context: str,
        recommendations: List[AssessmentRecommendation],
        should_clarify: bool,
        retrieval_viz: list[dict],
    ) -> str:
        if should_clarify:
            return self.clarification.build_clarification_question(state)

        state_summary = self.state_extractor.summarize(state)
        rec_block = json.dumps([r.model_dump() for r in recommendations], indent=2)
        viz_block = json.dumps(retrieval_viz[:5], indent=2) if retrieval_viz else "[]"

        system = SYSTEM_PROMPT.format(
            state_summary=state_summary,
            retrieved_context=retrieved_context or "No catalog matches.",
        )
        user_prompt = RESPONSE_GENERATION_PROMPT.format(
            intent=intent.value,
            recommendations=rec_block,
            retrieval_scores=viz_block,
            should_clarify=str(should_clarify).lower(),
        )

        llm_messages = [
            {"role": "system", "content": system},
            *[{"role": role_value(m.role), "content": m.content} for m in messages],
            {"role": "user", "content": user_prompt},
        ]

        raw = self.llm.chat(llm_messages, json_mode=True, max_tokens=900)
        try:
            data = self.llm.parse_json(raw)
            return str(data.get("reply", raw))
        except Exception:
            if recommendations:
                names = ", ".join(r.name for r in recommendations[:5])
                return (
                    f"Based on your requirements, I recommend: {names}. "
                    "See the structured recommendations for catalog links and test types."
                )
            return self.clarification.build_clarification_question(state)

    def _handle_comparison(self, user_msg: str, messages: list, state) -> ChatResponse:
        items = self.recommendation_engine.retrieve_for_comparison(user_msg)
        if len(items) < 2:
            names = [i.name for i in items]
            return ChatResponse(
                reply=(
                    f"I found limited catalog matches ({', '.join(names) or 'none'}). "
                    "Please name the two SHL assessments you'd like compared."
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        context = "\n\n---\n\n".join(i.to_text_chunk() for i in items[:4])
        prompt = COMPARISON_PROMPT.format(catalog_context=context, user_question=user_msg)
        raw = self.llm.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT.format(
                    state_summary=self.state_extractor.summarize(state),
                    retrieved_context=context,
                )},
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
            max_tokens=1000,
        )
        try:
            data = self.llm.parse_json(raw)
            reply = str(data.get("reply", raw))
        except Exception:
            reply = self._fallback_comparison(items[:2])

        return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)

    @staticmethod
    def _fallback_comparison(items: list) -> str:
        a, b = items[0], items[1]
        return (
            f"**{a.name}** ({a.test_type}): {a.description[:200]}\n\n"
            f"**{b.name}** ({b.test_type}): {b.description[:200]}\n\n"
            "Both are from the SHL Individual Test Solutions catalog. "
            f"Compare details at {a.url} and {b.url}."
        )

    @staticmethod
    def _refusal(message: str) -> ChatResponse:
        return ChatResponse(reply=message, recommendations=[], end_of_conversation=False)

    @staticmethod
    def _history_text(messages: list) -> str:
        return "\n".join(
            f"{role_value(m.role).capitalize()}: {m.content}" for m in messages[:-1]
        )

    @staticmethod
    def _format_retrieved(results: list) -> str:
        return "\n\n---\n\n".join(r.assessment.to_text_chunk() for r in results[:15])

    @staticmethod
    def _previous_recommendations(messages: list) -> List[AssessmentRecommendation]:
        for msg in reversed(messages):
            if role_value(msg.role) == "assistant" and "recommendations" in msg.content.lower():
                break
        return []

    @staticmethod
    def _user_satisfied(user_msg: str) -> bool:
        return bool(
            re.search(
                r"\b(thanks|thank you|that's all|perfect|goodbye|done)\b",
                user_msg.lower(),
            )
        )
