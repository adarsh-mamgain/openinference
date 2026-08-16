# OpenInference

A portfolio of **AI infrastructure** projects — a self-hosted, OpenAI-compatible
inference API built from scratch, aimed at becoming an **AI Systems / Inference
Engineer** (and FDE-ready for the global market).

> **Read first:** [`ARCHITECTURE.md`](./ARCHITECTURE.md) — how the workspace is
> wired today and the end-state we're building toward.
> [`ROADMAP.md`](./ROADMAP.md) — the 4-week plan.
> [`todo.md`](./todo.md) — the live ordered task list.

## Projects

| # | Project | Status | What you learn |
|---|---------|--------|----------------|
| 1 | [inference-server](./inference-server/) | **Building** (hardening) | HTTP, streaming, async, OpenAI API design, batching, KV cache, metrics |
| 2 | [scheduler](./scheduler/) | Built (hardening) | Priority queues, async workers, backpressure |
| 3 | [scratch-inference](./scratch-inference/) | Reference | BPE tokenizer, KV cache, transformer forward pass (numpy) |
| 4 | router | Planned (Week 3) | Cost/latency-aware routing, fallback, providers |
| 5 | evals | Deferred | Measurement, error analysis |

## Getting started

The repo is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
whose members are `inference-server`, `scheduler`, and `scratch-inference`.
`scheduler` is an **internal library**: `inference-server` imports it as its
request queue, so `inference-server` is the only service you run.

```bash
uv sync --all-packages   # from the repo root; installs all members

# Run the single inference-server (chat flows through the internal scheduler)
cd inference-server
uv run uvicorn inference_server.main:app --reload
```

Each project folder also has its own README and `uv` setup for standalone use.

## Tooling

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- FastAPI + Uvicorn for the HTTP layer
- llama-cpp-python (CPU) for local inference; numpy/safetensors for the
  from-scratch reference

## License

[MIT](./LICENSE.md)
