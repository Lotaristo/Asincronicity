from __future__ import annotations

import heapq
import itertools


class CrawlerQueue:
    """Priority queue that tracks pending, active, processed, and failed URLs."""

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, str]] = []
        self._counter = itertools.count()
        self._pending: set[str] = set()
        self._active: set[str] = set()
        self._processed: set[str] = set()
        self._failed: dict[str, str] = {}

    def add_url(self, url: str, priority: int = 0) -> bool:
        if url in self._pending or url in self._active or url in self._processed or url in self._failed:
            return False
        heapq.heappush(self._heap, (-priority, next(self._counter), url))
        self._pending.add(url)
        return True

    async def get_next(self) -> str | None:
        while self._heap:
            _priority, _order, url = heapq.heappop(self._heap)
            if url in self._pending:
                self._pending.remove(url)
                self._active.add(url)
                return url
        return None

    def mark_processed(self, url: str) -> None:
        self._active.discard(url)
        self._pending.discard(url)
        self._processed.add(url)

    def mark_failed(self, url: str, error: str) -> None:
        self._active.discard(url)
        self._pending.discard(url)
        self._failed[url] = error

    def has_pending(self) -> bool:
        return bool(self._pending)

    def get_stats(self) -> dict:
        return {
            "queued": len(self._pending),
            "active": len(self._active),
            "processed": len(self._processed),
            "failed": len(self._failed),
            "total_seen": (
                len(self._pending) + len(self._active) + len(self._processed) + len(self._failed)
            ),
        }

