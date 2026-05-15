"""Full parse of SHL product detail page."""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

slugs = [
    "net-mvc-new",  # technical K
    "account-manager-solution",  # job solution?
    "apprentice-8-0-job-focused-assessment",
]

for slug in slugs:
    url = f"{BASE}/products/product-catalog/view/{slug}/"
    r = requests.get(url, headers=HEADERS, timeout=60)
    soup = BeautifulSoup(r.text, "html.parser")
    print("\n" + "=" * 60, slug)
    h1 = soup.find("h1")
    print("NAME:", h1.get_text(strip=True) if h1 else None)

    # All paragraphs with labels
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if t and len(t) < 200:
            if any(k in t for k in ["Test Type", "Remote", "Adaptive", "Duration", "Job Level", "Language", "Solution", "Individual", "Job"]):
                print(" ", t)

    # Table rows
    for tr in soup.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        if cells and any("Individual" in c or "Job" in c or "Test" in c for c in cells):
            print(" TR:", cells)

    # Description - usually first content block after h1
    article = soup.find("article") or soup.find("main")
    if article:
        paras = [p.get_text(strip=True) for p in article.find_all("p") if len(p.get_text(strip=True)) > 50]
        if paras:
            print(" DESC:", paras[0][:250])

    # Skills / keywords sections
    for h in soup.find_all(["h2", "h3", "h4"]):
        t = h.get_text(strip=True)
        if any(k in t.lower() for k in ["skill", "measure", "competenc", "ability"]):
            sib = h.find_next_sibling()
            print(" SECTION", t, "->", (sib.get_text(strip=True)[:150] if sib else ""))
