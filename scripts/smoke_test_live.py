"""Smoke-test a live deployment URL."""

from __future__ import annotations

import json
import sys

import requests

TIMEOUT = 55


def main() -> None:
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"Testing {base}\n")

    r = requests.get(f"{base}/health", timeout=TIMEOUT)
    print("GET /health", r.status_code, r.json())
    assert r.status_code == 200 and r.json().get("status") == "ok"

    r = requests.get(f"{base}/", timeout=TIMEOUT)
    print("GET /", r.status_code, json.dumps(r.json(), indent=2)[:400])

    vague = requests.post(
        f"{base}/chat",
        json={"messages": [{"role": "user", "content": "I need an assessment"}]},
        timeout=TIMEOUT,
    )
    v = vague.json()
    print("\nPOST /chat (vague)", vague.status_code)
    print("  recs:", len(v.get("recommendations", [])))
    print("  reply:", v.get("reply", "")[:120])
    assert vague.status_code == 200
    assert "reply" in v and "recommendations" in v
    assert len(v["recommendations"]) == 0

    detailed = requests.post(
        f"{base}/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Mid-level Java developer. Need cognitive reasoning "
                        "and Java technical tests."
                    ),
                }
            ]
        },
        timeout=TIMEOUT,
    )
    d = detailed.json()
    print("\nPOST /chat (detailed)", detailed.status_code)
    print("  recs:", len(d.get("recommendations", [])))
    for rec in d.get("recommendations", [])[:3]:
        print("   -", rec.get("name"), rec.get("url", "")[:50])
    assert detailed.status_code == 200
    assert 1 <= len(d.get("recommendations", [])) <= 10
    for rec in d["recommendations"]:
        assert rec["url"].startswith("https://www.shl.com")

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
