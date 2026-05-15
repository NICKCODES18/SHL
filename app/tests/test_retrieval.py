"""Retrieval pipeline tests (no LLM)."""

from app.models.schemas import ConversationState
from app.retrieval.retriever import HybridRetriever


def test_retriever_loads_catalog() -> None:
    retriever = HybridRetriever()
    assert len(retriever.assessments) >= 1


def test_hybrid_search_returns_results() -> None:
    retriever = HybridRetriever()
    state = ConversationState(needs_cognitive=True, role="Software Engineer")
    results = retriever.search("cognitive reasoning software engineer", state, top_k=5)
    assert len(results) >= 1
    assert all(r.assessment.url.startswith("https://www.shl.com") for r in results)


def test_rrf_fusion() -> None:
    retriever = HybridRetriever()
    dense = retriever.dense_search("java programming", 5)
    sparse = retriever.sparse_search("java programming", 5)
    fused = retriever.rrf(dense, sparse)
    assert len(fused) >= 1
