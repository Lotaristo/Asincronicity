# Day 2: HTML Parsing and Data Extraction

This project contains the Day 2 implementation of an asynchronous web crawler assignment. `AsyncCrawler` downloads pages with `aiohttp`, and `HTMLParser` extracts structured data from HTML with BeautifulSoup and lxml.

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
- parser warnings with partial results on parsing errors.

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
    crawler = AsyncCrawler(max_concurrent=5)
    try:
        result = await crawler.fetch_and_parse("https://example.com")
    finally:
        await crawler.close()

    print({
        "url": result["url"],
        "title": result["title"],
        "text_length": len(result["text"]),
        "links_count": len(result["links"]),
        "images_count": len(result["images"]),
    })

asyncio.run(main())
```

## Demo

```powershell
python examples/day2_demo.py
```

The demo downloads and parses several pages, then prints a compact summary with title, text length, links count, image count, and other extracted data counts.

## Checks

```powershell
ruff check .
pytest
```
