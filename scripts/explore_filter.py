"""Explore SHL catalog filtering POST."""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
session = requests.Session()
session.headers.update(HEADERS)

# Get main page and extract form
url = f"{BASE}/solutions/products/product-catalog/"
r = session.get(url, timeout=60)
soup = BeautifulSoup(r.text, "html.parser")

forms = soup.find_all("form")
print("forms", len(forms))
for f in forms:
    print("FORM action", f.get("action"), "method", f.get("method"), "id", f.get("id"))
    for inp in f.find_all(["input", "select"]):
        print(" ", inp.name, inp.get("type"), inp.get("value"), inp.get("id"))

# Search for filter options in HTML
for term in ["Individual", "Job Solution", "solutionType", "productType", "testType"]:
    idx = r.text.find(term)
    if idx >= 0:
        print(term, "context:", r.text[idx:idx+200].replace("\n", " ")[:200])

# Find select options
for sel in soup.find_all("select"):
    opts = [(o.get("value"), o.get_text(strip=True)) for o in sel.find_all("option")]
    if opts:
        print("SELECT", sel.get("name"), "opts", len(opts), opts[:10])

# Search motion-product or custom elements
for tag in soup.find_all(True):
    if tag.name and "product" in tag.name.lower():
        print("TAG", tag.name)

# POST to FilteringForm with individual test filter
post_url = f"{BASE}/products/product-catalog/FilteringForm/"
data_variants = [
    {"SolutionType": "Individual Test Solutions"},
    {"solutionType": "individual"},
    {"ProductType": "Individual"},
    {"TestType": "K"},
]
for data in data_variants:
    try:
        pr = session.post(post_url, data=data, timeout=60)
        views = set(re.findall(r"/products/product-catalog/view/[a-z0-9\-]+/", pr.text))
        print("POST", data, "views", len(views))
    except Exception as e:
        print("POST err", e)
