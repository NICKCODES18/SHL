"""
Anti-hallucination grounding checks for recommendations.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from app.core.config import settings
from app.models.schemas import AssessmentMetadata, AssessmentRecommendation

logger = logging.getLogger(__name__)


class GroundingValidator:
    """Ensures all recommendations exist in the scraped catalog."""

    def __init__(self, catalog: Dict[str, AssessmentMetadata]) -> None:
        self.by_name = catalog
        self.by_url = {a.url.rstrip("/"): a for a in catalog.values()}
        self.allowed_prefix = settings.ALLOWED_URL_PREFIX

    def validate_and_fix(
        self,
        recommendations: List[AssessmentRecommendation],
    ) -> List[AssessmentRecommendation]:
        validated: List[AssessmentRecommendation] = []
        for rec in recommendations:
            fixed = self._match_catalog(rec)
            if fixed and fixed.url.startswith(self.allowed_prefix):
                validated.append(fixed)
            else:
                logger.warning("Dropped ungrounded recommendation: %s", rec.name)
        return validated

    def from_metadata(
        self,
        items: List[AssessmentMetadata],
        limit: int = 10,
    ) -> List[AssessmentRecommendation]:
        results: List[AssessmentRecommendation] = []
        seen: set[str] = set()
        for meta in items:
            if meta.name in seen:
                continue
            seen.add(meta.name)
            results.append(
                AssessmentRecommendation(
                    name=meta.name,
                    url=meta.url,
                    test_type=meta.test_type or "General",
                )
            )
            if len(results) >= limit:
                break
        return results

    def _match_catalog(
        self, rec: AssessmentRecommendation
    ) -> AssessmentRecommendation | None:
        url_key = rec.url.rstrip("/")
        if url_key in self.by_url:
            meta = self.by_url[url_key]
            return AssessmentRecommendation(
                name=meta.name, url=meta.url, test_type=meta.test_type
            )

        if rec.name in self.by_name:
            meta = self.by_name[rec.name]
            return AssessmentRecommendation(
                name=meta.name, url=meta.url, test_type=meta.test_type
            )

        lowered = rec.name.lower()
        for name, meta in self.by_name.items():
            if lowered in name.lower() or name.lower() in lowered:
                return AssessmentRecommendation(
                    name=meta.name, url=meta.url, test_type=meta.test_type
                )
        return None
