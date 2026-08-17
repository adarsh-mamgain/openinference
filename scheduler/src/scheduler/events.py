"""An in-process event bus that fans token deltas out to stream subscribers.

A running streaming job publishes text deltas into a per-job async queue; the
SSE endpoint for that job reads from the same queue. A sentinel marks the end
of the stream. All state lives on the asyncio event loop, so no locking is
needed.
"""

import asyncio


class _Sentinel:
    pass


END = _Sentinel()  # pushed after generation finishes


class StreamBus:
    def __init__(self, queue_size: int = 1000) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._queue_size = queue_size

    def create(self, job_id: str) -> None:
        self._queues[job_id] = asyncio.Queue(maxsize=self._queue_size)

    def publish(self, job_id: str, delta: str) -> None:
        """Append a token delta to a job's stream.

        Uses put_nowait so a slow subscriber cannot stall the producing worker;
        if the queue is momentarily full the delta is dropped (the final result
        is still recorded from the collected deltas).
        """
        queue = self._queues.get(job_id)
        if queue is not None:
            try:
                queue.put_nowait(delta)
            except asyncio.QueueFull:
                pass

    def stream_or_none(self, job_id: str) -> "asyncio.Queue | None":
        """Return the job's subscriber queue, or None if it isn't active yet."""
        return self._queues.get(job_id)

    async def close(self, job_id: str) -> None:
        """Push the end sentinel and stop tracking the job's stream."""
        queue = self._queues.pop(job_id, None)
        if queue is not None:
            await queue.put(END)

    async def close_all(self) -> None:
        """Close every open stream (used at shutdown) so no subscriber hangs."""
        for job_id in list(self._queues):
            await self.close(job_id)
