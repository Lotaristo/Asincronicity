# Day 1: Basic Asynchronous HTTP Client

This project contains the Day 1 implementation of an asynchronous web crawler assignment. The `AsyncCrawler` class downloads web pages with `aiohttp.ClientSession`, limits concurrency, uses connection pooling, and handles network errors, HTTP errors, and timeouts without crashing the program.

## Features

- `AsyncCrawler(max_concurrent=10)` with a configurable concurrency limit;
- `fetch_url(url)` for downloading a single page;
- `fetch_urls(urls)` for downloading multiple URLs in parallel;
- shared `aiohttp.ClientSession` with `connect` and `sock_read` timeouts;
- connection pooling through `aiohttp.TCPConnector`;
- explicit cleanup through `close()`;
- basic logging for request start, success, and errors.

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
    urls = [
        "https://example.com",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2",
    ]
    results = await crawler.fetch_urls(urls)
    await crawler.close()
    loaded_pages = sum(bool(page) for page in results.values())
    print(f"Loaded {loaded_pages} pages")

asyncio.run(main())
```

## Demo

```powershell
python examples/day1_demo.py
```

The demo downloads several URLs sequentially and in parallel, prints the status for each request, and compares the total execution time.

## Checks

```powershell
ruff check .
pytest
```