from __future__ import annotations

import asyncio
import logging
import time

from async_crawler import AsyncCrawler


URLS = [
    "https://example.com",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/2",
    "https://httpbin.org/status/404",
    "https://httpbin.org/html",
]


async def fetch_sequentially(urls: list[str]) -> dict[str, str]:
    crawler = AsyncCrawler(max_concurrent=1)
    try:
        results: dict[str, str] = {}
        for url in urls:
            results[url] = await crawler.fetch_url(url)
        return results
    finally:
        await crawler.close()


async def fetch_in_parallel(urls: list[str]) -> dict[str, str]:
    crawler = AsyncCrawler(max_concurrent=5)
    try:
        return await crawler.fetch_urls(urls)
    finally:
        await crawler.close()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    sequential_started = time.perf_counter()
    sequential_results = await fetch_sequentially(URLS)
    sequential_seconds = time.perf_counter() - sequential_started

    parallel_started = time.perf_counter()
    parallel_results = await fetch_in_parallel(URLS)
    parallel_seconds = time.perf_counter() - parallel_started

    print("Request statuses:")
    for url, content in parallel_results.items():
        status = "OK" if content else "ERROR"
        print(f"{status:5} {url}")

    print(f"Sequential time: {sequential_seconds:.2f}s")
    print(f"Parallel time:   {parallel_seconds:.2f}s")
    print(f"Loaded {sum(bool(content) for content in parallel_results.values())} pages")
    print(f"Sequential loaded {sum(bool(content) for content in sequential_results.values())} pages")


if __name__ == "__main__":
    asyncio.run(main())

