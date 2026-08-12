"""Landing page for the inference server.

Serves a single static-ish HTML page at `/` that explains the product and
has one call-to-action pointing at the interactive OpenAPI docs (`/docs`).
The page is rendered server-side so it can reflect live facts like which
models are loaded.
"""

from html import escape

from fastapi.responses import HTMLResponse

from inference_server.config import settings
from inference_server.llm import embedding_model, model


def _status(model_obj) -> str:
    return "loaded" if model_obj.available else "not loaded"


def _model_badge(path: str, status: str) -> str:
    dot = "ok" if status == "loaded" else "missing"
    tag = "loaded" if status == "loaded" else "not-loaded"
    return (
        f'<span class="model"><span class="dot {dot}"></span>'
        f"{escape(path)}<span class=\"tag {tag}\">{status}</span></span>"
    )


def landing_page() -> HTMLResponse:
    app_name = escape(settings.app_name)
    chat_status = _status(model)
    embed_status = _status(embedding_model)
    chat_badge = _model_badge(settings.model_path, chat_status)
    embed_badge = _model_badge(settings.embedding_model_path, embed_status)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__APP_NAME__ — OpenAI-compatible local inference API</title>
<style>
  :root {
    --bg: #0b0f1a;
    --panel: rgba(255,255,255,0.03);
    --panel-border: rgba(255,255,255,0.08);
    --text: #e6ecf7;
    --muted: #8b97ad;
    --accent: #6c8cff;
    --accent-2: #8f6cff;
    --ok: #3ecf8e;
    --missing: #f05a5a;
    --radius: 18px;
    --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background:
      radial-gradient(1000px 500px at 80% -10%, rgba(108,140,255,0.16), transparent 60%),
      radial-gradient(800px 420px at 10% -5%, rgba(143,108,255,0.14), transparent 55%),
      var(--bg);
    color: var(--text);
    line-height: 1.55;
    display: flex;
    flex-direction: column;
  }
  .wrap { width: min(1080px, 92%); margin: 0 auto; padding: 64px 0 80px; flex: 1; }

  nav { display: flex; align-items: center; justify-content: space-between; padding: 22px 0; }
  .brand { display: flex; align-items: center; gap: 12px; font-weight: 700; letter-spacing: .3px; }
  .logo {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    display: grid; place-items: center; font-size: 18px; box-shadow: 0 8px 24px rgba(108,140,255,.35);
  }
  nav .version { font: 12px var(--mono); color: var(--muted); }

  .eyebrow {
    display: inline-flex; align-items: center; gap: 8px;
    font: 12px/1 var(--mono); color: var(--accent);
    background: rgba(108,140,255,0.1); border: 1px solid rgba(108,140,255,0.25);
    padding: 8px 12px; border-radius: 999px; letter-spacing: .4px;
  }
  h1 {
    font-size: clamp(36px, 6vw, 60px); line-height: 1.05; letter-spacing: -1.5px;
    margin: 22px 0 18px; font-weight: 800;
  }
  h1 .grad {
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .lede { font-size: clamp(16px, 2.2vw, 20px); color: var(--muted); max-width: 640px; }
  .cta-row { display: flex; align-items: center; gap: 16px; margin-top: 34px; flex-wrap: wrap; }
  .cta {
    display: inline-flex; align-items: center; gap: 10px;
    text-decoration: none; font-weight: 600; font-size: 16px;
    padding: 15px 28px; border-radius: 12px;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    color: #fff; box-shadow: 0 12px 34px rgba(108,140,255,.35);
    transition: transform .15s ease, box-shadow .15s ease;
  }
  .cta:hover { transform: translateY(-2px); box-shadow: 0 16px 40px rgba(108,140,255,.45); }
  .cta .arrow { font-size: 18px; }
  .hint { font: 13px var(--mono); color: var(--muted); }

  .status-card {
    margin: 46px 0 60px; padding: 20px 22px;
    background: var(--panel); border: 1px solid var(--panel-border); border-radius: var(--radius);
    display: grid; gap: 14px;
  }
  .status-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .status-label { font: 12px var(--mono); color: var(--muted); min-width: 118px; text-transform: uppercase; letter-spacing: .6px; }
  .model {
    display: inline-flex; align-items: center; gap: 8px;
    font: 13px var(--mono); color: var(--text);
    background: rgba(255,255,255,0.05); border: 1px solid var(--panel-border);
    padding: 8px 12px; border-radius: 8px;
  }
  .dot { width: 9px; height: 9px; border-radius: 50%; }
  .dot.ok { background: var(--ok); box-shadow: 0 0 10px var(--ok); }
  .dot.missing { background: var(--missing); box-shadow: 0 0 10px var(--missing); }
  .tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; text-transform: capitalize; }
  .tag.loaded { background: rgba(62,207,142,.15); color: var(--ok); }
  .tag.not-loaded { background: rgba(240,90,90,.15); color: var(--missing); }

  .pipeline { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0; align-items: center; margin-bottom: 64px; }
  .stage { background: var(--panel); border: 1px solid var(--panel-border); border-radius: 14px; padding: 18px 12px; text-align: center; }
  .stage .icon { font-size: 26px; }
  .stage .name { font-weight: 700; font-size: 14px; margin-top: 8px; }
  .stage .desc { font: 11px var(--mono); color: var(--muted); margin-top: 4px; }
  .pipe-arrow { color: var(--accent); text-align: center; font-size: 22px; padding: 0 4px; }

  section h2 { font-size: 26px; font-weight: 800; letter-spacing: -.5px; margin-bottom: 8px; }
  section .sub { color: var(--muted); margin-bottom: 26px; max-width: 620px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
  .card { background: var(--panel); border: 1px solid var(--panel-border); border-radius: var(--radius); padding: 22px; transition: border-color .15s ease, transform .15s ease; }
  .card:hover { border-color: rgba(108,140,255,.4); transform: translateY(-2px); }
  .card .method { font-weight: 700; font-size: 15px; font-family: var(--mono); display: flex; align-items: center; gap: 10px; }
  .card .method .verb { font-size: 11px; padding: 3px 8px; border-radius: 6px; letter-spacing: .5px; }
  .verb.post { background: rgba(62,207,158,.16); color: var(--ok); }
  .verb.get { background: rgba(108,140,255,.16); color: var(--accent); }
  .card .desc { color: var(--muted); font-size: 14px; margin-top: 10px; }
  .card .tagline { font: 12px var(--mono); color: var(--accent); margin-top: 12px; display: block; }
  .card code { font-family: var(--mono); color: var(--text); }

  .feature .ico { font-size: 22px; }
  .feature .t { font-weight: 700; margin: 10px 0 6px; }
  .feature .d { color: var(--muted); font-size: 13.5px; }

  footer { border-top: 1px solid var(--panel-border); padding: 26px 0; margin-top: 70px; color: var(--muted); font-size: 13px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
  footer code { font-family: var(--mono); color: var(--text); }
  @media (max-width: 760px) {
    .pipeline { grid-template-columns: 1fr; }
    .pipe-arrow { transform: rotate(90deg); padding: 6px 0; }
  }
</style>
</head>
<body>
<div class="wrap">

  <nav>
    <div class="brand"><span class="logo">⚡</span> __APP_NAME__</div>
    <span class="version">v0.1.0 · OpenAI-compatible</span>
  </nav>

  <header>
    <span class="eyebrow">● local-first · self-hosted · CPU-only</span>
    <h1>Run an <span class="grad">OpenAI-compatible</span><br />inference API on your own hardware.</h1>
    <p class="lede">
      A production-shaped FastAPI service that speaks the OpenAI wire format —
      chat completions, streaming, tool calling and embeddings — powered by real
      local models. No cloud, no keys, no GPU required.
    </p>
    <div class="cta-row">
      <a class="cta" href="/docs">Explore the interactive API docs <span class="arrow">→</span></a>
      <span class="hint">/docs · OpenAPI · try every endpoint live</span>
    </div>
  </header>

  <div class="status-card">
    <div class="status-row">
      <span class="status-label">Models</span>
      __CHAT_BADGE__
      __EMBED_BADGE__
    </div>
    <div class="status-row">
      <span class="status-label">Backend</span>
      <span class="model"><span class="dot ok"></span>local llama.cpp</span>
      <span class="model">ctx __CTX__</span>
      <span class="model">threads __THREADS__</span>
    </div>
  </div>

  <section class="pipeline">
    <div class="stage"><div class="icon">🐚</div><div class="name">Client</div><div class="desc">any OpenAI SDK</div></div>
    <div class="pipe-arrow">→</div>
    <div class="stage"><div class="icon">⚡</div><div class="name">FastAPI</div><div class="desc">auth · rate-limit</div></div>
    <div class="pipe-arrow">→</div>
    <div class="stage"><div class="icon">🧮</div><div class="name">Tokenizer</div><div class="desc">real token counts</div></div>
    <div class="pipe-arrow">→</div>
    <div class="stage"><div class="icon">🧠</div><div class="name">Model</div><div class="desc">Qwen2.5 · CPU</div></div>
    <div class="pipe-arrow">→</div>
    <div class="stage"><div class="icon">📡</div><div class="name">Stream</div><div class="desc">SSE responses</div></div>
  </section>

  <section>
    <h2>Endpoints</h2>
    <p class="sub">Every route is fully OpenAI-compatible, protected by Bearer API-key auth and rate limiting.</p>
    <div class="grid">
      <div class="card">
        <span class="method"><span class="verb post">POST</span> /v1/chat/completions</span>
        <p class="desc">Multi-turn chat completions from the local Qwen2.5 model, with real token usage accounting.</p>
        <span class="tagline">stream = true · SSE chunks</span>
      </div>
      <div class="card">
        <span class="method"><span class="verb post">POST</span> /v1/embeddings</span>
        <p class="desc">Semantic embeddings from a dedicated local model (nomic-embed-text, 768-dim vectors).</p>
        <span class="tagline">single string or batch</span>
      </div>
      <div class="card">
        <span class="method"><span class="verb post">POST</span> /v1/chat/completions</span>
        <p class="desc">Tool / function calling — the model decides to call <code>get_weather</code> or <code>add</code>, then reasons over the result.</p>
        <span class="tagline">tools = [...]</span>
      </div>
      <div class="card">
        <span class="method"><span class="verb get">GET</span> /v1/models</span>
        <p class="desc">List the models currently served by this instance.</p>
        <span class="tagline">qwen2.5 · nomic-embed</span>
      </div>
      <div class="card">
        <span class="method"><span class="verb get">GET</span> /health</span>
        <p class="desc">Readiness probe for uptime monitors and orchestrators.</p>
        <span class="tagline">{"status":"ok"}</span>
      </div>
    </div>
  </section>

  <section class="features" style="margin-top:64px;">
    <h2>Why it matters</h2>
    <p class="sub">The same concerns every real inference API has to solve, tackled deliberately and minimally.</p>
    <div class="grid">
      <div class="card feature"><div class="ico">🔐</div><div class="t">Auth</div><div class="d">Bearer API-key validation on every protected route.</div></div>
      <div class="card feature"><div class="ico">⏱️</div><div class="t">Rate limiting</div><div class="d">Fixed-window limits per key with Retry-After headers.</div></div>
      <div class="card feature"><div class="ico">📶</div><div class="t">Streaming</div><div class="d">Token-level SSE with familiar OpenAI chunk shapes.</div></div>
      <div class="card feature"><div class="ico">🧰</div><div class="t">Tool calling</div><div class="d">Model-driven function selection + execution loop.</div></div>
      <div class="card feature"><div class="ico">🏠</div><div class="t">Self-hosted</div><div class="d">Runs entirely on CPU with quantized local weights.</div></div>
      <div class="card feature"><div class="ico">📐</div><div class="t">Compatible</div><div class="d">Swap the base URL in any OpenAI client — nothing else changes.</div></div>
    </div>
  </section>

  <footer>
    <span>__APP_NAME__ · built to learn how inference APIs work</span>
    <span>docs at <code>/docs</code> · health at <code>/health</code></span>
  </footer>

</div>
</body>
</html>
"""

    html = html.replace("__APP_NAME__", app_name)
    html = html.replace("__CHAT_BADGE__", chat_badge)
    html = html.replace("__EMBED_BADGE__", embed_badge)
    html = html.replace("__CTX__", str(settings.model_ctx))
    html = html.replace("__THREADS__", str(settings.model_threads))
    return HTMLResponse(content=html)
