# Day 3: Concurrency Control and Queues

This project contains the Day 3 implementation of an asynchronous web crawler assignment. `AsyncCrawler` downloads pages with `aiohttp`, extracts structured data with `HTMLParser`, and coordinates crawling through a priority queue and global/per-domain semaphore limits.

## Features

- asynchronous HTTP downloads with `AsyncCrawler`;
- concurrent URL fetching with a configurable concurrency limit;
- shared `aiohttp.ClientSession` with connection pooling and timeouts;
- `fetch_and_parse(url)` for downloading and parsing a page in one call;
- metadata extraction for title, description, and keywords;
- text extraction for the full page or a CSS selector;
- absolute URL extraction from relative links;
- image extraction with `src` and `alt`;
- heading extraction for `h1`, `h2`, and `h3`;
- table and list extraction;
- parser warnings with partial results on parsing errors;
- `CrawlerQueue` with priority, processed, failed, active, and queued states;
- `SemaphoreManager` with global and per-domain concurrency limits;
- `crawl(start_urls, max_pages=100)` for breadth-style site traversal;
- maximum crawl depth control;
- URL filtering by same domain, exclude patterns, and include patterns;
- crawl state through `visited_urls`, `failed_urls`, and `processed_urls`;
- optional real-time progress output.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Usage Example

```python
import asyncio
from async_crawler import AsyncCrawler

async def main():
    crawler = AsyncCrawler(max_concurrent=10, max_depth=2)
    try:
        results = await crawler.crawl(
            start_urls=["https://example.com"],
            max_pages=50,
            same_domain_only=True,
        )
    finally:
        await crawler.close()

    print(f"Processed {len(results)} pages")

asyncio.run(main())
```

## Demo

```powershell
python examples/day3_demo.py
```

The demo starts from one or more URLs, crawls with a depth limit, prints progress in real time, and saves a JSON summary of extracted data.

## Checks

```powershell
ruff check .
pytest
```
