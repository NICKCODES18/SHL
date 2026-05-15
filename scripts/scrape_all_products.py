"""Scrape all products via GET filtering."""
import re
import time
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
session = requests.Session()
session.headers.update(HEADERS)

def get_views(params: dict) -> set[str]:
    url = f"{BASE}/products/product-catalog/FilteringForm/"
    r = session.get(url, params=params, timeout=60)
    return set(re.findall(r"/products/product-catalog/view/([a-z0-9\-]+)/", r.text))

# Try empty filter
all_slugs = set()
base_views = get_views({})
print("base", len(base_views))
all_slugs.update(base_views)

# Try each job family
for jf in range(1, 8):
    slugs = get_views({"Form_FilteringForm_job_family": str(jf)})
    print("job_family", jf, len(slugs))
    all_slugs.update(slugs)
    time.sleep(0.3)

# Keywords search
for kw in ["java", "python", "personality", "cognitive", "coding", "opq", "verify"]:
    slugs = get_views({"Form_FilteringFormKeywords_keyword": kw})
    print("kw", kw, len(slugs))
    all_slugs.update(slugs)
    time.sleep(0.3)

# Main catalog page with pagination?
for page in range(1, 20):
    slugs = get_views({"start": str((page-1)*24)})
    if not slugs:
        break
    print("page", page, len(slugs))
    all_slugs.update(slugs)

print("TOTAL UNIQUE SLUGS", len(all_slugs))
print(sorted(all_slugs)[:30])
