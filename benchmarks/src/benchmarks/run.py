#!/usr/bin/env python3
"""Concurrency-ramp benchmark for the inference-server.

Drives the running server (BaseURL = ``BENCH_BASE_URL``, key = ``BENCH_API_KEY``)
with an increasing number of concurrent clients and reports:

* **Latency** — end-to-end request time (p50 / p95 / p99 / mean)
* **TTFT** — time-to-first-token for streaming requests
* **ITL** — inter-token latency (token cadence) for streaming requests
* **Throughput** — requests/sec and tokens/sec
* **Server metrics** — the server's own view from ``GET /metrics``

Usage:

    # start the server first
    uv run uvicorn inference_server.main:app --port 8000

    # then run the ramp (default: 4 concurrency levels x 10 requests each)
    uv run python benchmarks/run.py

    # tune it
    BENCH_BASE_URL=http://localhost:8000 BENCH_CONCURRENCIES="1,2,4,8" \
      BENCH_REQUESTS=10 uv run python benchmarks/run.py

Exit code is 0 on success. All timings are seconds unless noted (ms suffix).
"""

import asyncio
import json
import os
import statistics
import time

try:
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

BASE_URL = os.environ.get("BENCH_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("BENCH_API_KEY", "dev-key")
MODEL = os.environ.get("BENCH_MODEL", "qwen2.5-0.5b-instruct")
PROMPT = os.environ.get(
    "BENCH_PROMPT",
    "Write a short story about a robot that learns to paint in exactly five sentences.",
)
CONCURRENCIES = [
    int(x) for x in os.environ.get("BENCH_CONCURRENCIES", "1,2,4,8").split(",")
]
REQUESTS = int(os.environ.get("BENCH_REQUESTS", "10"))
MAX_TOKENS = int(os.environ.get("BENCH_MAX_TOKENS", "48"))
STREAM = os.environ.get("BENCH_STREAM", "1") == "1"
SETTLE_SECONDS = float(os.environ.get("BENCH_SETTLE_SECONDS", "2"))

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
BODY = {
    "model": MODEL,
    "messages": [{"role": "user", "content": PROMPT}],
    "max_tokens": MAX_TOKENS,
    "stream": STREAM,
}


def _fmt(p: float | None, suffix: str = "ms") -> str:
    return f"{(p * 1000):.2f}{suffix}" if p is not None else "n/a"


async def _one(client: httpx.AsyncClient) -> dict:
    """Send one request and return latency / TTFT / ITL / token counts.

    Reads the SSE body as raw bytes and stops as soon as the terminal
    ``data: [DONE]`` frame is seen. Reading via ``aiter_raw`` (rather than line
    decoding) avoids the reader asking for more body after the server closes the
    chunked stream.

    Network failures under heavy load are caught and surfaced as ``error``
    samples so one stalled request doesn't abort the whole ramp.
    """
    start = time.perf_counter()
    ttft = None
    first = True
    deltas: list[str] = []
    buffer = ""
    try:
        async with client.stream("POST", "/v1/chat/completions", json=BODY) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                return {"error": resp.status_code, "detail": body[:200].decode()}
            async for raw in resp.aiter_raw():
                buffer += raw.decode("utf-8", errors="ignore")
                # Process any complete SSE lines, keeping a possible trailing
                # partial line in the buffer.
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        return _finalize(start, first, ttft, deltas)
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content")
                    if delta:
                        if first:
                            ttft = time.perf_counter() - start
                            first = False
                        deltas.append(delta)
    except httpx.RemoteProtocolError:
        # Server closed the chunked stream right after [DONE]; report what we got.
        return _finalize(start, first, ttft, deltas)
    except httpx.HTTPError as exc:
        # Connect/read/timeout errors under load — record as an error sample.
        return {"error": type(exc).__name__, "detail": str(exc)[:200]}

    return _finalize(start, first, ttft, deltas)


def _finalize(start, first: bool, ttft: float | None, deltas: list[str]) -> dict:
    total = time.perf_counter() - start
    itl = None
    if len(deltas) > 1:
        itl = (total - (ttft or 0)) / (len(deltas) - 1)
    return {
        "latency": total,
        "ttft": ttft,
        "itl": itl,
        "deltas": len(deltas),
    }


async def _worker(client: httpx.AsyncClient, n: int, results: list) -> None:
    for _ in range(n):
        results.append(await _one(client))


async def _ramp(concurrency: int, requests: int) -> list:
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers=HEADERS,
        timeout=httpx.Timeout(120.0),
        # Streaming requests stop reading at [DONE], leaving the body undrained;
        # avoid reusing a poisoned keep-alive connection between requests.
        limits=httpx.Limits(max_connections=128, max_keepalive_connections=0),
    ) as client:
        results: list = []
        per_worker = max(1, requests // concurrency)
        tasks = [_worker(client, per_worker, results) for _ in range(concurrency)]
        await asyncio.gather(*tasks)
    return results


def _agg(results: list, key: str) -> dict:
    vals = sorted((r[key] for r in results if r.get(key) is not None))
    if not vals:
        return {"count": 0}
    return {
        "count": len(vals),
        "min": _fmt(vals[0]),
        "p50": _fmt(vals[len(vals) // 2]),
        "p95": _fmt(vals[int(len(vals) * 0.95) - 1]),
        "p99": _fmt(vals[int(len(vals) * 0.99) - 1]),
        "max": _fmt(vals[-1]),
        "mean": _fmt(statistics.mean(vals)),
    }


def _report(concurrency: int, results: list) -> None:
    ok = [r for r in results if "error" not in r]
    errs = [r for r in results if "error" in r]
    total_deltas = sum(r.get("deltas", 0) for r in ok)
    wall = sum(r.get("latency", 0) for r in ok)
    print(f"\n--- concurrency={concurrency}  requests={len(results)} "
          f"streaming={STREAM} ---")
    if errs:
        print(f"  errors: {len(errs)} (first: {errs[0]})")
    if not ok:
        return
    print(f"  latency   {_agg(ok, 'latency')}")
    print(f"  ttft      {_agg(ok, 'ttft')}   (stream only)")
    print(f"  inter-tok {_agg(ok, 'itl')}   (stream only)")
    print(f"  deltas emitted: {total_deltas}  → ~{total_deltas / wall:.2f} tokens/sec")


async def _fetch_server_metrics(client: httpx.AsyncClient) -> dict:
    r = await client.get("/metrics")
    return r.json() if r.status_code == 200 else {"error": r.status_code}


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS) as client:
        try:
            health = await client.get("/health")
            health.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            print(f"Cannot reach server at {BASE_URL} ({exc}). "
                  f"Start it first, then re-run.")
            return 1

        print(f"Target: {BASE_URL}  model={MODEL}  requests/level={REQUESTS} "
              f"max_tokens={MAX_TOKENS}  stream={STREAM}")
        for c in CONCURRENCIES:
            results = await _ramp(c, REQUESTS)
            _report(c, results)
            if SETTLE_SECONDS:
                print(f"  settling {SETTLE_SECONDS}s before next level...")
                await asyncio.sleep(SETTLE_SECONDS)

        print("\n--- server metrics (GET /metrics) ---")
        try:
            print(json.dumps(await _fetch_server_metrics(client), indent=2))
        except httpx.HTTPError as exc:
            print(f"  (server unreachable for metrics: {type(exc).__name__})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
