# benchmarks

A concurrency-ramp benchmark harness for the
[inference-server](../inference-server/). It drives the running server with an
increasing number of concurrent clients and reports the numbers that matter for
inference engineering:

* **Latency** — end-to-end request time (p50 / p95 / p99 / mean)
* **TTFT** — time-to-first-token (streaming)
* **ITL** — inter-token latency, i.e. token cadence (streaming)
* **Throughput** — requests/sec and tokens/sec
* **Server metrics** — the server's own `GET /metrics` view

## Usage

```bash
# 1. start the server (terminal 1)
cd ../inference-server
uv run uvicorn inference_server.main:app --port 8000

# 2. run the ramp (terminal 2)
uv run --project benchmarks python -m benchmarks.run
```

Tunable via environment variables:

| Variable | Default | Meaning |
|----------|---------|---------|
| `BENCH_BASE_URL` | `http://localhost:8000` | Server base URL |
| `BENCH_API_KEY` | `dev-key` | API key |
| `BENCH_MODEL` | `qwen2.5-0.5b-instruct` | Model to exercise |
| `BENCH_PROMPT` | (a short-story prompt) | Prompt text |
| `BENCH_CONCURRENCIES` | `1,2,4,8` | Concurrency levels to ramp through |
| `BENCH_REQUESTS` | `10` | Total requests per concurrency level |
| `BENCH_MAX_TOKENS` | `48` | Max completion tokens |
| `BENCH_STREAM` | `1` | `1` = streaming, `0` = non-streaming |
| `BENCH_SETTLE_SECONDS` | `2` | Pause between concurrency levels so the server recovers |

Example:

```bash
BENCH_CONCURRENCIES="1,4,8,16" BENCH_REQUESTS=20 \
  BENCH_MAX_TOKENS=64 BENCH_SETTLE_SECONDS=3 \
  uv run --project benchmarks python -m benchmarks.run
```

## Interpreting the output

A healthy streaming server shows TTFT and inter-token latency relatively flat
as concurrency rises; if TTFT climbs sharply or inter-token latency spikes,
the model/box is saturated. If requests start erroring under load, note it —
erroring is itself a valid benchmark result (the server is refusing/dropping
connections because it can't keep up).

> With the current single-worker CPU server, throughput collapses at even low
> concurrency: requests that arrive while a long stream is in progress stall or
> fail to connect. That's exactly the problem continuous batching (Week 2) is
> meant to fix — use this harness to prove the before/after.
