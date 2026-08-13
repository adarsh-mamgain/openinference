"""A priority-queue scheduler library used inside the inference-server.

Clients (the inference-server chat router) submit chat-completion requests as
jobs. A bounded pool of async workers drains the queue and runs the real model
from ``inference_server.llm``, honouring priority-then-FIFO ordering, bounded
concurrency and backpressure.

Library API (no HTTP surface — this is consumed by the inference-server):

    scheduler = Scheduler(num_workers=2)
    await scheduler.start()
    job = await scheduler.submit_chat(messages=[...], max_tokens=32)
    await job.done.wait()
    text = job.result            # non-streaming

    job = await scheduler.submit_chat(messages=[...], stream=True)
    async for delta in scheduler.subscribe_stream(job.id):
        ...                       # streaming
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator

from inference_server.llm import model
from inference_server.schemas import Message as ChatMessage
from inference_server.tools import (
    TOOL_SCHEMAS,
    parse_text_tool_call,
    run_tool,
    tool_result_message,
)

from scheduler.config import settings
from scheduler.events import END, StreamBus
from scheduler.queue import PriorityQueue, QueueItem
from scheduler.schemas import Job, JobStatus, JobSubmitRequest
from scheduler.store import JobStore

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOKENS = 64
MAX_TOOL_TURNS = 4


class Scheduler:
    def __init__(
        self,
        num_workers: int = settings.num_workers,
        max_queue_size: int = settings.max_queue_size,
    ) -> None:
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self.store = JobStore()
        self.queue = PriorityQueue(maxsize=self.max_queue_size)
        self.bus = StreamBus()
        self.in_flight = 0
        self._seq = 0
        self._workers: list[asyncio.Task] = []

    async def start(self) -> None:
        """Spawn the worker tasks. Idempotent."""
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._worker(i), name=f"worker-{i}")
            for i in range(self.num_workers)
        ]

    async def stop(self) -> None:
        """Cancel all workers and wait for them to finish."""
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    async def submit_chat(
        self,
        messages: list[dict],
        *,
        priority: int = 0,
        model_name: str = "qwen2.5-0.5b-instruct",
        max_tokens: int | None = None,
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> Job:
        """Create and enqueue a chat-completion job; returns immediately."""
        request = JobSubmitRequest(
            messages=[
                ChatMessage(**m) if isinstance(m, dict) else m for m in messages
            ],
            priority=priority,
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            stream=stream,
        )
        job = self.store.create(request)
        seq = self._seq
        self._seq += 1
        await self.queue.put(QueueItem(priority=job.priority, seq=seq, job_id=job.id))
        return job

    def job(self, job_id: str) -> Job | None:
        return self.store.get(job_id)

    async def cancel(self, job_id: str) -> Job | None:
        """Cancel a job if it is still queued. In-flight jobs cannot be aborted.

        Returns the cancelled :class:`Job`, or ``None`` if the job wasn't queued
        (e.g. already running or finished).
        """
        if await self.queue.cancel(job_id):
            job = self.store.get(job_id)
            if job is not None:
                self.store.set_status(job_id, JobStatus.CANCELLED)
                self.store.archive(job)
                return job
        return None

    async def subscribe_stream(self, job_id: str) -> AsyncIterator[str]:
        """Yield token deltas for a streaming job until it finishes."""
        queue = await self._wait_for_stream(job_id)
        if queue is None:
            return
        ended = False
        while True:
            try:
                item = await queue.get()
            except asyncio.CancelledError:
                raise
            if item is END:
                ended = True
                break
            yield item
        del ended  # stream ends when its sentinel arrives

    async def _wait_for_stream(self, job_id: str) -> "asyncio.Queue | None":
        """Return the job's stream queue once the worker creates it."""
        for _ in range(200):  # ~5s budget to reach RUNNING + create the stream
            queue = self.bus.stream_or_none(job_id)
            if queue is not None:
                return queue
            job = self.store.get(job_id)
            if job is None or _is_terminal(job.status):
                return None
            await asyncio.sleep(0.025)
        return None

    async def _worker(self, index: int) -> None:
        """Process jobs from the priority queue until cancelled."""
        logger.info("worker %d started", index)
        try:
            while True:
                item = await self.queue.get()
                job = self.store.get(item.job_id)
                if job is None or _is_terminal(job.status):
                    continue
                await self._run(job)
        except asyncio.CancelledError:
            logger.info("worker %d stopped", index)
            raise

    async def _run(self, job: Job) -> None:
        self.in_flight += 1
        self.store.set_status(job.id, JobStatus.RUNNING)
        try:
            await self._execute(job)
            self.store.set_status(job.id, JobStatus.COMPLETED)
        except Exception as exc:  # noqa: BLE001 - surface per-job failures
            logger.exception("job %s failed", job.id)
            self.store.set_result(job.id, f"error: {exc}")
            self.store.set_status(job.id, JobStatus.FAILED)
            if job.stream:
                await self.bus.close(job.id)
        finally:
            self.in_flight -= 1
            self.store.archive(job)

    async def _execute(self, job: Job) -> None:
        messages: list[ChatMessage] = job.messages
        max_tokens = job.max_tokens or DEFAULT_MAX_TOKENS

        if job.stream:
            await self._stream(job, messages, max_tokens)
            return

        content = await asyncio.to_thread(
            self._generate_with_tools, messages, max_tokens, job.tools
        )
        self.store.set_result(job.id, content or "")

    def _generate_with_tools(
        self, messages: list[ChatMessage], max_tokens: int, tools: list[dict] | None
    ) -> str:
        """Model-driven tool-calling loop. Returns the final assistant content."""
        tools = tools or TOOL_SCHEMAS
        for _ in range(MAX_TOOL_TURNS):
            content, tool_calls, _finish = model.generate(messages, max_tokens, tools)
            if tool_calls:
                for call in tool_calls:
                    result = run_tool(call)
                    messages.append(
                        ChatMessage(role="assistant", content=None, tool_calls=[call])
                    )
                    messages.append(tool_result_message(call, result))
                continue
            text_call = parse_text_tool_call(content or "")
            if text_call is not None:
                result = run_tool(text_call)
                messages.append(ChatMessage(role="assistant", content=content, tool_calls=[text_call]))
                messages.append(tool_result_message(text_call, result))
                continue
            return content or ""
        raise RuntimeError("Tool-calling loop exceeded its turn budget")

    async def _stream(self, job: Job, messages: list[ChatMessage], max_tokens: int) -> None:
        """Generate token deltas and fan them out to the job's subscribers."""
        self.bus.create(job.id)
        chunks: Iterator[str] = model.stream(messages, max_tokens, job.tools)
        collected: list[str] = []
        try:
            while True:
                text = await asyncio.to_thread(_next_or_none, chunks)
                if text is None:
                    break
                collected.append(text)
                self.bus.publish(job.id, text)
        finally:
            await self.bus.close(job.id)
            self.store.set_result(job.id, "".join(collected))

    @property
    def queue_size(self) -> int:
        return self.queue.qsize()

    def health(self) -> dict:
        return {
            "status": "ok",
            "queue_size": self.queue_size,
            "in_flight": self.in_flight,
            "workers": self.num_workers,
        }

    async def __aenter__(self) -> "Scheduler":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()


def _next_or_none(iterator: Iterator[str]) -> str | None:
    """Advance a blocking iterator, returning None on exhaustion (safe across
    the asyncio.to_thread boundary, where StopIteration cannot propagate)."""
    try:
        return next(iterator)
    except StopIteration:
        return None


def _is_terminal(status: JobStatus) -> bool:
    return status in (
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    )


# Default singleton that the inference-server starts on its own lifespan.
scheduler = Scheduler()
