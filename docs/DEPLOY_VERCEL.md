# Deploy to Vercel

## Prerequisites

1. [Vercel account](https://vercel.com)
2. [Vercel CLI](https://vercel.com/docs/cli): `npm i -g vercel`
3. `data/catalog.json` committed (191 Individual Test Solutions)
4. Run locally once: `python scripts/prebuild_tfidf.py` (creates `data/tfidf.joblib`)

## Deploy

```bash
cd e:\SHL
vercel login
vercel --prod
```

## Environment variables (Vercel Dashboard → Project → Settings → Environment Variables)

| Name | Required | Example |
|------|----------|---------|
| `OPENROUTER_API_KEY` | Yes | `sk-or-v1-...` |
| `DEFAULT_LLM_MODEL` | No | `mistralai/mistral-small-3.1-24b-instruct` |
| `VERCEL` | Auto | Set by `vercel.json` |

Apply to **Production**, **Preview**, and **Development**.

## Verify live API

Replace `YOUR_URL` with `https://your-project.vercel.app`:

```bash
curl https://YOUR_URL/health
curl https://YOUR_URL/
curl -X POST https://YOUR_URL/chat \
  -H "Content-Type: application/json" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Mid-level Java developer. Need cognitive and Java tests.\"}]}"
```

Or run: `python scripts/smoke_test_live.py https://YOUR_URL`

## Submission

Submit the production URL, e.g. `https://your-project.vercel.app` (evaluator will call `/health` and `/chat`).

## Notes

- Vercel uses **TF-IDF + BM25** (no Chroma/torch) to fit serverless limits.
- First request after idle may take 10–30s (cold start).
- Hobby plan: 10s timeout on some routes; Pro allows 60s (`maxDuration` in `vercel.json`).
