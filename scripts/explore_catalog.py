"""Temporary script to explore SHL catalog structure."""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
url = f"{BASE}/solutions/products/product-catalog/"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
print("status", r.status_code, "len", len(r.text))

views = set(re.findall(r"/products/product-catalog/view/[^/\"']+/", r.text))
print("unique view links", len(views))
for v in sorted(views)[:20]:
    print(v)

# Try a product detail page
if views:
    sample = sorted(views)[0]
    detail_url = BASE + sample
    dr = requests.get(detail_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    soup = BeautifulSoup(dr.text, "html.parser")
    title = soup.find("h1")
    print("\nSample:", detail_url)
    print("Title:", title.get_text(strip=True) if title else "N/A")
    # meta fields
    for label in ["Duration", "Remote", "Adaptive", "Test Type"]:
        el = soup.find(string=re.compile(label, re.I))
        if el:
            print(label, "->", el.parent.get_text(strip=True)[:120])

# Search for filter / individual test
for term in ["Individual Test", "individual-test", "Job Solution", "job-solution"]:
    print(term, "count", r.text.lower().count(term.lower()))
