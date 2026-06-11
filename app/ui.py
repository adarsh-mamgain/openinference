from __future__ import annotations

import json
from textwrap import dedent

from app.settings import SETTINGS


CREDIT_PACKS = [1000, 2500, 5000, 10000]
MODEL_FAMILIES = [
    {
        'name': 'DeepSeek',
        'slug': 'deepseek-v4-flash',
        'status': 'Live',
        'description': 'Fast general-purpose reasoning with an aggressive cost profile.',
        'price': '$0.25',
        'unit': '/ 1M tokens',
    },
    {
        'name': 'Qwen',
        'slug': 'qwen3-32b',
        'status': 'Live',
        'description': 'Strong coding and multilingual coverage for product workloads.',
        'price': '$0.35',
        'unit': '/ 1M tokens',
    },
    {
        'name': 'Llama',
        'slug': 'llama-4-scout',
        'status': 'Live',
        'description': 'High-capacity open-weight model for broad assistant use cases.',
        'price': '$0.48',
        'unit': '/ 1M tokens',
    },
    {
        'name': 'Mistral',
        'slug': 'mistral-small-3.1',
        'status': 'Beta',
        'description': 'Compact and fast for latency-sensitive work and fallbacks.',
        'price': '$0.20',
        'unit': '/ 1M tokens',
    },
    {
        'name': 'Gemma',
        'slug': 'gemma-3-27b',
        'status': 'Beta',
        'description': 'Lightweight Google open model for interactive tasks.',
        'price': '$0.18',
        'unit': '/ 1M tokens',
    },
]

COMMON_CSS = """
  :root {
    --bg: #080c10;
    --surface: #0e1520;
    --surface-2: #131c28;
    --surface-3: #1a2535;
    --border: rgba(255,255,255,0.07);
    --border-strong: rgba(255,255,255,0.13);
    --text: #e8edf3;
    --muted: #7a8899;
    --dim: #4a5668;
    --accent: #4fffb0;
    --accent-dim: rgba(79,255,176,0.12);
    --accent-border: rgba(79,255,176,0.25);
    --blue: #4f9fff;
    --blue-dim: rgba(79,159,255,0.12);
    --red: #ff5f5f;
    --red-dim: rgba(255,95,95,0.10);
    --yellow: #ffd55f;
    --r-sm: 8px;
    --r-md: 12px;
    --r-lg: 18px;
    --r-xl: 24px;
    --shadow: 0 24px 64px rgba(0,0,0,0.5);
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', ui-monospace, monospace;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body {
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    font-size: 14px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  a { color: inherit; text-decoration: none; }
  button, input, select, textarea { font: inherit; }
  button { cursor: pointer; }

  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--surface-3); border-radius: 99px; }

  .container { max-width: 1160px; margin: 0 auto; padding: 0 28px; }

  .topbar {
    position: sticky; top: 0; z-index: 50;
    border-bottom: 1px solid var(--border);
    background: rgba(8,12,16,0.88);
    backdrop-filter: blur(20px);
  }
  .topbar-inner {
    display: flex; align-items: center;
    justify-content: space-between;
    gap: 20px;
    height: 60px;
  }
  .brand {
    display: flex; align-items: center; gap: 10px;
    font-size: 15px; font-weight: 700; letter-spacing: -0.02em;
    color: var(--text);
  }
  .brand-icon {
    width: 30px; height: 30px;
    border-radius: 8px;
    background: linear-gradient(135deg, var(--accent) 0%, #00e5ff 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; color: #000; font-weight: 900;
    flex-shrink: 0;
  }
  .nav { display: flex; align-items: center; gap: 4px; }
  .nav-link {
    padding: 6px 12px; border-radius: var(--r-sm);
    color: var(--muted); font-size: 13px;
    transition: color 120ms, background 120ms;
    border: none; background: none;
  }
  .nav-link:hover { color: var(--text); background: var(--surface-2); }
  .nav-link.active { color: var(--text); }

  .btn {
    display: inline-flex; align-items: center; justify-content: center;
    gap: 8px; border-radius: var(--r-sm);
    padding: 8px 16px; font-size: 13px; font-weight: 600;
    border: 1px solid var(--border-strong);
    background: var(--surface-2); color: var(--text);
    transition: all 120ms ease; white-space: nowrap;
  }
  .btn:hover { background: var(--surface-3); border-color: var(--border-strong); }
  .btn.primary {
    background: var(--accent); color: #000;
    border-color: var(--accent);
    box-shadow: 0 0 24px rgba(79,255,176,0.2);
  }
  .btn.primary:hover { background: #5fffc0; box-shadow: 0 0 32px rgba(79,255,176,0.3); }
  .btn.ghost { background: transparent; border-color: var(--border); }
  .btn.ghost:hover { background: var(--surface); }
  .btn.danger { background: var(--red-dim); border-color: var(--red); color: var(--red); }
  .btn.sm { padding: 6px 12px; font-size: 12px; }
  .btn.xs { padding: 4px 8px; font-size: 11px; border-radius: 6px; }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .tag {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 9px; border-radius: 99px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
    border: 1px solid;
    text-transform: uppercase;
  }
  .tag.live { color: var(--accent); background: var(--accent-dim); border-color: var(--accent-border); }
  .tag.beta { color: var(--yellow); background: rgba(255,213,95,0.10); border-color: rgba(255,213,95,0.25); }
  .tag.dim { color: var(--dim); background: transparent; border-color: var(--border); }

  .panel {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--r-lg);
  }
  .panel-head {
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px; padding: 14px 18px;
    border-bottom: 1px solid var(--border);
    font-size: 13px; font-weight: 700; color: var(--muted);
    letter-spacing: 0.06em; text-transform: uppercase;
  }
  .panel-body { padding: 18px; }

  .code-block {
    background: #050810; border: 1px solid var(--border);
    border-radius: var(--r-md); padding: 16px 18px;
    font-size: 13px; line-height: 1.7;
    color: #c9d8ee; overflow-x: auto;
    white-space: pre;
  }

  .field { display: grid; gap: 6px; }
  .field label { font-size: 12px; color: var(--muted); font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; }
  .field input, .field textarea, .field select {
    width: 100%; padding: 10px 13px;
    background: var(--surface-2); border: 1px solid var(--border-strong);
    border-radius: var(--r-sm); color: var(--text);
    outline: none; transition: border-color 120ms, box-shadow 120ms;
  }
  .field input:focus, .field textarea:focus, .field select:focus {
    border-color: var(--accent-border);
    box-shadow: 0 0 0 3px var(--accent-dim);
  }
  .field textarea { min-height: 120px; resize: vertical; line-height: 1.6; }
  .field select option { background: var(--surface-2); }

  .tbl-wrap { border-radius: var(--r-md); border: 1px solid var(--border); overflow: auto; }
  .tbl { width: 100%; border-collapse: collapse; }
  .tbl th { padding: 10px 14px; background: var(--surface-2); color: var(--muted); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; text-align: left; border-bottom: 1px solid var(--border); }
  .tbl td { padding: 11px 14px; font-size: 13px; border-bottom: 1px solid var(--border); }
  .tbl tr:last-child td { border-bottom: none; }
  .tbl tr:hover td { background: var(--surface-2); }

  .stack { display: flex; flex-direction: column; gap: 14px; }
  .row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }

  .alert {
    padding: 11px 14px; border-radius: var(--r-sm);
    font-size: 13px; border: 1px solid;
  }
  .alert.success { background: var(--accent-dim); border-color: var(--accent-border); color: var(--accent); }
  .alert.error { background: var(--red-dim); border-color: var(--red); color: var(--red); }
  .alert.info { background: var(--blue-dim); border-color: rgba(79,159,255,0.3); color: var(--blue); }

  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
  .dot.pulse { animation: pulse 2s ease-in-out infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; box-shadow: 0 0 0 0 var(--accent-dim); } 50% { box-shadow: 0 0 0 5px transparent; } }

  .muted { color: var(--muted); }

  .spin {
    width: 14px; height: 14px; border-radius: 50%;
    border: 2px solid var(--border-strong);
    border-top-color: var(--accent);
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  @media (max-width: 768px) {
    .container { padding: 0 16px; }
    .grid-2 { grid-template-columns: 1fr; }
    .grid-3 { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 480px) {
    .grid-3 { grid-template-columns: 1fr; }
  }
"""


def _shell(title: str, body: str, extra_css: str = '', scripts: str = '') -> str:
    return dedent(f'''
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>{title}</title>
            <style>
{COMMON_CSS}
{extra_css}
            </style>
          </head>
          <body>
            {body}
            <script>{scripts}</script>
          </body>
        </html>
    ''').strip()


def render_landing_page() -> str:
    extra_css = """
      .hero-wrap {
        padding: 100px 0 80px;
        position: relative;
        overflow: hidden;
      }
      .hero-wrap::before {
        content: '';
        position: absolute; inset: 0;
        background: radial-gradient(ellipse 70% 50% at 50% -10%, rgba(79,255,176,0.07) 0%, transparent 70%);
        pointer-events: none;
      }
      .hero-grid-bg {
        position: absolute; inset: 0;
        background-image:
          linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
        background-size: 48px 48px;
        mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, black 30%, transparent 80%);
        pointer-events: none;
      }
      .eyebrow {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 5px 12px; border-radius: 99px;
        border: 1px solid var(--accent-border);
        background: var(--accent-dim);
        color: var(--accent); font-size: 12px; font-weight: 700;
        letter-spacing: 0.04em; text-transform: uppercase;
        margin-bottom: 24px;
      }
      .hero-title {
        font-size: clamp(36px, 5.5vw, 66px);
        line-height: 1.05; letter-spacing: -0.04em;
        font-weight: 800; margin-bottom: 22px;
      }
      .hero-title .dim-text { color: var(--muted); }
      .hero-sub {
        font-size: 16px; color: var(--muted);
        max-width: 52ch; line-height: 1.7; margin-bottom: 36px;
      }
      .hero-actions { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 52px; }
      .price-callout {
        display: inline-flex; align-items: baseline; gap: 6px;
        font-size: 13px; color: var(--dim);
        background: var(--surface-2); border: 1px solid var(--border);
        padding: 6px 14px; border-radius: 99px;
      }
      .price-callout strong { color: var(--accent); font-size: 15px; }

      .terminal-hero {
        background: #040810;
        border: 1px solid var(--border-strong);
        border-radius: var(--r-xl);
        box-shadow: var(--shadow), 0 0 0 1px rgba(79,255,176,0.05);
        overflow: hidden;
        margin-top: 60px;
      }
      .terminal-titlebar {
        display: flex; align-items: center; gap: 8px;
        padding: 12px 16px; border-bottom: 1px solid var(--border);
        background: var(--surface);
      }
      .terminal-dot { width: 10px; height: 10px; border-radius: 50%; }
      .terminal-filename { margin-left: 10px; font-size: 12px; color: var(--muted); }
      .terminal-body { padding: 22px 24px; font-size: 13px; line-height: 1.9; color: #c9d8ee; white-space: pre; overflow-x: auto; }
      .t-green { color: var(--accent); }
      .t-blue { color: #7eb3ff; }
      .t-orange { color: #ffb347; }
      .t-gray { color: var(--dim); }
      .t-white { color: var(--text); }

      .models-section { padding: 72px 0; }
      .section-label {
        font-size: 11px; font-weight: 700; letter-spacing: 0.12em;
        text-transform: uppercase; color: var(--muted); margin-bottom: 10px;
      }
      .section-title {
        font-size: clamp(24px, 3.5vw, 38px);
        letter-spacing: -0.03em; font-weight: 800;
        margin-bottom: 12px;
      }
      .section-sub { font-size: 15px; color: var(--muted); max-width: 54ch; line-height: 1.65; }
      .section-head { margin-bottom: 40px; }

      .model-card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--r-lg); padding: 20px;
        display: flex; flex-direction: column; gap: 12px;
        transition: border-color 200ms, background 200ms;
        position: relative; overflow: hidden;
      }
      .model-card::before {
        content: ''; position: absolute;
        top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, var(--accent-border), transparent);
        opacity: 0; transition: opacity 200ms;
      }
      .model-card:hover { border-color: var(--border-strong); background: var(--surface-2); }
      .model-card:hover::before { opacity: 1; }
      .model-name { font-weight: 800; font-size: 17px; letter-spacing: -0.02em; }
      .model-slug { font-size: 11px; color: var(--dim); font-family: inherit; }
      .model-desc { font-size: 13px; color: var(--muted); line-height: 1.55; flex: 1; }
      .model-price { font-size: 20px; font-weight: 800; color: var(--accent); letter-spacing: -0.03em; }
      .model-price span { font-size: 12px; font-weight: 400; color: var(--dim); }

      .how-it-works { padding: 72px 0; border-top: 1px solid var(--border); }
      .step-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--border); border: 1px solid var(--border); border-radius: var(--r-lg); overflow: hidden; }
      .step { background: var(--surface); padding: 28px 24px; }
      .step-num { font-size: 11px; font-weight: 700; color: var(--dim); letter-spacing: 0.10em; text-transform: uppercase; margin-bottom: 14px; }
      .step h3 { font-size: 17px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 10px; }
      .step p { font-size: 13px; color: var(--muted); line-height: 1.6; }

      .pricing-section { padding: 72px 0; border-top: 1px solid var(--border); }
      .pack-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 32px; }
      .pack {
        border: 1px solid var(--border); border-radius: var(--r-lg);
        padding: 20px; background: var(--surface);
        display: flex; flex-direction: column; gap: 8px;
        transition: border-color 200ms;
      }
      .pack:hover { border-color: var(--border-strong); }
      .pack.featured { border-color: var(--accent-border); background: linear-gradient(135deg, var(--accent-dim), transparent); }
      .pack-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
      .pack-amount { font-size: 30px; font-weight: 800; letter-spacing: -0.04em; color: var(--text); }
      .pack-amount span { font-size: 14px; color: var(--muted); font-weight: 400; }
      .pack-note { font-size: 12px; color: var(--dim); }

      .faq-section { padding: 72px 0; border-top: 1px solid var(--border); }
      .faq-list { display: flex; flex-direction: column; gap: 1px; background: var(--border); border: 1px solid var(--border); border-radius: var(--r-lg); overflow: hidden; margin-top: 32px; }
      details.faq {
        background: var(--surface); padding: 0;
      }
      details.faq summary {
        list-style: none; cursor: pointer;
        padding: 18px 22px; font-size: 14px; font-weight: 700;
        display: flex; justify-content: space-between; align-items: center;
        gap: 16px;
        transition: color 120ms;
      }
      details.faq summary::-webkit-details-marker { display: none; }
      details.faq summary::after { content: '+'; color: var(--dim); font-size: 18px; flex-shrink: 0; transition: transform 200ms; }
      details.faq[open] summary::after { transform: rotate(45deg); }
      details.faq[open] summary { color: var(--accent); }
      details.faq .faq-body { padding: 0 22px 18px; font-size: 13px; color: var(--muted); line-height: 1.7; }

      .cta-section { padding: 80px 0; }
      .cta-box {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--r-xl); padding: 52px;
        text-align: center; position: relative; overflow: hidden;
      }
      .cta-box::before {
        content: ''; position: absolute; inset: 0;
        background: radial-gradient(ellipse 60% 80% at 50% 100%, rgba(79,255,176,0.05) 0%, transparent 70%);
        pointer-events: none;
      }
      .cta-box h2 { font-size: clamp(24px, 3vw, 38px); letter-spacing: -0.03em; font-weight: 800; margin-bottom: 14px; }
      .cta-box p { font-size: 15px; color: var(--muted); max-width: 44ch; margin: 0 auto 32px; line-height: 1.65; }
      .cta-box .row { justify-content: center; }

      .footer { padding: 28px 0; border-top: 1px solid var(--border); }
      .footer-inner { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
      .footer p { font-size: 12px; color: var(--dim); }

      @media (max-width: 900px) {
        .step-grid { grid-template-columns: 1fr; }
        .pack-grid { grid-template-columns: 1fr 1fr; }
      }
      @media (max-width: 600px) {
        .pack-grid { grid-template-columns: 1fr; }
        .cta-box { padding: 32px 20px; }
      }
    """

    models_html = ''.join(
        f'''<article class="model-card">
  <div class="row" style="justify-content:space-between;align-items:flex-start;gap:8px">
    <div class="model-name">{m['name']}</div>
    <span class="tag {'live' if m['status'] == 'Live' else 'beta'}">{m['status']}</span>
  </div>
  <div class="model-slug">{m['slug']}</div>
  <div class="model-desc">{m['description']}</div>
  <div class="model-price">{m['price']} <span>{m['unit']}</span></div>
</article>'''
        for m in MODEL_FAMILIES
    )

    body = f'''
      <header class="topbar">
        <div class="container topbar-inner">
          <a class="brand" href="/">
            <div class="brand-icon">N</div>
            {SETTINGS.app_name}
          </a>
          <nav class="nav">
            <a class="nav-link" href="#models">Models</a>
            <a class="nav-link" href="#pricing">Pricing</a>
            <a class="nav-link" href="#faq">FAQ</a>
            <a class="nav-link" href="/login">Sign in</a>
            <a class="btn primary sm" href="/signup">Get started</a>
          </nav>
        </div>
      </header>

      <main>
        <section class="hero-wrap">
          <div class="hero-grid-bg"></div>
          <div class="container">
            <div class="eyebrow">
              <span class="dot pulse"></span>
              Open-weight models - OpenAI-compatible API
            </div>
            <h1 class="hero-title">
              Run open models.<br>
              <span class="dim-text">Pay way less.</span>
            </h1>
            <p class="hero-sub">
              {SETTINGS.app_name} routes your requests to DeepSeek, Llama, Qwen, Mistral, and Gemma -
              through one OpenAI-compatible endpoint. No GPU bills. No vendor lock-in.
              Top up credits, make calls.
            </p>
            <div class="hero-actions">
              <a class="btn primary" href="/signup">Start for free -></a>
              <a class="btn ghost" href="#models">See models & pricing</a>
            </div>
            <div class="row" style="gap:16px">
              <span class="price-callout">DeepSeek v4 Flash: <strong>$0.25</strong> / 1M tokens</span>
              <span class="price-callout">Llama 4 Scout: <strong>$0.48</strong> / 1M tokens</span>
              <span class="price-callout">Qwen 3 32B: <strong>$0.35</strong> / 1M tokens</span>
            </div>

            <div class="terminal-hero">
              <div class="terminal-titlebar">
                <div class="terminal-dot" style="background:#ff5f57"></div>
                <div class="terminal-dot" style="background:#febc2e"></div>
                <div class="terminal-dot" style="background:#28c840"></div>
                <span class="terminal-filename">example.py</span>
              </div>
              <div class="terminal-body"><span class="t-blue">from</span> <span class="t-white">openai</span> <span class="t-blue">import</span> <span class="t-white">OpenAI</span>

client = <span class="t-orange">OpenAI</span>(
    <span class="t-green">api_key</span>=<span class="t-white">"nr_live_xxxxxxxxxxxxxxxx"</span>,
    <span class="t-green">base_url</span>=<span class="t-white">"{SETTINGS.base_url}/v1"</span>,
)

response = client.chat.completions.<span class="t-orange">create</span>(
    <span class="t-green">model</span>=<span class="t-white">"deepseek-v4-flash"</span>,  <span class="t-gray"># or llama-4-scout, qwen3-32b ...</span>
    <span class="t-green">messages</span>=[{{"role": "user", "content": "Write a FastAPI auth middleware"}}],
)
<span class="t-orange">print</span>(response.choices[<span class="t-white">0</span>].message.content)</div>
            </div>
          </div>
        </section>

        <section class="models-section" id="models">
          <div class="container">
            <div class="section-head">
              <div class="section-label">Model catalog</div>
              <div class="section-title">Five model families. One endpoint.</div>
              <div class="section-sub">All requests go through <code style="color:var(--accent);">/v1/chat/completions</code> - the same interface your code already uses.</div>
            </div>
            <div class="grid-3" style="grid-template-columns: repeat(5,1fr)">
              {models_html}
            </div>
          </div>
        </section>

        <section class="how-it-works">
          <div class="container">
            <div class="section-head">
              <div class="section-label">How it works</div>
              <div class="section-title">Three steps to your first call</div>
            </div>
            <div class="step-grid">
              <div class="step">
                <div class="step-num">Step 01</div>
                <h3>Create a workspace</h3>
                <p>Sign up in under a minute. No credit card required to register. Your workspace holds your API keys, balance, and usage logs.</p>
              </div>
              <div class="step">
                <div class="step-num">Step 02</div>
                <h3>Top up credits</h3>
                <p>Add credits via card checkout. Your balance is available immediately after payment confirmation. No monthly minimums.</p>
              </div>
              <div class="step">
                <div class="step-num">Step 03</div>
                <h3>Start calling</h3>
                <p>Generate an API key and point your OpenAI client at our endpoint. Zero SDK changes. Pick a model and ship.</p>
              </div>
            </div>
          </div>
        </section>

        <section class="pricing-section" id="pricing">
          <div class="container">
            <div class="section-head">
              <div class="section-label">Pricing</div>
              <div class="section-title">Credits don't expire. Use them when you need them.</div>
              <div class="section-sub">Top up as much as you need. Credits go toward model usage at the token prices listed above. No subscriptions.</div>
            </div>
            <div class="pack-grid">
              <div class="pack">
                <div class="pack-label">Starter</div>
                <div class="pack-amount">$10 <span>credit</span></div>
                <div class="pack-note">Good for experimentation and small workloads</div>
              </div>
              <div class="pack">
                <div class="pack-label">Developer</div>
                <div class="pack-amount">$25 <span>credit</span></div>
                <div class="pack-note">For active projects and regular usage</div>
              </div>
              <div class="pack featured">
                <div class="pack-label" style="color:var(--accent)">Popular</div>
                <div class="pack-amount">$50 <span>credit</span></div>
                <div class="pack-note">Best value for small teams and agents</div>
              </div>
              <div class="pack">
                <div class="pack-label">Team</div>
                <div class="pack-amount">$100 <span>credit</span></div>
                <div class="pack-note">For high-volume pipelines and production workloads</div>
              </div>
            </div>
          </div>
        </section>

        <section class="faq-section" id="faq">
          <div class="container">
            <div class="section-head">
              <div class="section-label">FAQ</div>
              <div class="section-title">Common questions</div>
            </div>
            <div class="faq-list">
              <details class="faq">
                <summary>Can I use my existing OpenAI SDK code?</summary>
                <div class="faq-body">Yes. Change <code>api_key</code> to your {SETTINGS.app_name} key and set <code>base_url</code> to <code>{SETTINGS.base_url}/v1</code>. That's all. No new SDK, no new request format.</div>
              </details>
              <details class="faq">
                <summary>Which providers do you route through?</summary>
                <div class="faq-body">We route through DeepInfra, Together.ai, and Groq depending on model, load, and latency targets. You pick the model - we pick the best available provider for that request.</div>
              </details>
              <details class="faq">
                <summary>Do credits expire?</summary>
                <div class="faq-body">No. Top up when you need to. Your balance carries forward indefinitely.</div>
              </details>
              <details class="faq">
                <summary>What happens if I run out of credits?</summary>
                <div class="faq-body">Requests return a 402. Your existing workloads don't silently fail - you'll see the error immediately and can top up to resume.</div>
              </details>
              <details class="faq">
                <summary>Is there rate limiting?</summary>
                <div class="faq-body">Yes. Free and paid plans have per-minute rate limits to prevent runaway costs. Limits are visible in your dashboard.</div>
              </details>
            </div>
          </div>
        </section>

        <section class="cta-section">
          <div class="container">
            <div class="cta-box">
              <h2>Start routing in five minutes</h2>
              <p>Create a workspace, add credits, get a key. Your first call takes less time than reading a docs page.</p>
              <div class="row">
                <a class="btn primary" href="/signup">Create workspace -></a>
                <a class="btn ghost" href="/login">Sign in</a>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer class="footer">
        <div class="container footer-inner">
          <div class="brand">
            <div class="brand-icon" style="width:22px;height:22px;font-size:11px">N</div>
            {SETTINGS.app_name}
          </div>
          <p>OpenAI-compatible routing for open-weight models.</p>
          <p style="font-size:12px;color:var(--dim)">© 2026 {SETTINGS.app_name}</p>
        </div>
      </footer>
    '''
    return _shell(f'{SETTINGS.app_name} - Open model routing', body, extra_css)


def render_login_page() -> str:
    extra_css = """
      .auth-wrap { min-height: 100vh; display: grid; grid-template-columns: 1fr 1fr; }
      .auth-left {
        background: var(--surface); border-right: 1px solid var(--border);
        display: flex; flex-direction: column; justify-content: center;
        padding: 60px 72px;
        position: relative; overflow: hidden;
      }
      .auth-left::before {
        content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 40%;
        background: radial-gradient(ellipse 80% 60% at 50% 100%, rgba(79,255,176,0.06), transparent);
        pointer-events: none;
      }
      .auth-right { display: flex; flex-direction: column; justify-content: center; padding: 60px 72px; }
      .auth-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 52px; font-size: 15px; font-weight: 700; }
      .auth-tagline { font-size: clamp(22px, 3vw, 30px); font-weight: 800; letter-spacing: -0.03em; line-height: 1.2; margin-bottom: 16px; }
      .auth-sub { font-size: 14px; color: var(--muted); line-height: 1.65; max-width: 38ch; }
      .auth-perks { margin-top: 40px; display: flex; flex-direction: column; gap: 14px; }
      .perk { display: flex; align-items: flex-start; gap: 12px; }
      .perk-icon { width: 22px; height: 22px; border-radius: 6px; background: var(--accent-dim); border: 1px solid var(--accent-border); display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: var(--accent); font-size: 11px; margin-top: 1px; }
      .perk-text { font-size: 13px; color: var(--muted); line-height: 1.5; }
      .perk-text strong { color: var(--text); display: block; font-size: 13px; margin-bottom: 2px; }
      .auth-form-title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 6px; }
      .auth-form-sub { font-size: 13px; color: var(--muted); margin-bottom: 30px; }
      .form-stack { display: flex; flex-direction: column; gap: 16px; }
      .or-divider { display: flex; align-items: center; gap: 12px; color: var(--dim); font-size: 12px; }
      .or-divider::before, .or-divider::after { content: ''; flex: 1; height: 1px; background: var(--border); }
      @media (max-width: 768px) {
        .auth-wrap { grid-template-columns: 1fr; }
        .auth-left { display: none; }
        .auth-right { padding: 40px 24px; }
      }
    """

    body = f'''
      <div class="auth-wrap">
        <div class="auth-left">
          <div class="auth-brand">
            <div class="brand-icon">N</div>
            {SETTINGS.app_name}
          </div>
          <div class="auth-tagline">Open models.<br>One endpoint.<br>Token-level pricing.</div>
          <div class="auth-sub">Access DeepSeek, Llama, Qwen, Mistral, and Gemma through the same API surface as OpenAI.</div>
          <div class="auth-perks">
            <div class="perk">
              <div class="perk-icon">⚡</div>
              <div class="perk-text"><strong>No SDK changes</strong>Just swap the base URL and key.</div>
            </div>
            <div class="perk">
              <div class="perk-icon">$</div>
              <div class="perk-text"><strong>Credits, not subscriptions</strong>Top up when you need to. Nothing expires.</div>
            </div>
            <div class="perk">
              <div class="perk-icon">⛓</div>
              <div class="perk-text"><strong>No vendor lock-in</strong>Open models, transparent pricing, you own your prompts.</div>
            </div>
          </div>
        </div>

        <div class="auth-right">
          <div class="auth-form-title">Sign in</div>
          <div class="auth-form-sub">Access your workspace, keys, and usage logs.</div>
          <div class="form-stack">
            <div class="field">
              <label for="login-email">Email</label>
              <input id="login-email" type="email" placeholder="you@company.com" autocomplete="email" />
            </div>
            <div class="field">
              <label for="login-password">Password</label>
              <input id="login-password" type="password" placeholder="••••••••" autocomplete="current-password" />
            </div>
            <button class="btn primary" id="login-btn" style="width:100%;padding:11px 16px;font-size:14px">Sign in -></button>
            <div id="login-status" role="status" aria-live="polite"></div>
            <div class="or-divider">or</div>
            <a class="btn ghost" href="/signup" style="width:100%;text-align:center;padding:11px 16px;font-size:14px">Create a workspace</a>
          </div>
        </div>
      </div>
    '''

    scripts = '''
      const btn = document.getElementById('login-btn');
      const status = document.getElementById('login-status');
      btn.addEventListener('click', async () => {
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        if (!email || !password) { status.innerHTML = '<div class="alert error">Enter email and password.</div>'; return; }
        btn.disabled = true;
        btn.innerHTML = '<span class="spin"></span> Signing in...';
        const res = await fetch('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
        const payload = await res.json();
        if (!res.ok) { status.innerHTML = '<div class="alert error">' + (payload.detail || 'Login failed') + '</div>'; btn.disabled = false; btn.textContent = 'Sign in ->'; return; }
        window.location.href = '/app';
      });
      document.getElementById('login-password').addEventListener('keydown', e => { if (e.key === 'Enter') btn.click(); });
    '''
    return _shell(f'Sign in | {SETTINGS.app_name}', body, extra_css, scripts)


def render_signup_page() -> str:
    extra_css = """
      .auth-wrap { min-height: 100vh; display: grid; grid-template-columns: 1fr 1fr; }
      .auth-left {
        background: var(--surface); border-right: 1px solid var(--border);
        display: flex; flex-direction: column; justify-content: center;
        padding: 60px 72px; position: relative; overflow: hidden;
      }
      .auth-left::before {
        content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 40%;
        background: radial-gradient(ellipse 80% 60% at 50% 100%, rgba(79,255,176,0.06), transparent);
        pointer-events: none;
      }
      .auth-right { display: flex; flex-direction: column; justify-content: center; padding: 60px 72px; }
      .auth-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 52px; font-size: 15px; font-weight: 700; }
      .auth-tagline { font-size: clamp(22px, 3vw, 30px); font-weight: 800; letter-spacing: -0.03em; line-height: 1.2; margin-bottom: 16px; }
      .auth-sub { font-size: 14px; color: var(--muted); line-height: 1.65; max-width: 38ch; }
      .feature-list { margin-top: 40px; display: flex; flex-direction: column; gap: 10px; }
      .feat-row { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--muted); }
      .feat-row .dot { flex-shrink: 0; }
      .auth-form-title { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 6px; }
      .auth-form-sub { font-size: 13px; color: var(--muted); margin-bottom: 30px; }
      .form-stack { display: flex; flex-direction: column; gap: 16px; }
      .or-divider { display: flex; align-items: center; gap: 12px; color: var(--dim); font-size: 12px; }
      .or-divider::before, .or-divider::after { content: ''; flex: 1; height: 1px; background: var(--border); }
      @media (max-width: 768px) {
        .auth-wrap { grid-template-columns: 1fr; }
        .auth-left { display: none; }
        .auth-right { padding: 40px 24px; }
      }
    """

    body = f'''
      <div class="auth-wrap">
        <div class="auth-left">
          <div class="auth-brand">
            <div class="brand-icon">N</div>
            {SETTINGS.app_name}
          </div>
          <div class="auth-tagline">Ship faster.<br>Spend less.<br>Stay open.</div>
          <div class="auth-sub">One workspace for all your open model usage. Keys, credits, usage - in one dashboard.</div>
          <div class="feature-list">
            <div class="feat-row"><span class="dot" style="background:var(--accent)"></span>5 model families via one /v1 endpoint</div>
            <div class="feat-row"><span class="dot" style="background:var(--accent)"></span>DeepSeek V4 Flash from $0.25 / 1M tokens</div>
            <div class="feat-row"><span class="dot" style="background:var(--accent)"></span>No monthly fees - pay per token</div>
            <div class="feat-row"><span class="dot" style="background:var(--accent)"></span>Unlimited API keys per workspace</div>
            <div class="feat-row"><span class="dot" style="background:var(--accent)"></span>Usage logs and spend tracking</div>
          </div>
        </div>

        <div class="auth-right">
          <div class="auth-form-title">Create workspace</div>
          <div class="auth-form-sub">Takes about 30 seconds. No card needed to register.</div>
          <div class="form-stack">
            <div class="field">
              <label for="signup-name">Your name</label>
              <input id="signup-name" type="text" placeholder="Adarsh" autocomplete="name" />
            </div>
            <div class="field">
              <label for="signup-email">Email</label>
              <input id="signup-email" type="email" placeholder="you@company.com" autocomplete="email" />
            </div>
            <div class="field">
              <label for="signup-password">Password</label>
              <input id="signup-password" type="password" placeholder="Create a password" autocomplete="new-password" />
            </div>
            <button class="btn primary" id="signup-btn" style="width:100%;padding:11px 16px;font-size:14px">Create workspace -></button>
            <div id="signup-status" role="status" aria-live="polite"></div>
            <div class="or-divider">already have access?</div>
            <a class="btn ghost" href="/login" style="width:100%;text-align:center;padding:11px 16px;font-size:14px">Sign in</a>
          </div>
        </div>
      </div>
    '''

    scripts = '''
      const btn = document.getElementById('signup-btn');
      const status = document.getElementById('signup-status');
      btn.addEventListener('click', async () => {
        const name = document.getElementById('signup-name').value.trim();
        const email = document.getElementById('signup-email').value.trim();
        const password = document.getElementById('signup-password').value;
        if (!email || !password) { status.innerHTML = '<div class="alert error">Email and password required.</div>'; return; }
        btn.disabled = true;
        btn.innerHTML = '<span class="spin"></span> Creating workspace...';
        const res = await fetch('/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, email, password }) });
        const payload = await res.json();
        if (!res.ok) { status.innerHTML = '<div class="alert error">' + (payload.detail || 'Registration failed') + '</div>'; btn.disabled = false; btn.textContent = 'Create workspace ->'; return; }
        window.location.href = '/app';
      });
    '''
    return _shell(f'Sign up | {SETTINGS.app_name}', body, extra_css, scripts)


def render_app_page() -> str:
    packs_json = json.dumps(CREDIT_PACKS)
    model_family_json = json.dumps(MODEL_FAMILIES)

    extra_css = """
      .app-layout { display: flex; min-height: 100vh; }
      .sidebar {
        width: 220px; flex-shrink: 0;
        background: var(--surface); border-right: 1px solid var(--border);
        display: flex; flex-direction: column;
        position: sticky; top: 0; height: 100vh; overflow-y: auto;
      }
      .sidebar-brand {
        display: flex; align-items: center; gap: 10px;
        padding: 20px 16px; border-bottom: 1px solid var(--border);
        font-size: 14px; font-weight: 700;
      }
      .sidebar-nav { flex: 1; padding: 12px 10px; display: flex; flex-direction: column; gap: 2px; }
      .sidebar-item {
        display: flex; align-items: center; gap: 10px;
        padding: 9px 12px; border-radius: var(--r-sm);
        font-size: 13px; color: var(--muted);
        border: none; background: none; width: 100%;
        text-align: left; cursor: pointer;
        transition: background 120ms, color 120ms;
        text-decoration: none;
      }
      .sidebar-item:hover { background: var(--surface-2); color: var(--text); }
      .sidebar-item.active { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-border); }
      .sidebar-icon { width: 16px; text-align: center; flex-shrink: 0; }
      .sidebar-bottom { padding: 12px 10px; border-top: 1px solid var(--border); }
      .account-chip {
        display: flex; align-items: center; gap: 10px;
        padding: 10px 12px; border-radius: var(--r-sm);
        background: var(--surface-2); border: 1px solid var(--border);
      }
      .account-avatar {
        width: 28px; height: 28px; border-radius: 8px;
        background: linear-gradient(135deg, var(--accent), #00e5ff);
        display: flex; align-items: center; justify-content: center;
        font-size: 12px; font-weight: 900; color: #000; flex-shrink: 0;
      }
      .account-info { flex: 1; min-width: 0; }
      .account-email { font-size: 11px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .account-plan { font-size: 10px; color: var(--accent); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }

      .app-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
      .app-topbar {
        height: 56px; display: flex; align-items: center; justify-content: space-between;
        gap: 16px; padding: 0 28px;
        border-bottom: 1px solid var(--border);
        background: rgba(8,12,16,0.7); backdrop-filter: blur(12px);
        position: sticky; top: 0; z-index: 10;
      }
      .app-topbar-title { font-size: 14px; font-weight: 700; letter-spacing: -0.01em; }
      .topbar-right { display: flex; align-items: center; gap: 10px; }

      .app-content { padding: 28px; flex: 1; }
      .section-page { display: none; }
      .section-page.active { display: block; }

      .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
      .stat-card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--r-lg); padding: 18px 20px;
      }
      .stat-label { font-size: 11px; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px; }
      .stat-value { font-size: 26px; font-weight: 800; letter-spacing: -0.04em; line-height: 1; }
      .stat-sub { font-size: 12px; color: var(--dim); margin-top: 8px; }

      .pack-row { display: flex; gap: 10px; flex-wrap: wrap; }
      .credit-pack-btn {
        padding: 10px 20px; border-radius: var(--r-sm);
        background: var(--surface-2); border: 1px solid var(--border-strong);
        color: var(--text); font-size: 13px; font-weight: 700;
        cursor: pointer; transition: all 120ms;
      }
      .credit-pack-btn:hover { background: var(--surface-3); border-color: var(--accent-border); color: var(--accent); }

      .key-prefix {
        font-size: 12px; color: var(--muted);
        background: var(--surface-2); border: 1px solid var(--border);
        padding: 3px 8px; border-radius: 6px; font-family: inherit;
      }
      .key-secret-box {
        background: var(--accent-dim); border: 1px solid var(--accent-border);
        border-radius: var(--r-sm); padding: 12px 16px;
        font-size: 12px; color: var(--accent);
        word-break: break-all; line-height: 1.6;
      }

      @media (max-width: 900px) {
        .sidebar { display: none; }
        .stats-grid { grid-template-columns: 1fr 1fr; }
      }
      @media (max-width: 480px) {
        .stats-grid { grid-template-columns: 1fr; }
        .app-content { padding: 16px; }
      }
    """

    body = f'''
      <div class="app-layout">
        <aside class="sidebar">
          <div class="sidebar-brand">
            <div class="brand-icon">N</div>
            {SETTINGS.app_name}
          </div>
          <nav class="sidebar-nav">
            <button class="sidebar-item active" onclick="showSection('overview', this)">
              <span class="sidebar-icon">⊞</span> Overview
            </button>
            <button class="sidebar-item" onclick="showSection('credits', this)">
              <span class="sidebar-icon">⬡</span> Credits
            </button>
            <button class="sidebar-item" onclick="showSection('models', this)">
              <span class="sidebar-icon">◈</span> Models
            </button>
            <button class="sidebar-item" onclick="showSection('keys', this)">
              <span class="sidebar-icon">◎</span> API Keys
            </button>
            <button class="sidebar-item" onclick="showSection('usage', this)">
              <span class="sidebar-icon">▸</span> Usage
            </button>
            <button class="sidebar-item" onclick="showSection('quickstart', this)">
              <span class="sidebar-icon">⟩</span> Quickstart
            </button>
          </nav>
          <div class="sidebar-bottom">
            <div class="account-chip">
              <div class="account-avatar" id="nav-avatar">?</div>
              <div class="account-info">
                <div class="account-email" id="nav-email">Loading...</div>
                <div class="account-plan" id="nav-plan">-</div>
              </div>
            </div>
          </div>
        </aside>

        <div class="app-main">
          <div class="app-topbar">
            <div class="app-topbar-title" id="topbar-section">Overview</div>
            <div class="topbar-right">
              <span class="tag live" id="topbar-status" style="display:none"><span class="dot pulse" style="width:6px;height:6px"></span> Live</span>
              <button class="btn sm" id="refresh-btn">Refresh</button>
              <button class="btn sm danger" id="logout-btn">Sign out</button>
            </div>
          </div>

          <div class="app-content">
            <div class="section-page active" id="section-overview">
              <div class="stats-grid">
                <div class="stat-card">
                  <div class="stat-label">Credit balance</div>
                  <div class="stat-value" id="stat-credits">-</div>
                  <div class="stat-sub">Available for model usage</div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">Plan</div>
                  <div class="stat-value" id="stat-plan" style="font-size:18px">-</div>
                  <div class="stat-sub">Your access tier</div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">Rate limit</div>
                  <div class="stat-value" id="stat-rate" style="font-size:18px">-</div>
                  <div class="stat-sub">Requests per minute</div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">API keys</div>
                  <div class="stat-value" id="stat-keys">-</div>
                  <div class="stat-sub">Active in workspace</div>
                </div>
              </div>
              <div class="grid-2" style="gap:16px">
                <div class="panel">
                  <div class="panel-head">Recent usage</div>
                  <div class="panel-body">
                    <div class="tbl-wrap">
                      <table class="tbl">
                        <thead><tr><th>Model</th><th>Tokens</th><th>Cost</th></tr></thead>
                        <tbody id="overview-usage"><tr><td colspan="3" class="muted">Loading...</td></tr></tbody>
                      </table>
                    </div>
                  </div>
                </div>
                <div class="panel">
                  <div class="panel-head">Active keys</div>
                  <div class="panel-body">
                    <div class="tbl-wrap">
                      <table class="tbl">
                        <thead><tr><th>Name</th><th>Prefix</th><th>Status</th></tr></thead>
                        <tbody id="overview-keys"><tr><td colspan="3" class="muted">Loading...</td></tr></tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="section-page" id="section-credits">
              <div class="panel" style="margin-bottom:20px">
                <div class="panel-head">Current balance</div>
                <div class="panel-body">
                  <div style="font-size:40px;font-weight:800;letter-spacing:-0.04em;color:var(--accent)" id="credits-big">-</div>
                  <div class="muted" style="margin-top:6px;font-size:13px">Available for model usage across all API keys in this workspace.</div>
                </div>
              </div>
              <div class="panel">
                <div class="panel-head">Top up credits</div>
                <div class="panel-body stack">
                  <div class="muted" style="font-size:13px">Choose a credit pack. Your balance is available immediately after checkout confirmation.</div>
                  <div class="pack-row" id="credit-packs"></div>
                  <div id="checkout-status"></div>
                </div>
              </div>
            </div>

            <div class="section-page" id="section-models">
              <div class="panel">
                <div class="panel-head">Available models <span class="tag live" style="font-size:10px">Live catalog</span></div>
                <div class="panel-body">
                  <div class="tbl-wrap">
                    <table class="tbl">
                      <thead><tr><th>Family</th><th>Model ID</th><th>Price</th><th>Status</th><th>Use case</th></tr></thead>
                      <tbody id="models-body"></tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            <div class="section-page" id="section-keys">
              <div class="panel" style="margin-bottom:20px">
                <div class="panel-head">Create a key</div>
                <div class="panel-body">
                  <div class="row">
                    <div class="field" style="flex:1">
                      <label for="key-name">Key name</label>
                      <input id="key-name" type="text" placeholder="Production" />
                    </div>
                    <button class="btn primary" id="create-key-btn" style="align-self:flex-end">Create key</button>
                  </div>
                  <div id="new-key-secret" style="margin-top:14px"></div>
                </div>
              </div>
              <div class="panel">
                <div class="panel-head">All keys</div>
                <div class="panel-body" style="padding:0">
                  <div class="tbl-wrap" style="border:none;border-radius:0">
                    <table class="tbl">
                      <thead><tr><th>Name</th><th>Prefix</th><th>Status</th><th></th></tr></thead>
                      <tbody id="keys-body"><tr><td colspan="4" class="muted">Loading...</td></tr></tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            <div class="section-page" id="section-usage">
              <div class="panel">
                <div class="panel-head">Recent requests <span class="muted" style="font-size:12px;font-weight:400;text-transform:none;letter-spacing:0">Last 5 calls</span></div>
                <div class="panel-body" style="padding:0">
                  <div class="tbl-wrap" style="border:none;border-radius:0">
                    <table class="tbl">
                      <thead><tr><th>Model</th><th>Input tokens</th><th>Output tokens</th><th>Cost</th></tr></thead>
                      <tbody id="usage-body"><tr><td colspan="4" class="muted">Loading...</td></tr></tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            <div class="section-page" id="section-quickstart">
              <div class="grid-2" style="align-items:start">
                <div class="stack">
                  <div class="panel">
                    <div class="panel-head">Test a request</div>
                    <div class="panel-body stack">
                      <div class="field">
                        <label for="model-select">Model</label>
                        <select id="model-select"></select>
                      </div>
                      <div class="field">
                        <label for="prompt">Prompt</label>
                        <textarea id="prompt" placeholder="Write a FastAPI middleware for JWT auth..."></textarea>
                      </div>
                      <div class="row">
                        <button class="btn primary" id="send-btn">Send -></button>
                        <button class="btn ghost" id="copy-snippet-btn">Copy snippet</button>
                      </div>
                      <div id="request-status"></div>
                    </div>
                  </div>
                </div>
                <div class="stack">
                  <div class="panel">
                    <div class="panel-head">Python snippet</div>
                    <div class="panel-body" style="padding:0">
                      <pre class="code-block" id="sdk-snippet" style="border:none;border-radius:0;margin:0;font-size:12px"></pre>
                    </div>
                  </div>
                  <div class="panel">
                    <div class="panel-head">Response</div>
                    <div class="panel-body" style="padding:0">
                      <pre class="code-block" id="output" style="border:none;border-radius:0;margin:0;font-size:12px;white-space:pre-wrap;word-break:break-word">Waiting for a request...</pre>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    '''

    scripts = f'''
      const PACKS = {packs_json};
      const MODEL_FAMILIES = {model_family_json};

      function money(cents) {{
        return '$' + (Number(cents || 0) / 100).toFixed(2);
      }}

      function showSection(name, el) {{
        document.querySelectorAll('.section-page').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.sidebar-item').forEach(s => s.classList.remove('active'));
        document.getElementById('section-' + name).classList.add('active');
        if (el) el.classList.add('active');
        const titles = {{overview:'Overview',credits:'Credits',models:'Models',keys:'API Keys',usage:'Usage',quickstart:'Quickstart'}};
        document.getElementById('topbar-section').textContent = titles[name] || name;
      }}

      function renderSnippet(key = 'YOUR_KEY') {{
        document.getElementById('sdk-snippet').textContent =
          'from openai import OpenAI\\n\\nclient = OpenAI(\\n    api_key="' + key + '",\\n    base_url="{SETTINGS.base_url}/v1",\\n)\\n\\nresponse = client.chat.completions.create(\\n    model="deepseek-v4-flash",\\n    messages=[{{"role": "user", "content": "Hello"}}],\\n)\\nprint(response.choices[0].message.content)';
      }}

      async function loadAccount() {{
        const res = await fetch('/auth/me');
        if (!res.ok) {{ window.location.href = '/login'; return null; }}
        const me = await res.json();
        const bal = money(me.credits_cents);
        document.getElementById('stat-credits').textContent = bal;
        document.getElementById('stat-plan').textContent = me.plan;
        document.getElementById('stat-rate').textContent = me.rate_limit_per_minute + '/min';
        document.getElementById('credits-big').textContent = bal;
        document.getElementById('nav-email').textContent = me.email;
        document.getElementById('nav-plan').textContent = me.plan;
        document.getElementById('nav-avatar').textContent = (me.email || '?')[0].toUpperCase();
        document.getElementById('topbar-status').style.display = '';
        renderSnippet(localStorage.getItem('nr_api_key') || 'YOUR_KEY');
        return me;
      }}

      async function loadModels() {{
        const res = await fetch('/v1/models', {{ headers: {{ 'X-API-Key': localStorage.getItem('nr_api_key') || '' }} }});
        const payload = await res.json();
        const models = payload.data || [];
        const sel = document.getElementById('model-select');
        sel.innerHTML = '';
        const all = models.length ? models : MODEL_FAMILIES.map(m => ({{ id: m.slug }}));
        all.forEach(m => {{
          const o = document.createElement('option');
          o.value = m.id; o.textContent = m.id; sel.appendChild(o);
        }});
        const tbody = document.getElementById('models-body');
        tbody.innerHTML = '';
        MODEL_FAMILIES.forEach(m => {{
          const tr = document.createElement('tr');
          tr.innerHTML = '<td style="font-weight:700">' + m.name + '</td><td><span class="key-prefix">' + m.slug + '</span></td><td style="color:var(--accent);font-weight:700">' + m.price + '<span style="color:var(--dim);font-weight:400;font-size:11px"> ' + m.unit + '</span></td><td><span class="tag ' + (m.status === 'Live' ? 'live' : 'beta') + '">' + m.status + '</span></td><td class="muted" style="font-size:12px">' + m.description + '</td>';
          tbody.appendChild(tr);
        }});
      }}

      function renderCreditPacks() {{
        const c = document.getElementById('credit-packs');
        c.innerHTML = '';
        PACKS.forEach(amount => {{
          const b = document.createElement('button');
          b.className = 'credit-pack-btn';
          b.textContent = 'Add ' + money(amount);
          b.onclick = async () => {{
            document.getElementById('checkout-status').innerHTML = '<div class="alert info">Creating checkout session...</div>';
            const res = await fetch('/v1/billing/checkout', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ amount_cents: amount }}) }});
            const payload = await res.json();
            if (!res.ok) {{ document.getElementById('checkout-status').innerHTML = '<div class="alert error">' + (payload.detail || 'Checkout failed') + '</div>'; return; }}
            window.location.href = payload.checkout_url;
          }};
          c.appendChild(b);
        }});
      }}

      async function loadKeys() {{
        const res = await fetch('/v1/api-keys');
        const payload = await res.json();
        const keys = (payload.data || []);
        document.getElementById('stat-keys').textContent = keys.filter(k => k.active).length;

        function renderKeysTable(tbodyId, limit = Infinity) {{
          const tbody = document.getElementById(tbodyId);
          tbody.innerHTML = '';
          const shown = keys.slice(0, limit);
          if (!shown.length) {{ tbody.innerHTML = '<tr><td colspan="4" class="muted">No keys yet.</td></tr>'; return; }}
          shown.forEach(key => {{
            const tr = document.createElement('tr');
            tr.innerHTML = '<td style="font-weight:600">' + key.name + '</td><td><span class="key-prefix">' + key.prefix + '</span></td><td>' + (key.active ? '<span class="tag live">Active</span>' : '<span class="tag dim">Revoked</span>') + '</td><td>' + (key.active ? '<button class="btn xs danger" data-id="' + key.id + '">Revoke</button>' : '') + '</td>';
            tbody.appendChild(tr);
          }});
          tbody.querySelectorAll('[data-id]').forEach(b => {{
            b.onclick = async () => {{ await fetch('/v1/api-keys/' + b.dataset.id, {{ method: 'DELETE' }}); await loadKeys(); }};
          }});
        }}
        renderKeysTable('keys-body');
        renderKeysTable('overview-keys', 5);
      }}

      async function loadUsage() {{
        const res = await fetch('/v1/usage/recent?limit=5');
        const payload = await res.json();
        const items = payload.data || [];
        function renderUsageTable(tbodyId, cols) {{
          const tbody = document.getElementById(tbodyId);
          tbody.innerHTML = '';
          if (!items.length) {{ tbody.innerHTML = '<tr><td colspan="' + cols + '" class="muted">No usage yet.</td></tr>'; return; }}
          items.forEach(item => {{
            const tr = document.createElement('tr');
            if (cols === 3) {{
              tr.innerHTML = '<td style="font-weight:600">' + item.model + '</td><td>' + ((item.tokens_in||0)+(item.tokens_out||0)) + '</td><td style="color:var(--accent)">' + money(item.cost_cents||0) + '</td>';
            }} else {{
              tr.innerHTML = '<td style="font-weight:600">' + item.model + '</td><td>' + (item.tokens_in||0) + '</td><td>' + (item.tokens_out||0) + '</td><td style="color:var(--accent)">' + money(item.cost_cents||0) + '</td>';
            }}
            tbody.appendChild(tr);
          }});
        }}
        renderUsageTable('overview-usage', 3);
        renderUsageTable('usage-body', 4);
      }}

      document.getElementById('create-key-btn').onclick = async () => {{
        const name = document.getElementById('key-name').value.trim() || 'Default';
        const res = await fetch('/v1/api-keys', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ name }}) }});
        const payload = await res.json();
        const box = document.getElementById('new-key-secret');
        if (!res.ok) {{ box.innerHTML = '<div class="alert error">' + (payload.detail || 'Failed') + '</div>'; return; }}
        localStorage.setItem('nr_api_key', payload.secret);
        box.innerHTML = '<div class="key-secret-box">Copy this key now - it won\\'t be shown again.<br><br><strong>' + payload.secret + '</strong></div>';
        renderSnippet(payload.secret);
        await loadKeys();
      }};

      document.getElementById('send-btn').onclick = async () => {{
        const model = document.getElementById('model-select').value;
        const prompt = document.getElementById('prompt').value.trim();
        const apiKey = localStorage.getItem('nr_api_key') || '';
        const out = document.getElementById('output');
        const st = document.getElementById('request-status');
        if (!apiKey) {{ out.textContent = 'Create an API key (API Keys tab).'; return; }}
        if (!prompt) {{ out.textContent = 'Enter a prompt.'; return; }}
        st.innerHTML = '<div class="alert info"><span class="spin"></span> Sending...</div>';
        const res = await fetch('/v1/chat/completions', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey }}, body: JSON.stringify({{ model, messages: [{{ role: 'user', content: prompt }}] }}) }});
        out.textContent = await res.text();
        st.innerHTML = res.ok ? '<div class="alert success">Request complete</div>' : '<div class="alert error">Request failed</div>';
        await Promise.all([loadUsage(), loadAccount()]);
      }};

      document.getElementById('copy-snippet-btn').onclick = async () => {{
        try {{ await navigator.clipboard.writeText(document.getElementById('sdk-snippet').textContent); document.getElementById('request-status').innerHTML = '<div class="alert success">Copied!</div>'; }} catch(_) {{}}
      }};

      document.getElementById('refresh-btn').onclick = async () => {{
        await Promise.all([loadAccount(), loadModels(), loadKeys(), loadUsage()]);
      }};

      document.getElementById('logout-btn').onclick = async () => {{
        await fetch('/auth/logout', {{ method: 'POST' }});
        window.location.href = '/';
      }};

      const qs = new URLSearchParams(window.location.search).get('checkout');
      if (qs === 'success') {{
        document.getElementById('checkout-status').innerHTML = '<div class="alert success">Payment confirmed. Credits will update shortly.</div>';
        showSection('credits', null);
      }} else if (qs === 'cancelled') {{
        document.getElementById('checkout-status').innerHTML = '<div class="alert error">Checkout cancelled.</div>';
        showSection('credits', null);
      }}

      renderCreditPacks();
      renderSnippet(localStorage.getItem('nr_api_key') || 'YOUR_KEY');
      Promise.all([loadAccount(), loadModels(), loadKeys(), loadUsage()]).catch(() => {{ window.location.href = '/login'; }});
    '''
    return _shell(f'Dashboard | {SETTINGS.app_name}', body, extra_css, scripts)
