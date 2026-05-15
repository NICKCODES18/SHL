"""Fetch SHL product catalog RSS."""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

for path in [
    "/products/product-catalog/rss/",
    "/products/product-catalog/FilteringForm/",
    "/products/product-catalog/FilteringFormKeywords/",
]:
    url = BASE + path
    r = requests.get(url, headers=HEADERS, timeout=60)
    print("\n===", path, "===")
    print("status", r.status_code, "type", r.headers.get("content-type"), "len", len(r.text))
    print(r.text[:800])
