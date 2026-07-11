from __future__ import annotations

import logging
from collections.abc import Callable
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HTMLParser:
    """Extract structured data from HTML documents."""

    async def parse_html(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html or "", "lxml")

        def extract(field: str, default: object, callback: Callable[[], object]) -> object:
            try:
                return callback()
            except Exception as exc:
                logger.warning(
                    "HTML parsing warning for %s: %s extraction failed with %s",
                    url,
                    field,
                    exc.__class__.__name__,
                )
                return default

        metadata = extract("metadata", {}, lambda: self.extract_metadata(soup))
        if not isinstance(metadata, dict):
            metadata = {}

        return {
            "url": url,
            "title": metadata.get("title", ""),
            "text": extract("text", "", lambda: self.extract_text(soup)),
            "links": extract("links", [], lambda: self.extract_links(soup, url)),
            "metadata": metadata,
            "images": extract("images", [], lambda: self.extract_images(soup, url)),
            "headings": extract("headings", [], lambda: self.extract_headings(soup)),
            "tables": extract("tables", [], lambda: self.extract_tables(soup)),
            "lists": extract("lists", [], lambda: self.extract_lists(soup)),
        }

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        for tag in soup.find_all("a", href=True):
            absolute_url = self._normalize_url(tag["href"], base_url)
            if absolute_url and absolute_url not in seen:
                seen.add(absolute_url)
                links.append(absolute_url)
        return links

    def extract_text(self, soup: BeautifulSoup, selector: str | None = None) -> str:
        source = soup.select_one(selector) if selector else soup.body or soup
        if source is None:
            return ""
        return " ".join(source.get_text(" ", strip=True).split())

    def extract_metadata(self, soup: BeautifulSoup) -> dict:
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        metadata = {
            "title": title,
            "description": "",
            "keywords": "",
        }
        for tag in soup.find_all("meta"):
            name = (tag.get("name") or tag.get("property") or "").lower()
            content = tag.get("content", "")
            if name in {"description", "og:description"} and not metadata["description"]:
                metadata["description"] = content.strip()
            elif name == "keywords":
                metadata["keywords"] = content.strip()
        return metadata

    def extract_images(self, soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        for tag in soup.find_all("img", src=True):
            src = self._normalize_url(tag["src"], base_url)
            if src:
                images.append({"src": src, "alt": tag.get("alt", "")})
        return images

    def extract_headings(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        headings: list[dict[str, str]] = []
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = " ".join(tag.get_text(" ", strip=True).split())
            if text:
                headings.append({"level": tag.name, "text": text})
        return headings

    def extract_tables(self, soup: BeautifulSoup) -> list[list[list[str]]]:
        tables: list[list[list[str]]] = []
        for table in soup.find_all("table"):
            rows: list[list[str]] = []
            for row in table.find_all("tr"):
                cells = [
                    " ".join(cell.get_text(" ", strip=True).split())
                    for cell in row.find_all(["th", "td"])
                ]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables

    def extract_lists(self, soup: BeautifulSoup) -> list[dict[str, object]]:
        lists: list[dict[str, object]] = []
        for list_tag in soup.find_all(["ul", "ol"]):
            items = [
                " ".join(item.get_text(" ", strip=True).split())
                for item in list_tag.find_all("li", recursive=False)
            ]
            items = [item for item in items if item]
            if items:
                lists.append({"type": list_tag.name, "items": items})
        return lists

    def _normalize_url(self, value: str, base_url: str) -> str | None:
        absolute_url = urljoin(base_url, value.strip())
        absolute_url, _fragment = urldefrag(absolute_url)
        parsed = urlsplit(absolute_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        return absolute_url
