#!/usr/bin/env python3
"""Quantization sweep: benchmark the same model served at different GGUFs.

The route registry auto-registers quantized siblings of the default model (e.g.
``qwen2.5-0.5b-instruct-q8_0`` next to the default ``...-q4_k_m``). This script
runs the same workload against each quantized route and reports the
quality/latency/cost tradeoff:

* **Latency / TTFT / ITL** — same numbers the concurrency ramp reports
* **Quality** — a cheap task-level probe (e.g. a factual win/lose answer), so
  "0.9 quality" isn't just a number on a config; it's a measured accuracy
* **Size** — GGUF file size on disk (proxy for memory)

Usage (server must be running; sweeps one concurrency level per model):

    BENCH_BASE_URL=http://localhost:8000 \
      BENCH_CONCURRENCIES="2" BENCH_REQUESTS=15 \
      BENCH_MODELS="qwen2.5-0.5b-instruct,qwen2.5-0.5b-instruct-q8_0" \
      uv run --project benchmarks python -m benchmarks.sweep
"""

import asyncio
import json
import os
import statistics
import time
from pathlib import Path

from benchmarks.run import (
    BASE_URL,
    HEADERS,
    MAX_TOKENS,
    PROMPT,
    REQUESTS,
    STREAM,
    _agg,
    _one,
    _report,
)

try:
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

# Models to compare. Defaults to probing the server's route registry for quants.
MODELS = [
    m.strip()
    for m in os.environ.get(
        "BENCH_MODELS",
        "qwen2.5-0.5b-instruct,qwen2.5-0.5b-instruct-q8_0",
    ).split(",")
    if m.strip()
]
CONCURRENCIES = [
    int(x) for x in os.environ.get("BENCH_CONCURRENCIES", "1,2").split(",")
]
SETTLE_SECONDS = float(os.environ.get("BENCH_SETTLE_SECONDS", "3"))

# A cheap factual probe: ask for a one-word answer the base model gets right.
QUALITY_PROMPT = os.environ.get(
    "BENCH_QUALITY_PROMPT",
    "What is 2 + 2? Answer with only the number.",
)
QUALITY_ACCEPT = os.environ.get("BENCH_QUALITY_ACCEPT", "4")
QUALITY_REQUESTS = int(os.environ.get("BENCH_QUALITY_REQUESTS", "20"))


def _gguf_size(route_id: str) -> str | None:
    """Return the on-disk GGUF size for a route id (best effort).

    Uses the same registry the server builds routes from, mapping the route id
    back to its ``model_path`` and reporting the file size. ``None`` when the
    models directory isn't reachable from this working directory (remote server
    or different CWD) — the size axis is then reported as unknown.
    """
    try:
        from inference_server.router.registry import build_routes
        from pathlib import Path as P
        import inference_server

        # server root: the dir that contains models/. For the src layout the
        # package file sits at <root>/src/<pkg>/__init__.py (parents[2]); for a
        # flat install at <root>/<pkg>/__init__.py (parents[1]) that is also the
        # server root. Try the models dir up the tree from the package file.
        pkg_dir = P(inference_server.__file__).resolve().parent
        server_root = None
        for ancestor in (pkg_dir, *pkg_dir.parents):
            if (ancestor / "models").is_dir():
                server_root = ancestor
                break
        if server_root is None:
            return None
        routes = build_routes(extra_models_dir=str(server_root / "models"))
        for route in routes:
            if route.id == route_id and route.model_path:
                path = P(route.model_path)
                if not path.is_absolute():
                    path = server_root / path
                if path.is_file():
                    return f"{path.stat().st_size / 1e6:.1f}M"
        return None
    except Exception:  # noqa: BLE001 — sweep must still run without local registry
        return None


async def _quality(client: httpx.AsyncClient, model: str) -> dict:
    """Run a factual probe N times; return accuracy + samples.

    The server's scheduler always wires in tool schemas, so a 0.5B model often
    answers via a tool call rather than plain assistant content. We therefore
    check both the content field and any tool-call arguments for the accepting
    token — otherwise the probe reads ~0% through no fault of the quantization.
    """
    body_template = {
        "messages": [{"role": "user", "content": QUALITY_PROMPT}],
        "max_tokens": 32,
        "stream": False,
    }
    ok = 0
    errors = 0
    samples: list[str] = []
    for _ in range(QUALITY_REQUESTS):
        body = {**body_template, "model": model}
        try:
            r = await client.post("/v1/chat/completions", json=body)
            if r.status_code != 200:
                errors += 1
                continue
            message = (r.json().get("choices") or [{}])[0].get("message", {})
            answer = message.get("content") or ""
            for call in message.get("tool_calls") or []:
                answer += " " + (call.get("function", {}).get("arguments") or "")
            samples.append(answer)
            if QUALITY_ACCEPT in answer:
                ok += 1
        except httpx.HTTPError:
            errors += 1
    return {
        "accuracy": ok / QUALITY_REQUESTS if QUALITY_REQUESTS else 0.0,
        "errors": errors,
        "samples": samples[:3],
    }


async def _sweep_model(client: httpx.AsyncClient, model: str) -> dict:
    print(f"\n=== model: {model} ===", flush=True)
    for concurrency in CONCURRENCIES:
        body_override = {"model": model}
        results: list = []
        per_worker = max(1, REQUESTS // concurrency)
        tasks = []
        for _ in range(concurrency):
            async def _w():
                for _i in range(per_worker):
                    results.append(await _one(client, override=body_override))
            tasks.append(_w())
        await asyncio.gather(*tasks)
        _report(concurrency, results)
        if SETTLE_SECONDS:
            print(f"  settling {SETTLE_SECONDS}s...", flush=True)
            await asyncio.sleep(SETTLE_SECONDS)

    ok = None
    ok = await _quality(client, model)
    print(f"  quality probe accuracy: {ok['accuracy']:.0%} "
          f"(errors={ok['errors']}, accepts={int(ok['accuracy'] * QUALITY_REQUESTS)})")
    return ok


async def main() -> int:
    print(f"Quantization sweep: {MODELS}\nTarget: {BASE_URL}  stream={STREAM}")
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers=HEADERS,
        timeout=httpx.Timeout(120.0),
        limits=httpx.Limits(max_connections=128, max_keepalive_connections=0),
    ) as client:
        try:
            h = await client.get("/health")
            h.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            print(f"Cannot reach server at {BASE_URL} ({exc}). Start it first.")
            return 1
        quality_by_model = {}
        for model in MODELS:
            quality_by_model[model] = await _sweep_model(client, model)

    print("\n=== sweep summary ===")
    rows = []
    for model in MODELS:
        q = quality_by_model[model]
        rows.append(
            {
                "model": model,
                "gguf_size": _gguf_size(model),
                "quality_accuracy": q["accuracy"],
                "errors": q["errors"],
            }
        )
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))