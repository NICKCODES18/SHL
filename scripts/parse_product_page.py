"""Parse one SHL product detail page structure."""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
slug = "net-mvc-new"
url = f"{BASE}/products/product-catalog/view/{slug}/"
r = requests.get(url, headers=HEADERS, timeout=60)
soup = BeautifulSoup(r.text, "html.parser")

h1 = soup.find("h1")
print("NAME:", h1.get_text(strip=True) if h1 else None)

# Description paragraphs near h1
parent = h1.find_parent() if h1 else None
if parent:
    ps = parent.find_all("p")
    for p in ps[:5]:
        t = p.get_text(strip=True)
        if t:
            print("P:", t[:200])

# Spec rows - common patterns
for p in soup.find_all("p"):
    t = p.get_text(" ", strip=True)
    if any(k in t for k in ["Test Type", "Remote Testing", "Adaptive", "Duration", "Job Level"]):
        print("SPEC:", t[:150])

# Tooltip spans with test type codes
for span in soup.find_all("span", attrs={"data-tooltip": True}):
    txt = span.get_text(strip=True)
    if txt and len(txt) < 10:
        print("TOOLTIP SPAN:", txt, span.get("data-tooltip"))

# Links
canonical = soup.find("link", rel="canonical")
print("CANONICAL:", canonical.get("href") if canonical else url)
