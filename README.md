# AI Infrastructure Portfolio

A learning portfolio of AI infrastructure projects, built from scratch and kept
deliberately simple so the fundamentals are clear.

## Projects

| # | Project | Status | What you learn |
|---|---------|--------|----------------|
| 1 | [inference-server](./inference-server/) | Complete | HTTP, streaming, async, OpenAI API design |
| 2 | [scheduler](./scheduler/) | Complete | Queues, priorities, async workers |
| 3 | kv-cache | — | Caching, eviction, memory |
| 4 | gpu-autoscaler | — | Scaling, metrics, backpressure |
| 5 | benchmark-suite | — | Latency, throughput, load testing |
| 6 | rag-system | — | Retrieval, embeddings, pipelines |
| 7 | vector-db | — | Indexing, ANN search |
| 8 | tokenizer | — | BPE, tokenization |
| 9 | distributed-serving | — | Multi-node serving, sharding |
| 10 | monitoring | — | Metrics, dashboards, alerting |
| 11 | blogs | — | Writing and documentation |

## Getting started

The repo is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
whose members are `inference-server` and `scheduler`. The scheduler depends on
the inference-server and runs jobs against its real local model.

```bash
uv sync --all-packages   # from the repo root; installs all members

# Run each app in its own terminal
uv run --package inference-server uvicorn inference_server.main:app --port 8000
uv run --package scheduler uvicorn scheduler.main:app --port 8001
```

Each project folder also has its own README and `uv` setup for standalone use.

## Tooling

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- FastAPI + Uvicorn for the HTTP layer

## License

[MIT](./LICENSE.md)
