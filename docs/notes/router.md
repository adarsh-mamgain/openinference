# Router — cost/latency/quality-aware model selection

> Week 3, R1-R2. The routing layer is what turns "I serve one model" into
> "I can answer *which* model serves *this* workload, and why" — the cost/latency
> engineering skill FDE/inference roles pay for.

## What it is

A `router/` package (`inference_server/router/`) that picks which served
model/backend handles each chat request, and why. It shadows the newer
LiteLLM/OpenRouter-style gateways, but is our own, benchmarked, and explainable.

## Files

| File | Role |
|---|---|
| `models.py`   | `Route`, `RouteHints`, `RoutingDecision` dataclasses |
| `health.py`   | per-route success/failure tracking + cooldown |
| `engine.py`   | the `Router`: scoring, selection, fallback ordering |
| `registry.py` | build the route set from server settings |

## How a decision is made

For each request the engine:

1. If the client asked for a specific model (`request.model`) **and** that route
   is available + healthy → it wins immediately (reason: "explicit request").
2. Otherwise every *eligible* route (enabled, available, not on cooldown) is
   scored across three axes:
   - **quality** `route.quality` (0-1)
   - **cost**   `max(0, 1 - cost_per_1k / $5)`
   - **latency** how far a route is under the client's budget (or just fast)
3. Each axis carries a weight that responds to client hints, so a quality-seeking
   client leans quality, a cost-sensitive one leans cheap:

   ```
   score = (w_q*quality + w_l*latency + w_c*cost) / (w_q + w_l + w_c)
   w_q = 0.5 + 0.5*hints.quality
   w_l = 0.5 + 0.5*(latency_budget set)
   w_c = 0.5 + 2.0*hints.cost_sensitivity
   ```

4. The top scorer wins, with the **reason string** and the ordered fallback list
   attached to the `RoutingDecision`. A failed primary route is retried on the
   next healthy fallback (non-streaming requests).

## Wiring into the chat router

- `router_engine` is registered in `routers/chat.py`; every
  `POST /v1/chat/completions` gets a decision before submission.
- The chosen route's id is passed to the scheduler as the job's `model`, and the
  scheduler executes the model bound to that id via
  `Scheduler.register_model(id, model_instance)` — so routing is **real**, not a
  label: a different route means a different serving backend.
- Decisions are logged and stamped on responses:
  - `X-Router-Selected: <route id>` (the route that actually served)
  - `X-Router-Reason: <why>`
- `GET /v1/routes` (behind auth) exposes the routing table + per-route health for
  diagnostics.

## Client steering without breaking OpenAI compat

OpenAI clients send standard bodies; hints ride in optional headers so the wire
format never changes:

```
X-Router-Quality: 0.9              # demand best quality
X-Router-Latency-Budget-Ms: 800    # reject slower routes
X-Router-Cost-Sensitivity: 1.0     # cheapest wins
```

## Failure handling

- Backend failure on the primary route → `report_outcome(id, ok=False)`, retry
  the next healthy fallback (bounded), then a clear error if all fail.
- A route that fails repeatedly trips the health cooldown:
  `error_rate >= 0.5` puts it to sleep for 30s, so future requests skip it
  instead of hammering a broken backend.
- Client disconnects / cancelled streams are *not* counted as backend failures
  (they don't pollute the health score).

## Limits (honest)

- Scoring weights and thresholds are sane defaults, not tuned; a real deployment
  would fit them to production traffic.
- Health is in-process memory — a multi-node fleet would share it via a store.
- Only the local llama.cpp backend executes today; the `PROVIDER` route type
  (remote OpenAI-compatible endpoint) is defined in the model but not yet wired.

## Live check (real model)

```
POST /v1/chat/completions
  -> 200, X-Router-Selected: qwen2.5-0.5b-instruct
     X-Router-Reason: explicit request for 'qwen2.5-0.5b-instruct' and route is healthy
```