#!/usr/bin/env python3
"""Local SEO/AEO regression audit for zonted.com.

Hard failures cover crawlability, schema validity, and indexable-page basics.
Warnings cover editorial length guidance so long narrative titles do not block
shipping.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://zonted.com"
SKIP_PARTS = {".git", "node_modules", "prototype", "_templates"}
EXPECTED_AUTHOR_SAME_AS = {
    "https://x.com/bernardjhuang",
    "https://github.com/bernardjhuang",
    "https://www.linkedin.com/in/bernardjhuang/",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.h1_count = 0
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self._jsonld_depth = 0
        self._jsonld_parts: list[str] = []
        self.jsonld: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        if attrs_dict.get("id"):
            self.ids.add(attrs_dict["id"])
        if tag.lower() == "title":
            self.in_title = True
        elif tag.lower() == "h1":
            self.h1_count += 1
        elif tag.lower() == "meta":
            self.meta.append(attrs_dict)
        elif tag.lower() == "link":
            self.links.append(attrs_dict)
        elif tag.lower() == "script":
            self.scripts.append(attrs_dict)
            if attrs_dict.get("type", "").lower() == "application/ld+json":
                self._jsonld_depth = 1
                self._jsonld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False
        elif tag.lower() == "script" and self._jsonld_depth:
            self.jsonld.append("".join(self._jsonld_parts).strip())
            self._jsonld_depth = 0
            self._jsonld_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._jsonld_depth:
            self._jsonld_parts.append(data)

    @property
    def title(self) -> str:
        return re.sub(r"\s+", " ", "".join(self.title_parts)).strip()

    def meta_content(self, *, name: str | None = None, prop: str | None = None) -> str:
        for attrs in self.meta:
            if name and attrs.get("name", "").lower() == name.lower():
                return attrs.get("content", "").strip()
            if prop and attrs.get("property", "").lower() == prop.lower():
                return attrs.get("content", "").strip()
        return ""

    def canonical(self) -> str:
        for attrs in self.links:
            rel = attrs.get("rel", "").lower().split()
            if "canonical" in rel:
                return attrs.get("href", "").strip()
        return ""

    def is_noindex(self) -> bool:
        return "noindex" in self.meta_content(name="robots").lower()


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text("utf-8", errors="ignore"))
    return parser


def public_url_for(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if str(rel) == "index.html":
        return f"{SITE_URL}/"
    if rel.name == "index.html":
        return f"{SITE_URL}/{'/'.join(rel.parent.parts)}/"
    return f"{SITE_URL}/{rel.as_posix()}"


def jsonld_objects(page: PageParser, failures: list[str], rel: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for raw in page.jsonld:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            failures.append(f"{rel}: invalid JSON-LD: {exc}")
            continue
        queue = data if isinstance(data, list) else [data]
        for item in queue:
            if isinstance(item, dict) and "@graph" in item and isinstance(item["@graph"], list):
                objects.extend(x for x in item["@graph"] if isinstance(x, dict))
            elif isinstance(item, dict):
                objects.append(item)
    return objects


def has_type(obj: dict[str, Any], type_name: str) -> bool:
    t = obj.get("@type")
    if isinstance(t, list):
        return type_name in t
    return t == type_name


def load_sitemap() -> set[str]:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return set()
    tree = ET.parse(sitemap)
    return {
        el.text.strip()
        for el in tree.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if el.text
    }


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    sitemap_urls = load_sitemap()
    if not sitemap_urls:
        failures.append("sitemap.xml missing or empty")

    html_paths = sorted(
        p for p in ROOT.rglob("*.html")
        if not any(part in SKIP_PARTS for part in p.relative_to(ROOT).parts)
    )

    for path in html_paths:
        rel = path.relative_to(ROOT).as_posix()
        page = parse_page(path)
        url = public_url_for(path)
        noindex = page.is_noindex()
        title = page.title
        desc = page.meta_content(name="description")
        canonical = page.canonical()

        if rel == "404.html":
            continue

        if not title:
            failures.append(f"{rel}: missing <title>")
        elif len(title) > 70:
            warnings.append(f"{rel}: long title ({len(title)} chars)")

        if not desc:
            failures.append(f"{rel}: missing meta description")
        elif len(desc) > 170:
            warnings.append(f"{rel}: long meta description ({len(desc)} chars)")

        if not canonical:
            failures.append(f"{rel}: missing canonical")
        elif not canonical.startswith(f"{SITE_URL}/"):
            failures.append(f"{rel}: canonical outside site: {canonical}")

        if not noindex:
            if page.h1_count != 1:
                failures.append(f"{rel}: expected exactly one H1, found {page.h1_count}")
            if url not in sitemap_urls:
                failures.append(f"{rel}: indexable page missing from sitemap: {url}")
        elif url in sitemap_urls:
            failures.append(f"{rel}: noindex page is included in sitemap: {url}")

        if page.meta_content(prop="og:image") and page.meta_content(name="twitter:card") == "summary":
            failures.append(f"{rel}: image-backed page uses twitter summary card")

        objects = jsonld_objects(page, failures, rel)
        if rel.startswith("posts/") and rel.endswith("/index.html") and rel != "posts/index.html":
            article = next((obj for obj in objects if has_type(obj, "Article")), None)
            if not article:
                failures.append(f"{rel}: missing Article JSON-LD")
            else:
                for field in [
                    "headline",
                    "description",
                    "image",
                    "datePublished",
                    "dateModified",
                    "mainEntityOfPage",
                    "author",
                    "publisher",
                    "url",
                ]:
                    if not article.get(field):
                        failures.append(f"{rel}: Article JSON-LD missing {field}")
                author = article.get("author") if isinstance(article.get("author"), dict) else {}
                same_as = set(author.get("sameAs") or []) if isinstance(author, dict) else set()
                if not EXPECTED_AUTHOR_SAME_AS.issubset(same_as):
                    failures.append(f"{rel}: Article author.sameAs incomplete")
                publisher = article.get("publisher") if isinstance(article.get("publisher"), dict) else {}
                if not isinstance(publisher, dict) or publisher.get("@type") != "Organization":
                    failures.append(f"{rel}: Article publisher must be Organization")
                if not isinstance(publisher, dict) or not publisher.get("logo"):
                    failures.append(f"{rel}: Article publisher.logo missing")

    if failures:
        print("SEO audit failed:")
        for failure in failures:
            print(f"FAIL: {failure}")
    else:
        print("SEO audit passed: no hard failures")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"WARN: {warning}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
