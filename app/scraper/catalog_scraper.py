"""
Scraper for SHL Individual Test Solutions catalog (product-catalog table 2).
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.models.schemas import AssessmentMetadata

logger = logging.getLogger(__name__)

BASE = "https://www.shl.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

TYPE_CODE_MAP: dict[str, str] = {
    "K": "Knowledge/Technical",
    "C": "Cognitive",
    "P": "Personality",
    "A": "Ability",
    "B": "Behavioral",
    "S": "Situational Judgment",
    "D": "Development",
    "E": "Other",
}


class CatalogScraper:
    """Scrapes Individual Test Solutions from the SHL product catalog."""

    def __init__(self, base_url: str = BASE) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get(self, path: str, params: dict[str, str] | None = None) -> str:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        response = self.session.get(url, params=params or {}, timeout=60)
        response.raise_for_status()
        return response.text

    def collect_individual_slugs(self) -> dict[str, dict[str, Any]]:
        """Paginate catalog list and return slug -> list-row metadata."""
        url = "/products/product-catalog/FilteringForm/"
        slug_meta: dict[str, dict[str, Any]] = {}
        seen_pages: set[tuple[str, ...]] = set()

        for page in range(1, 60):
            params = {"start": str((page - 1) * 24)} if page > 1 else {}
            html = self._get(url, params)
            soup = BeautifulSoup(html, "html.parser")
            tables = soup.find_all("table")
            if len(tables) < 2:
                break

            page_slugs: list[str] = []
            for row in tables[1].find_all("tr")[1:]:
                link = row.find("a", href=True)
                if not link:
                    continue
                match = re.search(
                    r"/products/product-catalog/view/([a-z0-9\-]+)/", link["href"]
                )
                if not match:
                    continue
                slug = match.group(1)
                cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
                remote = cells[1] if len(cells) > 1 else ""
                adaptive = cells[2] if len(cells) > 2 else ""
                test_codes = cells[3] if len(cells) > 3 else ""
                slug_meta[slug] = {
                    "name": link.get_text(strip=True),
                    "remote_testing": self._has_check(remote),
                    "adaptive_support": self._has_check(adaptive),
                    "test_type_codes": test_codes,
                }
                page_slugs.append(slug)

            key = tuple(page_slugs)
            if not page_slugs or key in seen_pages:
                break
            seen_pages.add(key)
            logger.info("Catalog page %s: %s individual tests", page, len(page_slugs))
            time.sleep(0.15)

        return slug_meta

    @staticmethod
    def _has_check(value: str) -> bool:
        lowered = value.lower()
        return any(x in lowered for x in ("yes", "✓", "check", "true", "supported"))

    def parse_product_page(self, slug: str, list_meta: dict[str, Any]) -> AssessmentMetadata:
        """Fetch and parse a single product detail page."""
        html = self._get(f"/products/product-catalog/view/{slug}/")
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1")
        name = h1.get_text(strip=True) if h1 else list_meta["name"]
        url = f"{self.base_url}/products/product-catalog/view/{slug}/"

        description = ""
        root = soup.find("article") or soup.find("main") or soup
        for paragraph in root.find_all("p"):
            text = paragraph.get_text(strip=True)
            if len(text) > 40 and "cookie" not in text.lower():
                description = text
                break

        duration: str | None = None
        job_levels: list[str] = []
        languages: list[str] = []

        for paragraph in soup.find_all("p"):
            text = paragraph.get_text(" ", strip=True)
            if "Duration" in text and not duration:
                duration = re.sub(r"^Duration:\s*", "", text, flags=re.I).strip() or None
            if "job level" in text.lower():
                levels = re.sub(r"^Job Levels?:\s*", "", text, flags=re.I)
                job_levels = [x.strip() for x in re.split(r"[,;]", levels) if x.strip()]
            if text.startswith("Language") and "Evaluation" not in text:
                langs = re.sub(r"^Languages?:\s*", "", text, flags=re.I)
                languages.extend(x.strip() for x in langs.split(",") if x.strip())

        codes = [c for c in list_meta.get("test_type_codes", "").split() if c in TYPE_CODE_MAP]
        test_types = [TYPE_CODE_MAP[c] for c in codes]
        primary_type = test_types[0] if test_types else "General"
        blob = f"{name} {description} {' '.join(test_types)}".lower()

        keywords = list(
            {
                w
                for w in re.findall(r"[a-z0-9\+\.#]{3,}", blob)
                if w
                not in {"the", "and", "for", "with", "that", "this", "from", "are", "new", "shl"}
            }
        )[:40]

        synonyms = self._build_synonyms(name, blob)
        skills = self._extract_skills(blob, codes)

        return AssessmentMetadata(
            name=name,
            url=url,
            description=description,
            duration=duration,
            remote_testing=bool(list_meta.get("remote_testing")),
            adaptive_support=bool(list_meta.get("adaptive_support")),
            job_levels=job_levels,
            languages=languages,
            skills_measured=skills,
            test_type=primary_type,
            test_type_codes=codes,
            keywords=keywords,
            synonyms=synonyms,
            tags=test_types,
            cognitive="C" in codes or "cognitive" in blob,
            personality="P" in codes or "personality" in blob,
            technical="K" in codes
            or any(
                k in blob
                for k in (
                    "coding",
                    "programming",
                    "technical",
                    ".net",
                    "java",
                    "sql",
                    "python",
                    "software",
                )
            ),
            behavioral="B" in codes or "behavioral" in blob,
            situational_judgment="S" in codes
            or "situational" in blob
            or "judgment" in blob,
        )

    @staticmethod
    def _build_synonyms(name: str, blob: str) -> list[str]:
        synonyms: list[str] = []
        lower = name.lower()
        if "opq" in lower or "personality" in lower:
            synonyms.extend(["opq", "opq32", "opq32r", "occupational personality questionnaire"])
        if "verify" in lower or "gat" in lower or "general ability" in lower:
            synonyms.extend(["gsa", "verify gat", "general ability test", "cognitive ability"])
        if "java" in lower:
            synonyms.extend(["java developer", "java programming", "java 8"])
        if "coding" in lower or "automata" in lower:
            synonyms.extend(["programming test", "code assessment", "developer test"])
        if "sjt" in lower or "situational" in lower:
            synonyms.extend(["situational judgment", "sjt"])
        if "mq" in lower or "motivation" in lower:
            synonyms.extend(["motivation questionnaire", "mq"])
        return list(dict.fromkeys(synonyms))

    @staticmethod
    def _extract_skills(blob: str, codes: list[str]) -> list[str]:
        skills: list[str] = []
        skill_terms = [
            "leadership",
            "teamwork",
            "communication",
            "reasoning",
            "numerical",
            "logical",
            "coding",
            "problem solving",
            "stakeholder",
            "judgment",
        ]
        for term in skill_terms:
            if term in blob:
                skills.append(term.title())
        if "K" in codes and "Coding" not in skills:
            skills.append("Technical Knowledge")
        if "C" in codes and "Reasoning" not in " ".join(skills):
            skills.append("Cognitive Reasoning")
        return skills

    def scrape_catalog(self) -> list[AssessmentMetadata]:
        """Scrape all Individual Test Solutions."""
        logger.info("Collecting Individual Test Solutions from SHL catalog...")
        slug_meta = self.collect_individual_slugs()
        assessments: list[AssessmentMetadata] = []

        for index, (slug, meta) in enumerate(slug_meta.items(), 1):
            try:
                assessments.append(self.parse_product_page(slug, meta))
                if index % 25 == 0:
                    logger.info("Scraped %s/%s products", index, len(slug_meta))
                time.sleep(0.12)
            except Exception as exc:
                logger.warning("Failed to scrape %s: %s", slug, exc)

        logger.info("Scraped %s assessments total", len(assessments))
        return assessments

    def save_to_json(
        self,
        assessments: list[AssessmentMetadata],
        filepath: str | None = None,
    ) -> None:
        path = Path(filepath or settings.CATALOG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(
                [a.model_dump() for a in assessments],
                handle,
                indent=2,
                ensure_ascii=False,
            )
        logger.info("Saved catalog to %s", path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = CatalogScraper()
    data = scraper.scrape_catalog()
    scraper.save_to_json(data)
