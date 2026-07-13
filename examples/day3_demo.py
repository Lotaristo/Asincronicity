from __future__ import annotations

import asyncio
import json
import logging

import aiofiles
from async_crawler import AsyncCrawler


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    crawler = AsyncCrawler(max_concurrent=10, max_depth=2, per_domain_concurrent=2)
    try:
        results = await crawler.crawl(
            start_urls=["https://example.com"],
            max_pages=50,
            same_domain_only=True,
            show_progress=True,
        )
    finally:
        await crawler.close()

    summaries = [
        {
            "url": page["url"],
            "title": page["title"],
            "text_length": len(page["text"]),
            "links_count": len(page["links"]),
            "images_count": len(page["images"]),
        }
        for page in results.values()
    ]
    output_path = "day3_results.json"
    async with aiofiles.open(output_path, "w", encoding="utf-8") as file:
        await file.write(json.dumps(summaries, indent=2))
    print(f"Processed {len(results)} pages")
    print(f"Saved summary to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
