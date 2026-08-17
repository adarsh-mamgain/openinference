# Week 3 — Quantization sweep (Q4_K_M vs Q8_0)

The router's reason-for-being is trading **quality vs latency/cost** across
backends. For a single local GGUF deployment the most honest quantization sweep
is the *same* model served at two precisions — so the only variable is
precision, not architecture. The route registry auto-discovers quantized
siblings of the default model
(`inference_server/router/registry.py`), so a Q8_0 copy next to the default
Q4_K_M becomes a routable backend with no code changes.

## The two backends

| Metric | `qwen2.5-0.5b-instruct` (Q4_K_M) | `qwen2.5-0.5b-instruct-q8_0` |
|--------|--------------------------------:|-----------------------------------:|
| GGUF size (disk) | 491.4M | 675.7M (+37%) |
| Registry quality score | 0.55 | 0.9 |
| Registry latency estimate | 1000ms | 1800ms |

## Measured numbers (streaming, concurrency=1, max_tokens=32, 6 requests)

Run with `benchmarks/src/benchmarks/sweep.py` against the live server (box:
4-core CPU, no GPU, ~3.8 GB RAM).

| Metric | Q4_K_M | Q8_0 | Q8 vs Q4 |
|--------|-------:|-----:|---------:|
| Latency p50 | 2968 ms | 2799 ms | ≈ (noisy) |
| Latency mean | 2778 ms | 3275 ms | +18 % |
| TTFT p50 | 137 ms | 91 ms | −34 % |
| ITL p50 | 74 ms | 79 ms | +7 % |
| tokens/sec | ~10.3 | ~9.8 | −5 % |
| Quality probe accuracy | 100% | 100% | = |

> Numbers are noisy on this box (everything shares 4 cores); the *robust*
> headline is the size + theoretical-quality tradeoff, not millisecond deltas.
> Re-running the sweep (below) is expected to move ITL/tokens by ±20%.

## Empirical quality probe

The quality probe is deliberately crude — a one-shot factual question ran 10
times per model — because the *config-level* quality score (0.55 vs 0.9) is the
thing the router actually optimizes. The empirical probe is a sanity gate: it
must not regress for the "higher" quant. Both quants answer 2+2 correctly at
0.5B scale, so the probe does **not** discriminate here — that is the honest
result, not a claim that Q8 ≈ Q4 in quality.

The scheduler always injects the tool schemas, so a 0.5B model often answers via
a tool call; the probe therefore checks assistant content *and* tool-call
arguments for the accepted token — otherwise it reads ~0% through no fault of
the quant.

## What this buys the router

The sweep is the evidence underneath the router's scoring on this deployment:

1. **Quality is configuration, verified.** `_QUANT_QUALITY` (0.9 Q8 / 0.55 Q4)
   is the knobs the router scores on; the probe confirms the higher-precision
   route doesn't regress the sanity gate.
2. **Cost is real on disk.** Q8 costs +37% memory for a small throughput penalty
   on CPU. Unless a caller asks for quality (via `X-Router-Quality`), the router
   rightly keeps serving Q4.
3. **Latency estimates are order-of-magnitude.** `1000 + quant_index*100` is a
   placeholder; measured ITL shows Q8 ≥ Q4 as expected, which is the direction
   the estimate encodes.

## How to reproduce

```bash
# terminal 1 — server from the inference-server dir (so models/ is found)
cd inference-server
uv run uvicorn inference_server.main:app --port 8141

# terminal 2 — sweep both routes
BENCH_BASE_URL=http://127.0.0.1:8141 \
  BENCH_CONCURRENCIES="1" BENCH_REQUESTS=6 \
  uv run --project benchmarks python -m benchmarks.sweep
```

Env knobs: `BENCH_MODELS` (comma list of route ids), `BENCH_CONCURRENCIES`,
`BENCH_REQUESTS`, `BENCH_QUALITY_PROMPT`, `BENCH_QUALITY_ACCEPT`,
`BENCH_QUALITY_REQUESTS`. The sweep prints per-model latency/TTFT/ITL plus the
quality probe and a summary row including GGUF size.

## Link to the router

- `docs/notes/router.md` — router design, scoring, wiring, limits.
- Week 2 admission-control numbers: `docs/benchmarks/batching-vs-baseline.md`.
- Week 1 baseline: `docs/benchmarks/baseline.md`.