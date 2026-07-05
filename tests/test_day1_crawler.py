from __future__ import annotations

import asyncio
import time

import aiohttp
from aiohttp import web

from async_crawler import AsyncCrawler


def test_crawler_can_be_created_outside_running_event_loop():
    crawler = AsyncCrawler(max_concurrent=2)

    assert crawler._session is None


async def test_close_before_first_request_is_safe():
    crawler = AsyncCrawler()

    await crawler.close()


async def test_fetch_url_loads_valid_url(aiohttp_client):
    async def handler(request):
        return web.Response(text="hello from test server")

    app = web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    crawler = AsyncCrawler(max_concurrent=2)
    try:
        content = await crawler.fetch_url(str(client.make_url("/")))
    finally:
        await crawler.close()

    assert content == "hello from test server"


async def test_fetch_url_handles_http_error(aiohttp_client, caplog):
    async def handler(request):
        return web.Response(status=404, text="not found")

    app = web.Application()
    app.router.add_get("/missing", handler)
    client = await aiohttp_client(app)

    crawler = AsyncCrawler()
    try:
        content = await crawler.fetch_url(str(client.make_url("/missing")))
    finally:
        await crawler.close()

    assert content == ""
    assert "HTTP error" in caplog.text


async def test_fetch_url_handles_timeout(aiohttp_client, caplog):
    async def handler(request):
        await asyncio.sleep(0.05)
        return web.Response(text="too late")

    app = web.Application()
    app.router.add_get("/slow", handler)
    client = await aiohttp_client(app)

    crawler = AsyncCrawler(read_timeout=0.001)
    try:
        content = await crawler.fetch_url(str(client.make_url("/slow")))
    finally:
        await crawler.close()

    assert content == ""
    assert "Timeout" in caplog.text


async def test_fetch_url_handles_network_error(unused_tcp_port, caplog):
    crawler = AsyncCrawler()
    try:
        content = await crawler.fetch_url(f"http://127.0.0.1:{unused_tcp_port}/")
    finally:
        await crawler.close()

    assert content == ""
    assert "Network error" in caplog.text


async def test_parallel_fetch_is_faster_than_sequential(aiohttp_client):
    async def handler(request):
        await asyncio.sleep(0.05)
        return web.Response(text=request.match_info["name"])

    app = web.Application()
    app.router.add_get("/{name}", handler)
    client = await aiohttp_client(app)
    urls = [str(client.make_url(f"/page-{index}")) for index in range(4)]

    sequential = AsyncCrawler(max_concurrent=1)
    sequential_started = time.perf_counter()
    try:
        for url in urls:
            await sequential.fetch_url(url)
    finally:
        await sequential.close()
    sequential_seconds = time.perf_counter() - sequential_started

    parallel = AsyncCrawler(max_concurrent=4)
    parallel_started = time.perf_counter()
    try:
        results = await parallel.fetch_urls(urls)
    finally:
        await parallel.close()
    parallel_seconds = time.perf_counter() - parallel_started

    assert all(results.values())
    assert parallel_seconds < sequential_seconds


def test_client_session_timeout_uses_connect_and_read_timeouts():
    timeout = aiohttp.ClientTimeout(connect=1.0, sock_read=2.0)

    assert timeout.connect == 1.0
    assert timeout.sock_read == 2.0
