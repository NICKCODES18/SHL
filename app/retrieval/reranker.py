"""
Weighted reranking layer on top of hybrid retrieval (RRF) results.
"""

from __future__ import annotations

import re
from typing import List

from app.models.schemas import ConversationState, RetrievalResult


class WeightedReranker:
    """
    Reranks candidates using role, seniority, skill, and assessment-type alignment.
    Ordering priority: technical > cognitive > personality > leadership/communication.
    """

    def rerank(
        self,
        results: List[RetrievalResult],
        state: ConversationState,
        query: str,
    ) -> List[RetrievalResult]:
        query_tokens = set(re.findall(r"[a-z0-9\+.#]{2,}", query.lower()))

        scored: list[tuple[float, RetrievalResult]] = []
        for result in results:
            meta = result.assessment
            score = result.rrf_score * 10.0

            blob = (
                f"{meta.name} {meta.description} "
                f"{' '.join(meta.keywords)} {' '.join(meta.synonyms)} "
                f"{' '.join(meta.skills_measured)}"
            ).lower()

            for token in query_tokens:
                if token in blob:
                    score += 1.5

            if state.role and state.role.lower() in blob:
                score += 3.0
            if state.seniority:
                for level in meta.job_levels:
                    if state.seniority.lower() in level.lower():
                        score += 2.0
            for skill in state.skills:
                if skill.lower() in blob:
                    score += 2.5

            if state.needs_coding and meta.technical:
                score += 5.0
            if state.needs_technical and meta.technical:
                score += 4.0
            if state.needs_cognitive and meta.cognitive:
                score += 4.0
            if state.needs_personality and meta.personality:
                score += 3.5
            if state.needs_behavioral and (meta.behavioral or meta.situational_judgment):
                score += 3.0
            if state.needs_leadership and any(
                k in blob for k in ("leadership", "communication", "stakeholder", "team")
            ):
                score += 2.5
            if state.remote_required and meta.remote_testing:
                score += 1.0

            # Type priority tie-breaker
            if meta.technical:
                score += 0.4
            if meta.cognitive:
                score += 0.3
            if meta.personality:
                score += 0.2

            result.score = score
            scored.append((score, result))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]

    def diversify(
        self,
        results: List[RetrievalResult],
        limit: int = 10,
    ) -> List[RetrievalResult]:
        """Ensure diversity across assessment types for Recall@10."""
        selected: List[RetrievalResult] = []
        type_counts: dict[str, int] = {}

        for result in results:
            test_type = result.assessment.test_type or "General"
            if type_counts.get(test_type, 0) >= 4 and len(selected) < limit - 3:
                continue
            selected.append(result)
            type_counts[test_type] = type_counts.get(test_type, 0) + 1
            if len(selected) >= limit:
                break

        if len(selected) < limit:
            for result in results:
                if result not in selected:
                    selected.append(result)
                if len(selected) >= limit:
                    break
        return selected[:limit]
