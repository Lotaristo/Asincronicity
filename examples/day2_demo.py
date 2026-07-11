from __future__ import annotations

import asyncio
import logging

from async_crawler import AsyncCrawler


URLS = [
    "https://example.com",
    "https://httpbin.org/html",
    "https://www.python.org",
]


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    crawler = AsyncCrawler(max_concurrent=3)
    try:
        results = await asyncio.gather(*(crawler.fetch_and_parse(url) for url in URLS))
    finally:
        await crawler.close()

    for result in results:
        summary = {
            "url": result["url"],
            "title": result["title"],
            "text_length": len(result["text"]),
            "links_count": len(result["links"]),
            "links": result["links"][:5],
            "images_count": len(result["images"]),
            "headings_count": len(result["headings"]),
            "tables_count": len(result["tables"]),
            "lists_count": len(result["lists"]),
        }
        print(summary)


if __name__ == "__main__":
    asyncio.run(main())
