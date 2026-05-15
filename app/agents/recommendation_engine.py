"""
Deterministic recommendation engine grounded in retrieval results.
"""

from __future__ import annotations

import logging
from typing import List

from app.agents.grounding import GroundingValidator
from app.core.config import settings
from app.models.schemas import (
    AssessmentMetadata,
    AssessmentRecommendation,
    ConversationState,
    IntentType,
    RetrievalResult,
)
from app.retrieval.query_builder import QueryBuilder
from app.retrieval.factory import get_retriever

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Produces catalog-grounded shortlists via hybrid retrieval."""

    def __init__(self, retriever=None) -> None:
        self.retriever = retriever or get_retriever()
        self.query_builder = QueryBuilder()
        self.grounding = GroundingValidator(self.retriever.assessments)

    def retrieve_candidates(
        self,
        messages: list,
        state: ConversationState,
        top_k: int | None = None,
    ) -> List[RetrievalResult]:
        query = self.query_builder.build(messages, state)
        k = top_k or settings.RERANK_TOP_K
        results = self.retriever.search(query, state, top_k=max(k, settings.FINAL_TOP_K))
        confidence = self._confidence(results)
        logger.info(
            "Retrieval: query_len=%s results=%s confidence=%.3f",
            len(query),
            len(results),
            confidence,
        )
        return results

    def build_recommendations(
        self,
        results: List[RetrievalResult],
        limit: int | None = None,
    ) -> List[AssessmentRecommendation]:
        limit = limit or settings.MAX_RECOMMENDATION_COUNT
        metas = [r.assessment for r in results]
        recs = self.grounding.from_metadata(metas, limit=limit)
        target = min(limit, settings.MAX_RECOMMENDATION_COUNT)
        if len(recs) < settings.MIN_RECOMMENDATION_COUNT and len(metas) > len(recs):
            return self.grounding.from_metadata(metas, limit=target)
        return recs[:target]

    def retrieve_for_comparison(
        self, user_message: str
    ) -> List[AssessmentMetadata]:
        query = self.query_builder.build_comparison_query(user_message)
        results = self.retriever.search(
            query,
            ConversationState(ready_to_recommend=True),
            top_k=5,
        )
        return [r.assessment for r in results]

    def refine(
        self,
        previous: List[AssessmentRecommendation],
        messages: list,
        state: ConversationState,
        intent: IntentType,
    ) -> List[AssessmentRecommendation]:
        fresh = self.retrieve_candidates(messages, state)
        fresh_recs = self.build_recommendations(fresh)

        if intent != IntentType.REFINEMENT:
            return fresh_recs

        merged: list[AssessmentRecommendation] = []
        seen: set[str] = set()

        latest = messages[-1].content.lower() if messages else ""
        additive = any(
            k in latest for k in ("add", "also", "include", "plus", "as well")
        )

        if additive:
            for rec in previous + fresh_recs:
                if rec.name not in seen:
                    merged.append(rec)
                    seen.add(rec.name)
        else:
            for rec in fresh_recs:
                if rec.name not in seen:
                    merged.append(rec)
                    seen.add(rec.name)

        return merged[: settings.MAX_RECOMMENDATION_COUNT]

    @staticmethod
    def _confidence(results: List[RetrievalResult]) -> float:
        if not results:
            return 0.0
        top = results[0].score
        if len(results) == 1:
            return min(1.0, top / 20.0)
        second = results[1].score
        gap = max(0.0, top - second)
        return min(1.0, (top + gap) / 25.0)
