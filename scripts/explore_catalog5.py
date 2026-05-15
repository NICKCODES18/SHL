"""Find SHL catalog backend endpoints in page JS."""
import re
import requests

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
url = f"{BASE}/solutions/products/product-catalog/"
r = requests.get(url, headers=HEADERS, timeout=60)
html = r.text

# URLs in page
urls = set(re.findall(r'["\'](/[a-zA-Z0-9_\-/\.]+)["\']', html))
interesting = [u for u in urls if any(k in u.lower() for k in ["catalog", "product", "api", "search", "filter", "assessment"])]
for u in sorted(interesting):
    print(u)

# external API
ext = set(re.findall(r'https?://[a-zA-Z0-9\.\-/]+(?:catalog|product|api)[a-zA-Z0-9\.\-/]*', html))
for e in sorted(ext)[:30]:
    print("EXT", e)

# Try SHL search endpoint patterns
endpoints = [
    "/umbraco/api/productcatalog/search",
    "/api/v1/products",
    "/api/productcatalog",
    "/product-catalog/api",
    "/solutions/products/product-catalog/search",
]
for ep in endpoints:
    for method_url in [BASE + ep, BASE + ep + "?pageSize=500"]:
        try:
            rr = requests.get(method_url, headers=HEADERS, timeout=15)
            if rr.status_code != 404:
                print(method_url, rr.status_code, rr.headers.get("content-type","")[:40], len(rr.text))
                print(rr.text[:300])
        except Exception as ex:
            print(method_url, ex)

# Download a JS bundle and search
scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
print("script count", len(scripts))
for src in scripts:
    if "catalog" in src.lower() or "product" in src.lower() or "main" in src.lower():
        print("JS", src[:100])
