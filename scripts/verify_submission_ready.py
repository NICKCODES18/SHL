"""
Run before submitting your public API URL to SHL.
Exits 0 only if all evaluator-critical checks pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_files() -> list[str]:
    errors: list[str] = []
    catalog = ROOT / "data" / "catalog.json"
    tfidf = ROOT / "data" / "tfidf.joblib"
    if not catalog.exists():
        errors.append("Missing data/catalog.json — run: python -m app.scraper.catalog_scraper")
    elif catalog.stat().st_size < 10_000:
        errors.append("data/catalog.json too small — re-scrape catalog")
    else:
        count = len(json.loads(catalog.read_text(encoding="utf-8")))
        if count < 50:
            errors.append(f"Catalog only has {count} items (expected 100+)")
        else:
            print(f"OK catalog: {count} assessments")
    if not tfidf.exists():
        errors.append("Missing data/tfidf.joblib — run: python scripts/prebuild_tfidf.py")
    else:
        print(f"OK tfidf index: {tfidf.stat().st_size // 1024} KB")
    return errors


def check_live(base: str) -> list[str]:
    import requests

    errors: list[str] = []
    base = base.rstrip("/")
    print(f"\nChecking live URL: {base}")

    try:
        h = requests.get(f"{base}/health", timeout=120)
        if h.status_code != 200:
            errors.append(f"/health returned {h.status_code}")
        elif h.json().get("status") != "ok":
            errors.append(f"/health body invalid: {h.text[:100]}")
        else:
            print("OK GET /health")
    except Exception as exc:
        errors.append(f"/health unreachable: {exc}")
        return errors

    try:
        c = requests.post(
            f"{base}/chat",
            json={"messages": [{"role": "user", "content": "I need an assessment"}]},
            timeout=60,
        )
        if c.status_code != 200:
            errors.append(f"POST /chat returned {c.status_code}")
        else:
            body = c.json()
            if "reply" not in body or "recommendations" not in body:
                errors.append("POST /chat schema invalid")
            elif len(body["recommendations"]) != 0:
                errors.append("Vague query should return 0 recommendations")
            else:
                print("OK POST /chat (vague → clarify)")
    except Exception as exc:
        errors.append(f"POST /chat failed: {exc}")

    try:
        c = requests.post(
            f"{base}/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Mid-level Java developer. Need cognitive and Java technical tests."
                        ),
                    }
                ]
            },
            timeout=60,
        )
        body = c.json()
        recs = body.get("recommendations", [])
        if not (1 <= len(recs) <= 10):
            errors.append(f"Detailed query: expected 1-10 recs, got {len(recs)}")
        else:
            for rec in recs:
                if not rec.get("url", "").startswith("https://www.shl.com"):
                    errors.append(f"Invalid URL: {rec.get('url')}")
                    break
            else:
                print(f"OK POST /chat (detailed → {len(recs)} recommendations)")
    except Exception as exc:
        errors.append(f"POST /chat detailed failed: {exc}")

    return errors


def main() -> None:
    print("=== SHL submission readiness check ===\n")
    errors = check_files()
    if len(sys.argv) > 1:
        errors.extend(check_live(sys.argv[1]))

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("\nAll checks passed. Safe to submit your API URL.")
    if len(sys.argv) < 2:
        print("\nNext: deploy, then re-run with your live URL:")
        print("  python scripts/verify_submission_ready.py https://YOUR-APP.onrender.com")


if __name__ == "__main__":
    main()
