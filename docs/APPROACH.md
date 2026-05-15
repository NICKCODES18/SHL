# SHL Assessment Recommender — Approach Document (Draft)

## Problem framing

Hiring managers describe roles in natural language; keyword search assumes they already know SHL product names. We built a **stateless** FastAPI agent that clarifies efficiently (≤8 turns), recommends 1–10 **Individual Test Solutions** with catalog URLs, supports refinement and comparison, and refuses out-of-scope or adversarial requests.

## Architecture

**Retrieval-first recommendations.** The LLM generates conversational `reply` text only. Shortlists come from hybrid search over scraped catalog documents, then pass through a **GroundingValidator** that drops any name/URL not in `catalog.json`.

Pipeline: **IntentClassifier** → **StateExtractor** → **ClarificationPolicy** → **HybridRetriever** (dense Chroma + BM25, RRF k=60, weighted rerank, diversity cap per test type) → optional **LLM** for natural language.

## Retrieval setup

- **Corpus**: SHL product catalog, table “Individual Test Solutions” only (~200+ tests). Each document includes name, URL, description, duration, job levels, test type codes (K/C/P/B/…), and derived flags (cognitive, personality, technical).
- **Dense**: `all-MiniLM-L6-v2` in ChromaDB (cosine).
- **Sparse**: BM25 over tokenized text chunks.
- **Fusion**: Reciprocal Rank Fusion, then rule+feature reranking (role, seniority, skills, assessment-type needs).
- **Recall@10**: Retrieve top 40 per channel, rerank 25, diversify to 10 (max 4 per test type) to cover multiple relevant types in one shortlist.

## Prompt design

- System prompt: scope, anti-hallucination, injection resistance, compound clarification.
- Separate prompts for intent, state JSON, reply generation (references approved recommendation list), and comparison (catalog-only).
- JSON mode for structured auxiliary outputs; API response schema enforced by Pydantic.

## Agent behavior

| Behavior | Mechanism |
|----------|-----------|
| Clarify vague queries | `ready_to_recommend=false`; empty `recommendations`; compound question |
| Recommend | ≥2 signals (role/skills + seniority/type); retrieval shortlist |
| Refine | Re-retrieve; merge on “add/include” |
| Compare | Retrieve named tests; comparison prompt on chunks only |
| Refuse | Pattern + intent routing; empty recommendations |

## Evaluation

- **Hard**: Pydantic schema; URL prefix `https://www.shl.com`; probe harness in `app/evaluation/eval_harness.py`.
- **Recall@10**: `data/eval_traces.json` with `relevant` name lists per trace.
- **Probes**: vague turn-1, detailed recommend, jailbreak, salary refusal, refinement.

## What didn’t work / iterations

- **Mock 4-item catalog**: insufficient for Recall@10; replaced with full scraper.
- **LLM-only recommendations**: caused hallucinated URLs; moved to retrieval + validator.
- **Sequential clarification**: wasted turns; replaced with compound questions and rule-based readiness.
- **Job Solutions in index**: out of scope; filtered at scrape time (second catalog table).

## AI tools used

Cursor/agent assisted with boilerplate, scraper exploration (pagination via `start` param), and test scaffolding. Design decisions (retrieval-first, RRF, grounding) were validated against assignment eval criteria.

## Stack justification

| Choice | Why |
|--------|-----|
| FastAPI + Pydantic | Strict schema for automated grader |
| Chroma + sentence-transformers | Simple persistent vectors, Render-friendly |
| BM25 | Exact match on product names (Java, OPQ, Verify) |
| OpenRouter | Required model swap via env |
| No LangGraph | Lighter orchestration, deterministic recommend path |
