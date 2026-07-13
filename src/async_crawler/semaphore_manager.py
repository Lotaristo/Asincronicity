from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from urllib.parse import urlsplit


class SemaphoreManager:
    """Manage global and per-domain concurrency limits."""

    def __init__(self, global_limit: int, per_domain_limit: int = 2) -> None:
        if global_limit < 1:
            raise ValueError("global_limit must be at least 1")
        if per_domain_limit < 1:
            raise ValueError("per_domain_limit must be at least 1")

        self._global_semaphore = asyncio.Semaphore(global_limit)
        self._per_domain_limit = per_domain_limit
        self._domain_semaphores: defaultdict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(per_domain_limit)
        )
        self._lock = asyncio.Lock()
        self._active_tasks = 0
        self._active_by_domain: defaultdict[str, int] = defaultdict(int)

    @asynccontextmanager
    async def limit_for(self, url: str):
        domain = urlsplit(url).netloc.lower()
        domain_semaphore = self._domain_semaphores[domain]
        global_acquired = False
        domain_acquired = False
        stats_counted = False

        try:
            await self._global_semaphore.acquire()
            global_acquired = True
            await domain_semaphore.acquire()
            domain_acquired = True
            async with self._lock:
                self._active_tasks += 1
                self._active_by_domain[domain] += 1
                stats_counted = True
            yield
        finally:
            if stats_counted:
                async with self._lock:
                    self._active_tasks -= 1
                    self._active_by_domain[domain] -= 1
            if domain_acquired:
                domain_semaphore.release()
            if global_acquired:
                self._global_semaphore.release()

    def get_stats(self) -> dict:
        return {
            "active_tasks": self._active_tasks,
            "active_by_domain": dict(self._active_by_domain),
            "per_domain_limit": self._per_domain_limit,
        }
