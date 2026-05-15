# Submission checklist — keep your API URL accessible

SHL runs **automated tests** against your public URL. An inaccessible or timing-out endpoint can disqualify your submission.

## Recommended platform: **Render** (not Vercel Hobby)

| Platform | Issue for evaluators |
|----------|----------------------|
| **Vercel Hobby** | 10s function timeout — may fail 30s `/chat` tests |
| **Vercel Pro** | 60s timeout — OK if you enable Pro |
| **Render (Docker)** | Always-on web service, 30s+ requests — **best fit** |

## Deploy to Render (recommended)

1. Push this repo to GitHub (include `data/catalog.json` and `data/tfidf.joblib`).
2. [Render Dashboard](https://dashboard.render.com) → **New** → **Web Service** → connect repo.
3. **Runtime**: Docker (uses root `Dockerfile`).
4. **Environment variables**:
   - `OPENROUTER_API_KEY` = your key
   - `DEFAULT_LLM_MODEL` = `mistralai/mistral-small-3.1-24b-instruct`
5. Deploy. Copy URL: `https://shl-assessment-recommender-xxxx.onrender.com`

Free tier may sleep after inactivity; **first request wakes the service** (evaluators allow up to **2 minutes** for `/health` cold start).

## Verify before you submit

```bash
# Local artifacts
python scripts/verify_submission_ready.py

# Live URL (required before submitting)
python scripts/verify_submission_ready.py https://YOUR-APP.onrender.com
python scripts/smoke_test_live.py https://YOUR-APP.onrender.com
```

Submit **only** if both pass:

- `GET https://YOUR-URL/health` → `{"status":"ok"}`
- `POST https://YOUR-URL/chat` → valid schema every time

## What to submit

| Field | Example |
|-------|---------|
| Public API URL | `https://shl-assessment-recommender.onrender.com` |
| Health | `https://YOUR-URL/health` |
| Chat | `https://YOUR-URL/chat` |

Do **not** submit `localhost` or a Vercel preview URL that expires.

## Keep it online until evaluation ends

- Do not delete the Render/Vercel project.
- Do not let free-tier credits expire without migration.
- Re-run `verify_submission_ready.py` the day you submit.

## Vercel (optional)

Only if you have **Pro** (60s timeout) or accept cold-start risk:

```bash
vercel login
vercel --prod
```

Set `OPENROUTER_API_KEY` in Vercel → Settings → Environment Variables → **Redeploy**.
