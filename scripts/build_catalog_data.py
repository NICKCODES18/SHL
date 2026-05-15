"""Build catalog.json from SHL Individual Test Solutions only."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "catalog.json"

# Test type code mapping from SHL catalog
TYPE_CODE_MAP = {
    "K": "Knowledge/Technical",
    "C": "Cognitive",
    "P": "Personality",
    "A": "Ability",
    "B": "Behavioral",
    "S": "Situational Judgment",
    "D": "Development",
    "E": "Other",
}


def fetch_html(url: str, params: dict | None = None) -> str:
    r = requests.get(url, headers=HEADERS, params=params or {}, timeout=60)
    r.raise_for_status()
    return r.text


def collect_individual_slugs() -> dict[str, dict[str, str]]:
    """Paginate catalog and collect Individual Test Solutions rows."""
    url = f"{BASE}/products/product-catalog/FilteringForm/"
    slug_meta: dict[str, dict[str, str]] = {}
    seen_pages: set[tuple[str, ...]] = set()

    for page in range(1, 50):
        params = {"start": str((page - 1) * 24)} if page > 1 else {}
        html = fetch_html(url, params)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if len(tables) < 2:
            break

        individual_table = tables[1]
        page_slugs: list[str] = []
        for row in individual_table.find_all("tr")[1:]:
            link = row.find("a", href=True)
            if not link:
                continue
            href = link["href"]
            m = re.search(r"/products/product-catalog/view/([a-z0-9\-]+)/", href)
            if not m:
                continue
            slug = m.group(1)
            name = link.get_text(strip=True)
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            remote = cells[1] if len(cells) > 1 else ""
            adaptive = cells[2] if len(cells) > 2 else ""
            test_codes = cells[3] if len(cells) > 3 else ""
            slug_meta[slug] = {
                "name": name,
                "remote_testing": "yes" in remote.lower() or "✓" in remote or "check" in remote.lower(),
                "adaptive_support": "yes" in adaptive.lower() or "✓" in adaptive or "irt" in adaptive.lower(),
                "test_type_codes": test_codes,
            }
            page_slugs.append(slug)

        key = tuple(page_slugs)
        if not page_slugs or key in seen_pages:
            break
        seen_pages.add(key)
        print(f"page {page}: +{len(page_slugs)} individual tests (total {len(slug_meta)})")
        time.sleep(0.2)

    return slug_meta


def parse_detail(slug: str, list_meta: dict[str, str]) -> dict[str, Any]:
    url = f"{BASE}/products/product-catalog/view/{slug}/"
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else list_meta["name"]
    canonical = f"{BASE}/products/product-catalog/view/{slug}/"

    description = ""
    article = soup.find("article") or soup.find("main") or soup
    for p in article.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 40 and "cookie" not in text.lower():
            description = text
            break

    duration = None
    job_levels: list[str] = []
    languages: list[str] = []
    skills: list[str] = []

    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if "Duration" in t and not duration:
            duration = re.sub(r"^Duration:\s*", "", t, flags=re.I).strip() or None
        if "Job Level" in t or "job level" in t.lower():
            levels = re.sub(r"^Job Level[s]?:\s*", "", t, flags=re.I)
            job_levels = [x.strip() for x in re.split(r"[,;]", levels) if x.strip()]
        if t.startswith("Language") and "Evaluation" not in t:
            langs = re.sub(r"^Languages?:\s*", "", t, flags=re.I)
            languages.extend([x.strip() for x in langs.split(",") if x.strip()])

    codes = list_meta.get("test_type_codes", "")
    code_list = [c for c in codes.split() if c in TYPE_CODE_MAP]
    test_types = [TYPE_CODE_MAP[c] for c in code_list]
    primary_type = test_types[0] if test_types else "General"

    text_blob = f"{name} {description} {' '.join(test_types)}".lower()
    cognitive = "C" in code_list or "cognitive" in text_blob
    personality = "P" in code_list or "personality" in text_blob
    technical = "K" in code_list or any(
        k in text_blob for k in ["coding", "programming", "technical", ".net", "java", "sql", "python"]
    )
    behavioral = "B" in code_list or "behavioral" in text_blob
    situational = "S" in code_list or "situational" in text_blob or "judgment" in text_blob

    keywords = list(
        {
            w
            for w in re.findall(r"[a-z0-9\+\.#]{3,}", text_blob)
            if w not in {"the", "and", "for", "with", "that", "this", "from", "are", "new"}
        }
    )[:30]

    synonyms: list[str] = []
    name_lower = name.lower()
    if "opq" in name_lower:
        synonyms.extend(["opq32", "opq32r", "occupational personality questionnaire"])
    if "verify" in name_lower or "gat" in name_lower:
        synonyms.extend(["gsa", "general ability", "verify gat", "cognitive ability"])
    if "java" in name_lower:
        synonyms.extend(["java developer", "java programming"])
    if "coding" in name_lower or "automata" in name_lower:
        synonyms.extend(["programming test", "code assessment"])

    return {
        "name": name,
        "url": canonical,
        "description": description,
        "duration": duration,
        "remote_testing": bool(list_meta.get("remote_testing")),
        "adaptive_support": bool(list_meta.get("adaptive_support")),
        "job_levels": job_levels,
        "languages": languages,
        "skills_measured": skills,
        "test_type": primary_type,
        "test_type_codes": code_list,
        "keywords": keywords,
        "synonyms": synonyms,
        "tags": test_types,
        "cognitive": cognitive,
        "personality": personality,
        "technical": technical,
        "situational_judgment": situational,
        "behavioral": behavioral,
    }


def main() -> None:
    print("Collecting Individual Test Solutions slugs...")
    slug_meta = collect_individual_slugs()
    print(f"Found {len(slug_meta)} individual tests. Fetching details...")

    catalog: list[dict[str, Any]] = []
    for i, (slug, meta) in enumerate(slug_meta.items(), 1):
        try:
            item = parse_detail(slug, meta)
            catalog.append(item)
            if i % 20 == 0:
                print(f"  scraped {i}/{len(slug_meta)}")
            time.sleep(0.15)
        except Exception as exc:
            print(f"  WARN {slug}: {exc}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(catalog)} assessments to {OUTPUT}")


if __name__ == "__main__":
    main()
