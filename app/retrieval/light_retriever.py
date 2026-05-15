"""
Serverless-friendly hybrid retrieval: BM25 + pre-built TF-IDF (no Chroma/torch).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.models.schemas import AssessmentMetadata, ConversationState, RetrievalResult
from app.retrieval.reranker import WeightedReranker

logger = logging.getLogger(__name__)


class LightHybridRetriever:
    """BM25 + TF-IDF with RRF — designed for Vercel serverless."""

    def __init__(self, data_path: str | None = None) -> None:
        self.data_path = data_path or settings.CATALOG_PATH
        self.reranker = WeightedReranker()
        self.assessments: Dict[str, AssessmentMetadata] = {}
        self.doc_ids: List[str] = []
        self.bm25: BM25Okapi | None = None
        self._vectorizer = None
        self._matrix = None
        self._load()

    def _load(self) -> None:
        path = Path(self.data_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Catalog not found at {path}. Commit data/catalog.json before deploying."
            )

        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)

        corpus: list[list[str]] = []
        for item in raw:
            meta = AssessmentMetadata(**item)
            self.assessments[meta.name] = meta
            self.doc_ids.append(meta.name)
            corpus.append(meta.to_text_chunk().lower().split())

        tfidf_path = Path(settings.TFIDF_INDEX_PATH)
        if tfidf_path.exists():
            data = joblib.load(tfidf_path)
            self._vectorizer = data["vectorizer"]
            self._matrix = data["matrix"]
            if data.get("doc_ids"):
                self.doc_ids = data["doc_ids"]
        else:
            logger.warning("TF-IDF index missing — run scripts/prebuild_tfidf.py")

        bm25_path = Path(settings.BM25_INDEX_PATH)
        if bm25_path.exists():
            with bm25_path.open(encoding="utf-8") as handle:
                saved = json.load(handle)
            self.bm25 = BM25Okapi(saved["corpus"])
            self.doc_ids = saved.get("doc_ids", self.doc_ids)
        else:
            self.bm25 = BM25Okapi(corpus)

        logger.info("Light retriever loaded %s assessments", len(self.assessments))

    def dense_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        if self._vectorizer is None or self._matrix is None:
            return self.sparse_search(query, top_k)

        q_vec = self._vectorizer.transform([query])
        scores = (self._matrix @ q_vec.T).toarray().flatten()
        indices = np.argsort(scores)[::-1][:top_k]
        return [
            (self.doc_ids[idx], float(scores[idx]))
            for idx in indices
            if scores[idx] > 0 and idx < len(self.doc_ids)
        ]

    def sparse_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        if not self.bm25:
            return []
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        indices = np.argsort(scores)[::-1][:top_k]
        return [
            (self.doc_ids[idx], float(scores[idx]))
            for idx in indices
            if scores[idx] > 0
        ]

    def rrf(
        self,
        dense: List[Tuple[str, float]],
        sparse: List[Tuple[str, float]],
        k: int | None = None,
    ) -> List[RetrievalResult]:
        k = k or settings.RRF_K
        fused: dict[str, dict] = {}

        for rank, (name, _) in enumerate(dense):
            fused.setdefault(name, {"dense_rank": None, "sparse_rank": None, "score": 0.0})
            fused[name]["dense_rank"] = rank + 1
            fused[name]["score"] += 1.0 / (k + rank + 1)

        for rank, (name, _) in enumerate(sparse):
            fused.setdefault(name, {"dense_rank": None, "sparse_rank": None, "score": 0.0})
            fused[name]["sparse_rank"] = rank + 1
            fused[name]["score"] += 1.0 / (k + rank + 1)

        sorted_items = sorted(fused.items(), key=lambda x: x[1]["score"], reverse=True)
        results: List[RetrievalResult] = []
        for name, data in sorted_items:
            if name not in self.assessments:
                continue
            results.append(
                RetrievalResult(
                    assessment=self.assessments[name],
                    dense_rank=data["dense_rank"],
                    sparse_rank=data["sparse_rank"],
                    rrf_score=data["score"],
                )
            )
        return results

    def search(
        self,
        query: str,
        state: ConversationState,
        top_k: int | None = None,
    ) -> List[RetrievalResult]:
        final_k = top_k or settings.FINAL_TOP_K
        dense = self.dense_search(query, settings.DENSE_TOP_K)
        sparse = self.sparse_search(query, settings.SPARSE_TOP_K)
        fused = self.rrf(dense, sparse)
        filtered = self._apply_constraints(fused, state)
        reranked = self.reranker.rerank(filtered, state, query)
        return self.reranker.diversify(reranked, limit=final_k)

    def _apply_constraints(
        self, results: List[RetrievalResult], state: ConversationState
    ) -> List[RetrievalResult]:
        needs = [
            (state.needs_coding or state.needs_technical, lambda m: m.technical),
            (state.needs_cognitive, lambda m: m.cognitive or "cognitive" in m.test_type.lower()),
            (state.needs_personality, lambda m: m.personality),
            (
                state.needs_behavioral,
                lambda m: m.behavioral or m.situational_judgment,
            ),
        ]
        active = [check for flag, check in needs if flag]
        if not active:
            return results
        if len(active) == 1:
            filtered = [r for r in results if active[0](r.assessment)]
            return filtered if filtered else results
        filtered = [r for r in results if any(check(r.assessment) for check in active)]
        return filtered if len(filtered) >= 3 else results

    def get_scoring_visualization(
        self, query: str, state: ConversationState
    ) -> list[dict]:
        dense = self.dense_search(query, 10)
        sparse = self.sparse_search(query, 10)
        fused = self.rrf(dense, sparse)[:10]
        return [
            {
                "name": r.assessment.name,
                "rrf_score": round(r.rrf_score, 4),
                "dense_rank": r.dense_rank,
                "sparse_rank": r.sparse_rank,
                "final_score": round(r.score, 4),
            }
            for r in self.reranker.rerank(fused, state, query)[:10]
        ]
