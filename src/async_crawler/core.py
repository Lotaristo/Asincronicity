from __future__ import annotations

import asyncio
import logging

import aiohttp

from async_crawler.html_parser import HTMLParser

logger = logging.getLogger(__name__)


class AsyncCrawler:
    """Basic asynchronous crawler with HTTP fetching and HTML parsing."""

    def __init__(
        self,
        max_concurrent: int = 10,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        self._max_concurrent = max_concurrent
        self._timeout = aiohttp.ClientTimeout(connect=connect_timeout, sock_read=read_timeout)
        self._connector: aiohttp.TCPConnector | None = None
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._parser = HTMLParser()

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
        async with self._semaphore:
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

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
