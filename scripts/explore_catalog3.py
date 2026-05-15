"""Find all SHL catalog product URLs."""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Try sitemap
for path in ["/sitemap.xml", "/sitemap_index.xml", "/en/sitemap.xml"]:
    try:
        r = requests.get(BASE + path, headers=HEADERS, timeout=30)
        if r.status_code == 200 and "xml" in r.headers.get("content-type", ""):
            urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
            prod = [u for u in urls if "product-catalog/view" in u]
            print(path, "total", len(urls), "products", len(prod))
            if prod:
                print("sample", prod[:5])
    except Exception as e:
        print(path, e)

# Search robots.txt
r = requests.get(BASE + "/robots.txt", headers=HEADERS, timeout=30)
print("robots", r.status_code)
for line in r.text.splitlines()[:30]:
    if "sitemap" in line.lower():
        print(line)

# Parse detail page with better extraction
url = f"{BASE}/products/product-catalog/view/net-mvc-new/"
r = requests.get(url, headers=HEADERS, timeout=60)
soup = BeautifulSoup(r.text, "html.parser")

# Find product info section
for div in soup.find_all("motion-product-catalogue-detail"):
    print("custom element found")

# Look for key-value pairs in page
html = r.text
# Test type pattern
for pat in [
    r"Test Type[^<]*</[^>]+>\s*<[^>]+>([^<]+)",
    r'"testType"\s*:\s*"([^"]+)"',
    r"test_type[\"']?\s*[:=]\s*[\"']([^\"']+)",
]:
    m = re.search(pat, html, re.I)
    if m:
        print("test type match", m.group(1)[:50])

# All product-catalog/view in sitemap from main page pagination?
# Check if there's __NEXT_DATA__ or similar
for key in ["__NEXT_DATA__", "__NUXT__", "window.__", "productCatalog", "catalogData"]:
    if key in html:
        idx = html.find(key)
        print("found", key, "at", idx, html[idx:idx+200])
