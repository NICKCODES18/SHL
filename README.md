# SHL AI Conversational Assessment Recommender

Production-grade FastAPI agent that recommends **SHL Individual Test Solutions** only, via stateless multi-turn dialogue with hybrid retrieval and strict schema compliance.

## Architecture

```
Client → POST /chat (full message history)
           ↓
       OrchestratorAgent
           ├── IntentClassifier (rules + LLM)
           ├── StateExtractor (rules + LLM)
           ├── ClarificationPolicy (≤8 turns)
           ├── RecommendationEngine
           │      └── HybridRetriever (Chroma + BM25 + RRF + rerank)
           ├── GroundingValidator (catalog-only URLs)
           └── LLMClient (OpenRouter) → reply text only
```

**Key design choices**

| Concern | Approach |
|--------|----------|
| Hallucination | Recommendations from retrieval + catalog validator, not LLM |
| Recall@10 | Broad dense/sparse retrieval (k=40), RRF, weighted rerank, diversity |
| Turn budget | Compound clarification questions; rule-based readiness |
| Security | Jailbreak/out-of-scope patterns + prompt constraints |
| Stateless | No server memory; full `messages[]` per request |

## Project structure

```
app/
  api/           # /health, /chat
  agents/        # orchestrator, intent, state, grounding, LLM
  retrieval/     # hybrid search, reranker, query builder
  scraper/       # SHL catalog scraper (Individual Test Solutions)
  models/        # Pydantic schemas
  prompts/       # system & task prompts
  evaluation/    # behavior probes + Recall@10
  tests/         # pytest suite
  core/          # config, logging
data/
  catalog.json   # scraped catalog
  chroma_db/     # vector index (generated)
scripts/         # build catalog, startup
```

## Quick start (local)

```powershell
cd e:\SHL
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Build catalog (first run, ~3–5 min)
python -m app.scraper.catalog_scraper

# Set API key
copy .env.example .env
# Edit .env → OPENROUTER_API_KEY=...

uvicorn app.main:app --reload --port 8000
```

Or: `.\scripts\start.ps1`

## API

### `GET /health`

```json
{"status": "ok"}
```

### `POST /chat`

**Request**

```json
{
  "messages": [
    {"role": "user", "content": "Hiring a Java developer who works with stakeholders"},
    {"role": "assistant", "content": "What role, seniority, and assessment types do you need?"},
    {"role": "user", "content": "Mid-level, around 4 years. Cognitive and Java technical."}
  ]
}
```

**Response**

```json
{
  "reply": "...",
  "recommendations": [
    {"name": "...", "url": "https://www.shl.com/...", "test_type": "K"}
  ],
  "end_of_conversation": false
}
```

- `recommendations`: `[]` while clarifying or refusing; **1–10** when recommending
- All URLs must be `https://www.shl.com/...` from scraped catalog

### Sample curl

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"I need an assessment"}]}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Mid-level Java developer. Need cognitive reasoning and Java coding tests."}]}'
```

## Evaluation

```bash
python -m app.evaluation.eval_harness
pytest app/tests -q
```

Probes: schema, vague→clarify, detailed→recommend, URL grounding, out-of-scope, jailbreak, refinement.

Place labeled traces in `data/eval_traces.json` for Recall@10.

## Deploy on Vercel (submission)

```bash
# One-time
npm i -g vercel
vercel login
python scripts/prebuild_tfidf.py   # creates data/tfidf.joblib

# Deploy
vercel --prod
```

**Vercel env vars** (Project → Settings → Environment Variables):

- `OPENROUTER_API_KEY` (required)
- `DEFAULT_LLM_MODEL` (optional)

After deploy, verify:

```bash
python scripts/smoke_test_live.py https://YOUR-PROJECT.vercel.app
```

See [docs/DEPLOY_VERCEL.md](docs/DEPLOY_VERCEL.md). Root `GET /` shows `catalog_size: 191` and `mode: serverless` when live.

## Deploy on Render

1. New **Web Service** → connect repo
2. **Environment**: Docker (or Python 3.11)
3. **Build**: `pip install -r requirements.txt && python -m app.scraper.catalog_scraper`
4. **Start**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set `OPENROUTER_API_KEY`, `DEFAULT_LLM_MODEL`
6. Health check path: `/health` (allow up to 120s cold start for embedding model)

`Dockerfile` pre-caches `all-MiniLM-L6-v2` for faster cold starts.

## Catalog ingestion

`app/scraper/catalog_scraper.py`:

1. Paginates [SHL product catalog](https://www.shl.com/solutions/products/product-catalog/)
2. Reads **Individual Test Solutions** table only (excludes Job Solutions)
3. Scrapes each product page for description, duration, job levels, test types
4. Writes `data/catalog.json` and indexes Chroma + BM25

Rebuild: `python -m app.scraper.catalog_scraper`

## Configuration

| Variable | Default |
|----------|---------|
| `OPENROUTER_API_KEY` | (required for LLM replies) |
| `DEFAULT_LLM_MODEL` | `mistralai/mistral-small-3.1-24b-instruct` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` |
| `PORT` | `8000` |

## Approach document

See [docs/APPROACH.md](docs/APPROACH.md) (2-page draft for submission).
