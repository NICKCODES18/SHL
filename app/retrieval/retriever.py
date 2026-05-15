"""
Hybrid retrieval: dense (ChromaDB) + sparse (BM25) with RRF fusion and reranking.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.models.schemas import AssessmentMetadata, ConversationState, RetrievalResult
from app.retrieval.reranker import WeightedReranker
from app.scraper.catalog_scraper import CatalogScraper

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid dense + sparse retriever with RRF and weighted reranking."""

    def __init__(self, data_path: str | None = None) -> None:
        self.data_path = data_path or settings.CATALOG_PATH
        self.reranker = WeightedReranker()
        self.assessments: Dict[str, AssessmentMetadata] = {}
        self.doc_ids: List[str] = []
        self.bm25: BM25Okapi | None = None

        os.makedirs(Path(settings.CHROMA_PERSIST_DIRECTORY).parent, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="shl_individual_tests",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        self._load_catalog()

    def _load_catalog(self) -> None:
        path = Path(self.data_path)
        if not path.exists() or path.stat().st_size < 500:
            logger.info("Catalog missing or small — running scraper...")
            scraper = CatalogScraper()
            assessments = scraper.scrape_catalog()
            scraper.save_to_json(assessments, str(path))

        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)

        docs: list[str] = []
        metadatas: list[dict] = []
        ids: list[str] = []
        corpus: list[list[str]] = []

        for item in raw:
            meta = AssessmentMetadata(**item)
            self.assessments[meta.name] = meta
            chunk = meta.to_text_chunk()
            docs.append(chunk)
            metadatas.append({"name": meta.name, "test_type": meta.test_type})
            ids.append(self._doc_id(meta.name))
            corpus.append(chunk.lower().split())
            self.doc_ids.append(meta.name)

        self.bm25 = BM25Okapi(corpus)
        self._persist_bm25(corpus)

        if self.collection.count() == 0 and docs:
            logger.info("Indexing %s documents in ChromaDB...", len(docs))
            batch = 100
            for i in range(0, len(docs), batch):
                self.collection.add(
                    documents=docs[i : i + batch],
                    metadatas=metadatas[i : i + batch],
                    ids=ids[i : i + batch],
                )

    def _persist_bm25(self, corpus: list[list[str]]) -> None:
        path = Path(settings.BM25_INDEX_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump({"doc_ids": self.doc_ids, "corpus": corpus}, handle)

    @staticmethod
    def _doc_id(name: str) -> str:
        return name.replace("/", "_").replace(" ", "_")[:200]

    def dense_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        if self.collection.count() == 0:
            return []
        results = self.collection.query(query_texts=[query], n_results=min(top_k, self.collection.count()))
        if not results["ids"] or not results["ids"][0]:
            return []
        pairs: List[Tuple[str, float]] = []
        metas = results.get("metadatas", [[]])[0]
        for doc_id, distance, meta in zip(
            results["ids"][0], results["distances"][0], metas
        ):
            name = meta.get("name") if meta else None
            if not name:
                name = self._name_from_doc_id(doc_id)
            score = 1.0 / (1.0 + float(distance))
            pairs.append((name, score))
        return pairs

    def _name_from_doc_id(self, doc_id: str) -> str:
        for name in self.assessments:
            if self._doc_id(name) == doc_id:
                return name
        return doc_id.replace("_", " ")

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
        diversified = self.reranker.diversify(reranked, limit=final_k)
        return diversified

    def _apply_constraints(
        self, results: List[RetrievalResult], state: ConversationState
    ) -> List[RetrievalResult]:
        """Soft filter: when multiple assessment types requested, keep items matching ANY."""
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
        """Bonus: hybrid retrieval scoring breakdown for debugging."""
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
