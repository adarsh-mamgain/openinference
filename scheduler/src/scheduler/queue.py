"""An asyncio min-heap priority queue with FIFO tie-breaking and cancellation.

This is the scheduling heart: jobs are stored in a binary heap so the highest
priority (lowest numeric value) is always dequeued first. Equal priorities fall
back to arrival order (a monotonic sequence number), giving a clean
priority-then-FIFO policy.

Unlike ``asyncio.PriorityQueue``, this queue supports removing a still-queued
job (needed for the ``cancel`` endpoint). Removal uses a cheap lazy-tombstone:
the item is flagged and skipped when popped, avoiding an O(n) heap rebuild.
"""

import asyncio
import heapq
from dataclasses import dataclass


@dataclass
class QueueItem:
    priority: int
    seq: int
    job_id: str

    def __lt__(self, other: "QueueItem") -> bool:
        # Priority first (lower = higher priority), then arrival order (FIFO).
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.seq < other.seq


class PriorityQueue:
    """Heap-backed async priority queue with FIFO tie-breaks and cancel."""

    def __init__(self, maxsize: int = 0) -> None:
        self._maxsize = maxsize
        self._heap: list[tuple[int, int, QueueItem]] = []
        self._tombstones: set[str] = set()
        self._cond = asyncio.Condition()

    def qsize(self) -> int:
        return len(self._heap) - len(self._tombstones)

    def full(self) -> bool:
        return self._maxsize > 0 and self.qsize() >= self._maxsize

    async def put(self, item: QueueItem) -> None:
        """Add a job to the queue, blocking while full (backpressure)."""
        async with self._cond:
            while self.full():
                await self._cond.wait()
            heapq.heappush(self._heap, (item.priority, item.seq, item))
            self._cond.notify()

    def put_nowait(self, item: QueueItem) -> None:
        """Add a job without blocking; raises QueueFull when over capacity."""
        if self.full():
            raise asyncio.QueueFull
        heapq.heappush(self._heap, (item.priority, item.seq, item))

    async def get(self) -> QueueItem:
        """Pop the highest-priority item, skipping cancelled (tombstoned) ones."""
        async with self._cond:
            while True:
                while self._heap:
                    _, _, item = heapq.heappop(self._heap)
                    if item.job_id in self._tombstones:
                        self._tombstones.discard(item.job_id)
                        continue
                    self._cond.notify()
                    return item
                await self._cond.wait()

    async def cancel(self, job_id: str) -> bool:
        """Mark a queued job for removal. Returns True if it was present."""
        async with self._cond:
            found = any(item.job_id == job_id for _, _, item in self._heap)
            if found:
                self._tombstones.add(job_id)
                # Wake any producer blocked on a full queue now that capacity
                # may have freed up.
                self._cond.notify_all()
            return found
