from __future__ import annotations

import asyncio

from aiohttp import web

from async_crawler import AsyncCrawler, CrawlerQueue, SemaphoreManager


async def test_crawler_queue_returns_higher_priority_first():
    queue = CrawlerQueue()

    assert queue.add_url("https://example.com/low", priority=1)
    assert queue.add_url("https://example.com/high", priority=10)
    assert not queue.add_url("https://example.com/high", priority=10)

    assert await queue.get_next() == "https://example.com/high"
    queue.mark_processed("https://example.com/high")
    assert await queue.get_next() == "https://example.com/low"
    queue.mark_failed("https://example.com/low", "boom")

    assert queue.get_stats() == {
        "queued": 0,
        "active": 0,
        "processed": 1,
        "failed": 1,
        "total_seen": 2,
    }


async def test_semaphore_manager_limits_per_domain_concurrency():
    manager = SemaphoreManager(global_limit=10, per_domain_limit=1)
    active = 0
    max_active = 0

    async def run_task():
        nonlocal active, max_active
        async with manager.limit_for("https://example.com/page"):
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1

    await asyncio.gather(*(run_task() for _ in range(3)))

    assert max_active == 1
    assert manager.get_stats()["active_tasks"] == 0


async def test_semaphore_manager_releases_global_slot_after_waiting_task_is_cancelled():
    manager = SemaphoreManager(global_limit=2, per_domain_limit=1)
    first_entered = asyncio.Event()
    release_first = asyncio.Event()

    async def hold_first_slot():
        async with manager.limit_for("https://example.com/first"):
            first_entered.set()
            await release_first.wait()

    async def wait_for_same_domain():
        async with manager.limit_for("https://example.com/second"):
            pass

    first_task = asyncio.create_task(hold_first_slot())
    await first_entered.wait()

    waiting_task = asyncio.create_task(wait_for_same_domain())
    await asyncio.sleep(0.01)
    waiting_task.cancel()
    await asyncio.gather(waiting_task, return_exceptions=True)

    release_first.set()
    await first_task

    active = 0
    max_active = 0

    async def run_other_domain(url: str):
        nonlocal active, max_active
        async with manager.limit_for(url):
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1

    await asyncio.gather(
        run_other_domain("https://one.example/page"),
        run_other_domain("https://two.example/page"),
    )

    assert max_active == 2
    assert manager.get_stats()["active_tasks"] == 0


async def test_crawl_respects_max_depth(aiohttp_client):
    async def root(request):
        return web.Response(text='<a href="/level-1">level 1</a>', content_type="text/html")

    async def level_1(request):
        return web.Response(text='<a href="/level-2">level 2</a>', content_type="text/html")

    async def level_2(request):
        return web.Response(text="<p>too deep</p>", content_type="text/html")

    app = web.Application()
    app.router.add_get("/", root)
    app.router.add_get("/level-1", level_1)
    app.router.add_get("/level-2", level_2)
    client = await aiohttp_client(app)

    crawler = AsyncCrawler(max_concurrent=2, max_depth=1)
    try:
        results = await crawler.crawl([str(client.make_url("/"))], same_domain_only=True)
    finally:
        await crawler.close()

    assert str(client.make_url("/")) in results
    assert str(client.make_url("/level-1")) in results
    assert str(client.make_url("/level-2")) not in results


async def test_crawl_filters_urls_and_avoids_duplicates(aiohttp_client):
    async def root(request):
        return web.Response(
            text="""
            <a href="/keep">keep</a>
            <a href="/keep">duplicate</a>
            <a href="/skip">skip</a>
            <a href="https://external.example/page">external</a>
            """,
            content_type="text/html",
        )

    async def keep(request):
        return web.Response(text='<a href="/">back</a>', content_type="text/html")

    async def skip(request):
        return web.Response(text="skip", content_type="text/html")

    app = web.Application()
    app.router.add_get("/", root)
    app.router.add_get("/keep", keep)
    app.router.add_get("/skip", skip)
    client = await aiohttp_client(app)

    crawler = AsyncCrawler(max_concurrent=2, max_depth=2)
    try:
        results = await crawler.crawl(
            [str(client.make_url("/"))],
            same_domain_only=True,
            exclude_patterns=[r"/skip$"],
        )
    finally:
        await crawler.close()

    assert set(results) == {str(client.make_url("/")), str(client.make_url("/keep"))}
    assert len(crawler.visited_urls) == len(set(crawler.visited_urls))
    assert str(client.make_url("/skip")) not in crawler.visited_urls
    assert "https://external.example/page" not in crawler.visited_urls


async def test_crawl_include_patterns(aiohttp_client):
    async def root(request):
        return web.Response(
            text='<a href="/allowed">allowed</a><a href="/blocked">blocked</a>',
            content_type="text/html",
        )

    async def page(request):
        return web.Response(text=request.path, content_type="text/html")

    app = web.Application()
    app.router.add_get("/", root)
    app.router.add_get("/allowed", page)
    app.router.add_get("/blocked", page)
    client = await aiohttp_client(app)

    crawler = AsyncCrawler(max_concurrent=2, max_depth=1)
    try:
        results = await crawler.crawl(
            [str(client.make_url("/"))],
            same_domain_only=True,
            include_patterns=[r"/$", r"/allowed$"],
        )
    finally:
        await crawler.close()

    assert str(client.make_url("/allowed")) in results
    assert str(client.make_url("/blocked")) not in results
