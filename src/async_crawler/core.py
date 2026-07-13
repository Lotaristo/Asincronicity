from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Iterable
from urllib.parse import urlsplit

import aiohttp

from async_crawler.html_parser import HTMLParser
from async_crawler.queue import CrawlerQueue
from async_crawler.semaphore_manager import SemaphoreManager

logger = logging.getLogger(__name__)


class AsyncCrawler:
    """Basic asynchronous crawler with HTTP fetching and HTML parsing."""

    def __init__(
        self,
        max_concurrent: int = 10,
        max_depth: int = 1,
        per_domain_concurrent: int = 2,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")

        self._max_concurrent = max_concurrent
        self._max_depth = max_depth
        self._timeout = aiohttp.ClientTimeout(connect=connect_timeout, sock_read=read_timeout)
        self._connector: aiohttp.TCPConnector | None = None
        self._session: aiohttp.ClientSession | None = None
        self._semaphore_manager = SemaphoreManager(max_concurrent, per_domain_concurrent)
        self._parser = HTMLParser()
        self.visited_urls: set[str] = set()
        self.failed_urls: dict[str, str] = {}
        self.processed_urls: dict[str, dict] = {}

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._connector = aiohttp.TCPConnector(limit=self._max_concurrent)
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=self._timeout,
                raise_for_status=True,
            )
        return self._session

    async def fetch_url(self, url: str) -> str:
        """Fetch one URL and return response text, or an empty string on errors."""
        async with self._semaphore_manager.limit_for(url):
            logger.info("Starting download: %s", url)
            try:
                async with self._get_session().get(url) as response:
                    text = await response.text()
                    logger.info("Finished download: %s status=%s", url, response.status)
                    return text
            except aiohttp.ClientResponseError as exc:
                logger.warning("HTTP error for %s: status=%s", url, exc.status)
            except aiohttp.ClientError as exc:
                logger.warning("Network error for %s: %s", url, exc.__class__.__name__)
            except asyncio.TimeoutError:
                logger.warning("Timeout while downloading: %s", url)

        return ""

    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        """Fetch many URLs concurrently and return a URL-to-content mapping."""
        tasks = [asyncio.create_task(self.fetch_url(url)) for url in urls]
        contents = await asyncio.gather(*tasks)
        return dict(zip(urls, contents, strict=True))

    async def fetch_and_parse(self, url: str) -> dict:
        """Fetch a URL and return structured data extracted from the HTML."""
        html = await self.fetch_url(url)
        return await self._parser.parse_html(html, url)

    async def crawl(
        self,
        start_urls: list[str],
        max_pages: int = 100,
        same_domain_only: bool = False,
        exclude_patterns: Iterable[str] | None = None,
        include_patterns: Iterable[str] | None = None,
        show_progress: bool = False,
    ) -> dict[str, dict]:
        """Crawl pages from start URLs with queue, depth, and URL filtering controls."""
        if max_pages < 1:
            return {}

        queue = CrawlerQueue()
        self.visited_urls = set()
        self.failed_urls = {}
        self.processed_urls = {}
        depths: dict[str, int] = {}
        start_domains = {urlsplit(url).netloc.lower() for url in start_urls}
        exclude_regexes = [re.compile(pattern) for pattern in exclude_patterns or []]
        include_regexes = [re.compile(pattern) for pattern in include_patterns or []]
        started_at = time.perf_counter()

        for url in start_urls:
            if self._should_enqueue(url, start_domains, same_domain_only, exclude_regexes, include_regexes):
                if queue.add_url(url, priority=self._max_depth):
                    depths[url] = 0

        tasks: set[asyncio.Task[tuple[str, dict | None, str | None]]] = set()
        while len(self.visited_urls) < max_pages:
            while (
                len(tasks) < self._max_concurrent
                and queue.has_pending()
                and len(self.visited_urls) < max_pages
            ):
                url = await queue.get_next()
                if url is None:
                    break
                self.visited_urls.add(url)
                tasks.add(asyncio.create_task(self._crawl_one(url)))

            if not tasks:
                break

            done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                url, result, error = task.result()
                if result is None:
                    error_message = error or "Unknown crawl error"
                    self.failed_urls[url] = error_message
                    queue.mark_failed(url, error_message)
                    continue

                self.processed_urls[url] = result
                queue.mark_processed(url)
                current_depth = depths.get(url, 0)
                if current_depth < self._max_depth:
                    next_depth = current_depth + 1
                    for link in result["links"]:
                        if self._should_enqueue(
                            link,
                            start_domains,
                            same_domain_only,
                            exclude_regexes,
                            include_regexes,
                        ):
                            if queue.add_url(link, priority=self._max_depth - next_depth):
                                depths[link] = next_depth

            if show_progress:
                self._print_progress(queue, started_at)

        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        if show_progress:
            self._print_progress(queue, started_at)
        return self.processed_urls

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()

    async def _crawl_one(self, url: str) -> tuple[str, dict | None, str | None]:
        html = await self.fetch_url(url)
        if not html:
            return url, None, "Empty response or fetch failed"
        try:
            return url, await self._parser.parse_html(html, url), None
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", url, exc.__class__.__name__)
            return url, None, exc.__class__.__name__

    def _should_enqueue(
        self,
        url: str,
        start_domains: set[str],
        same_domain_only: bool,
        exclude_regexes: list[re.Pattern[str]],
        include_regexes: list[re.Pattern[str]],
    ) -> bool:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        normalized_url = parsed.geturl()
        if same_domain_only and parsed.netloc.lower() not in start_domains:
            return False
        if exclude_regexes and any(pattern.search(normalized_url) for pattern in exclude_regexes):
            return False
        if include_regexes and not any(pattern.search(normalized_url) for pattern in include_regexes):
            return False
        return True

    def _print_progress(self, queue: CrawlerQueue, started_at: float) -> None:
        elapsed = max(time.perf_counter() - started_at, 0.001)
        processed = len(self.processed_urls)
        failed = len(self.failed_urls)
        queued = queue.get_stats()["queued"]
        rate = processed / elapsed
        print(
            f"processed={processed} queued={queued} failed={failed} "
            f"rate={rate:.2f} pages/sec"
        )
