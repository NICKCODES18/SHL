"""Extract embedded catalog data from SHL page."""
import json
import re
import requests

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
url = f"{BASE}/solutions/products/product-catalog/"
r = requests.get(url, headers=HEADERS, timeout=60)
html = r.text

# Find JSON arrays in scripts
arrays = re.findall(r'\[\s*\{[^\]]{50,5000}\}\s*\]', html)
print("json array candidates", len(arrays))
for i, a in enumerate(arrays[:5]):
    print(i, len(a), a[:150])

# product-catalog/view all occurrences
views = re.findall(r'/products/product-catalog/view/[a-z0-9\-]+/', html)
print("views in html", len(views), "unique", len(set(views)))

# Search for slug list
for pat in [
    r'"slug"\s*:\s*"([^"]+)"',
    r'"name"\s*:\s*"([^"]{3,80})"',
    r'product-catalog/view/([a-z0-9\-]+)',
]:
    matches = re.findall(pat, html)
    if matches:
        print(pat[:40], "count", len(matches), "sample", matches[:5])

# Look for angular/react state
for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S):
    content = m.group(1).strip()
    if len(content) > 100:
        print("JSON script", len(content), content[:200])

# Fetch with different query params for individual tests
for qs in [
    "?solutionType=individual",
    "?type=individual-test",
    "?filter=individual",
    "?productType=K",
]:
    u = url.rstrip("/") + qs
    rr = requests.get(u, headers=HEADERS, timeout=30)
    v = set(re.findall(r'/products/product-catalog/view/[a-z0-9\-]+/', rr.text))
    print(qs, "unique views", len(v))
