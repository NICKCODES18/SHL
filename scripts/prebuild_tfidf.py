"""
Pre-build TF-IDF index for Vercel/serverless (no sentence-transformers at runtime).
Run during Vercel build: python scripts/prebuild_tfidf.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.models.schemas import AssessmentMetadata  # noqa: E402

CATALOG = ROOT / "data" / "catalog.json"
OUT = ROOT / "data" / "tfidf.joblib"
BM25_OUT = ROOT / "data" / "bm25_corpus.json"


def main() -> None:
    if not CATALOG.exists():
        print("ERROR: data/catalog.json missing. Run: python -m app.scraper.catalog_scraper")
        sys.exit(1)

    with CATALOG.open(encoding="utf-8") as f:
        raw = json.load(f)

    doc_ids: list[str] = []
    docs: list[str] = []
    corpus: list[list[str]] = []

    for item in raw:
        meta = AssessmentMetadata(**item)
        chunk = meta.to_text_chunk()
        doc_ids.append(meta.name)
        docs.append(chunk)
        corpus.append(chunk.lower().split())

    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), sublinear_tf=True)
    matrix = vectorizer.fit_transform(docs)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "doc_ids": doc_ids}, OUT)

    with BM25_OUT.open("w", encoding="utf-8") as f:
        json.dump({"doc_ids": doc_ids, "corpus": corpus}, f)

    print(f"Wrote TF-IDF index ({matrix.shape}) -> {OUT}")
    print(f"Wrote BM25 corpus ({len(doc_ids)} docs) -> {BM25_OUT}")


if __name__ == "__main__":
    main()
