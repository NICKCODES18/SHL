"""Explore SHL catalog API / pagination."""
import json
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

# Try common API patterns
candidates = [
    f"{BASE}/api/product-catalog",
    f"{BASE}/wp-json/wp/v2/products",
    f"{BASE}/solutions/products/product-catalog/?format=json",
]
for c in candidates:
    try:
        r = requests.get(c, headers=HEADERS, timeout=15)
        print(c, r.status_code, r.headers.get("content-type", "")[:50], len(r.text))
    except Exception as e:
        print(c, "ERR", e)

# Parse detail page properly
url = f"{BASE}/products/product-catalog/view/net-mvc-new/"
r = requests.get(url, headers=HEADERS, timeout=60)
soup = BeautifulSoup(r.text, "html.parser")

# Print structured content
for h in soup.find_all(["h1", "h2", "h3"])[:10]:
    print("H:", h.name, h.get_text(strip=True)[:80])

# tables / dl
for dl in soup.find_all("dl")[:3]:
    print("DL:", dl.get_text(" | ", strip=True)[:200])

for row in soup.select(".product-detail, .catalog-detail, [class*='spec']")[:5]:
    print("ROW:", row.get("class"), row.get_text(strip=True)[:150])

# all text with Test Type
text = soup.get_text("\n", strip=True)
for line in text.split("\n"):
    if any(k in line for k in ["Test Type", "Duration", "Remote", "Adaptive", "Job Level", "Language"]):
        print("LINE:", line[:120])

# Find script with product data
for script in soup.find_all("script"):
    t = script.string or ""
    if "product" in t.lower() and len(t) > 200 and "NREUM" not in t:
        print("SCRIPT LEN", len(t))
        print(t[:500])

# Search main catalog for data attributes
main = requests.get(f"{BASE}/solutions/products/product-catalog/", headers=HEADERS, timeout=60)
for m in re.finditer(r'data-[a-z-]+="[^"]{5,100}"', main.text):
    s = m.group()
    if "product" in s.lower() or "catalog" in s.lower():
        print(s[:120])
