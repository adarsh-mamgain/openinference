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

Each project folder is self-contained with its own README and `uv` setup.

```bash
cd inference-server
uv sync
uv run uvicorn app.main:app --reload
```

## Tooling

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- FastAPI + Uvicorn for the HTTP layer

## License

[MIT](./LICENSE.md)
