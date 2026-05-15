"""Parse catalog list table for solution types."""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
url = f"{BASE}/products/product-catalog/FilteringForm/"
r = requests.get(url, headers=HEADERS, timeout=60)
soup = BeautifulSoup(r.text, "html.parser")

# Find table
tables = soup.find_all("table")
print("tables", len(tables))
for ti, table in enumerate(tables):
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if headers:
        print(f"\nTable {ti} headers:", headers)
    rows = table.find_all("tr")
    for row in rows[1:6]:
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        links = [a.get("href") for a in row.find_all("a", href=True)]
        if cells:
            print(" ROW:", cells[:6], "link", links[0] if links else "")

# Search for Individual Test Solutions text
for th in soup.find_all("th"):
    t = th.get_text(strip=True)
    if "Individual" in t or "Job" in t:
        print("TH:", t)
