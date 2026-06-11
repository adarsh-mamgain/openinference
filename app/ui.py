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
    },
    {
        'name': 'Qwen',
        'slug': 'qwen3-32b',
        'status': 'Live',
        'description': 'Strong coding and multilingual coverage for product workloads.',
    },
    {
        'name': 'Llama',
        'slug': 'llama-4-scout',
        'status': 'Live',
        'description': 'High-capacity open-weight model for broad assistant use cases.',
    },
    {
        'name': 'Mistral',
        'slug': 'mistral-small-3.1',
        'status': 'Routing ready',
        'description': 'A compact family slot for latency-sensitive work and fallbacks.',
    },
    {
        'name': 'Gemma',
        'slug': 'gemma-3-27b',
        'status': 'Routing ready',
        'description': 'An efficient open model family for lightweight interactive tasks.',
    },
]


def _shell(title: str, body: str, scripts: str = '') -> str:
    return dedent(
        f'''
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <meta name="color-scheme" content="light dark" />
            <title>{title}</title>
            <style>
              :root {{
                color-scheme: light;
                --bg: #f4f5f7;
                --bg-alt: #edf1f5;
                --surface: rgba(255, 255, 255, 0.92);
                --surface-strong: #ffffff;
                --surface-soft: #f7f9fb;
                --line: rgba(19, 27, 38, 0.08);
                --line-strong: rgba(19, 27, 38, 0.14);
                --text: #111827;
                --muted: #5f6b7a;
                --accent: #1f5cff;
                --accent-strong: #1745c7;
                --success: #0d7a46;
                --warning: #8b5e12;
                --danger: #c0362c;
                --shadow: 0 18px 54px rgba(16, 24, 40, 0.08);
                --radius-xl: 28px;
                --radius-lg: 20px;
                --radius-md: 14px;
                --radius-sm: 10px;
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
              }}

              @media (prefers-color-scheme: dark) {{
                :root {{
                  color-scheme: dark;
                  --bg: #0b0f14;
                  --bg-alt: #0f141b;
                  --surface: rgba(14, 19, 26, 0.92);
                  --surface-strong: #111722;
                  --surface-soft: #0f1621;
                  --line: rgba(255, 255, 255, 0.08);
                  --line-strong: rgba(255, 255, 255, 0.16);
                  --text: #e7edf4;
                  --muted: #9aa6b2;
                  --shadow: 0 18px 54px rgba(0, 0, 0, 0.34);
                }}
              }}

              * {{ box-sizing: border-box; }}
              html {{ scroll-behavior: smooth; }}
              body {{
                margin: 0;
                min-height: 100%;
                background:
                  linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 180px),
                  var(--bg);
                color: var(--text);
              }}
              body::before {{
                content: '';
                position: fixed;
                inset: 0;
                pointer-events: none;
                background-image: linear-gradient(rgba(127, 138, 151, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(127, 138, 151, 0.08) 1px, transparent 1px);
                background-size: 42px 42px;
                mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.14), transparent 70%);
                opacity: 0.35;
              }}
              a {{ color: inherit; text-decoration: none; }}
              button, input, select, textarea {{ font: inherit; }}
              button {{ cursor: pointer; }}
              ::selection {{ background: rgba(31, 92, 255, 0.18); }}
              .container {{ max-width: 1280px; margin: 0 auto; padding: 0 24px; }}
              .shell {{ position: relative; z-index: 1; }}
              .topbar {{
                position: sticky;
                top: 0;
                z-index: 20;
                border-bottom: 1px solid var(--line);
                background: color-mix(in srgb, var(--bg) 84%, transparent);
                backdrop-filter: blur(18px);
              }}
              .topbar-inner {{
                min-height: 74px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 18px;
              }}
              .brand {{ display: inline-flex; align-items: center; gap: 12px; }}
              .brand-badge {{
                width: 38px;
                height: 38px;
                border-radius: 13px;
                background: linear-gradient(135deg, var(--accent), #63a5ff);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
              }}
              .brand-mark {{ display: grid; gap: 2px; }}
              .brand-mark strong {{ font-size: 15px; line-height: 1.15; letter-spacing: -0.01em; }}
              .brand-mark span {{ font-size: 12px; color: var(--muted); }}
              .nav {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
              .nav a, .nav button {{
                border: 1px solid transparent;
                border-radius: 999px;
                padding: 9px 13px;
                color: var(--muted);
                background: transparent;
                transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
              }}
              .nav a:hover, .nav button:hover {{
                background: var(--surface);
                border-color: var(--line);
                color: var(--text);
              }}
              .button {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                border: 1px solid var(--line-strong);
                border-radius: 12px;
                padding: 11px 15px;
                background: var(--surface-strong);
                color: var(--text);
                transition: transform 160ms ease, border-color 160ms ease, background 160ms ease, color 160ms ease;
              }}
              .button:hover {{ transform: translateY(-1px); border-color: rgba(31, 92, 255, 0.28); }}
              .button.primary {{ background: var(--accent); border-color: var(--accent); color: #fff; box-shadow: 0 14px 24px rgba(31, 92, 255, 0.18); }}
              .button.primary:hover {{ background: var(--accent-strong); border-color: var(--accent-strong); }}
              .button.ghost {{ background: transparent; }}
              .button.small {{ padding: 8px 12px; font-size: 13px; }}
              .button.tiny {{ padding: 7px 10px; font-size: 12px; border-radius: 10px; }}
              .badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 7px 12px;
                border: 1px solid var(--line-strong);
                border-radius: 999px;
                background: var(--surface);
                color: var(--muted);
                font-size: 12px;
                letter-spacing: 0.01em;
              }}
              .badge strong {{ color: var(--text); }}
              .badge.success {{ color: var(--success); background: rgba(13, 122, 70, 0.08); border-color: rgba(13, 122, 70, 0.16); }}
              .badge.warning {{ color: var(--warning); background: rgba(139, 94, 18, 0.08); border-color: rgba(139, 94, 18, 0.16); }}
              .badge.accent {{ color: var(--accent); background: rgba(31, 92, 255, 0.08); border-color: rgba(31, 92, 255, 0.16); }}
              .page {{ padding: 30px 0 44px; }}
              .hero {{ padding: 58px 0 30px; }}
              .hero-grid {{
                display: grid;
                grid-template-columns: minmax(0, 1.08fr) minmax(340px, 0.92fr);
                gap: 24px;
                align-items: start;
              }}
              .eyebrow {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 8px 12px;
                border: 1px solid var(--line-strong);
                border-radius: 999px;
                background: var(--surface);
                color: var(--muted);
                font-size: 12px;
              }}
              .eyebrow-dot {{ width: 7px; height: 7px; border-radius: 999px; background: var(--accent); box-shadow: 0 0 0 4px rgba(31, 92, 255, 0.12); }}
              h1 {{
                margin: 18px 0 0;
                font-size: clamp(44px, 6vw, 76px);
                line-height: 0.94;
                letter-spacing: -0.05em;
                max-width: 11ch;
              }}
              .hero-copy {{ max-width: 60ch; margin-top: 18px; color: var(--muted); font-size: 17px; line-height: 1.65; }}
              .hero-actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 26px; }}
              .hero-points {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 22px; }}
              .proof-bar {{
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 12px;
                margin-top: 28px;
              }}
              .proof-card {{
                padding: 14px 16px;
                border-radius: 16px;
                background: var(--surface);
                border: 1px solid var(--line);
              }}
              .proof-card .k {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }}
              .proof-card .v {{ margin-top: 8px; font-size: 18px; font-weight: 650; letter-spacing: -0.02em; }}
              .preview {{
                border: 1px solid var(--line-strong);
                border-radius: var(--radius-xl);
                background: var(--surface);
                box-shadow: var(--shadow);
                overflow: hidden;
              }}
              .preview-head {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                padding: 16px 18px;
                border-bottom: 1px solid var(--line);
                background: var(--surface-soft);
              }}
              .preview-body {{ padding: 18px; display: grid; gap: 16px; }}
              .preview-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
              .metric {{
                padding: 14px;
                border-radius: 16px;
                border: 1px solid var(--line);
                background: var(--surface-strong);
              }}
              .metric .k {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }}
              .metric .v {{ margin-top: 8px; font-size: 20px; font-weight: 700; letter-spacing: -0.03em; }}
              .metric .s {{ margin-top: 6px; color: var(--muted); font-size: 12px; line-height: 1.5; }}
              .terminal {{
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                background: #0b1220;
                color: #dce7ff;
                padding: 16px;
                font-size: 13px;
                line-height: 1.6;
                white-space: pre-wrap;
                word-break: break-word;
                overflow: auto;
              }}
              .section {{ padding: 24px 0; }}
              .section-head {{ display: flex; align-items: end; justify-content: space-between; gap: 16px; margin-bottom: 16px; }}
              .section-head h2 {{ margin: 0; font-size: clamp(24px, 3vw, 34px); letter-spacing: -0.03em; }}
              .section-head p {{ margin: 0; max-width: 56ch; color: var(--muted); line-height: 1.6; }}
              .grid-two {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
              .grid-three {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
              .grid-five {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }}
              .stack {{ display: grid; gap: 12px; }}
              .panel {{
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: var(--radius-lg);
                box-shadow: var(--shadow);
                overflow: hidden;
              }}
              .panel-head {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                padding: 16px 18px;
                background: var(--surface-soft);
                border-bottom: 1px solid var(--line);
              }}
              .panel-head strong {{ font-size: 15px; letter-spacing: -0.01em; }}
              .panel-body {{ padding: 18px; }}
              .feature {{
                padding: 18px;
                border-radius: 18px;
                border: 1px solid var(--line);
                background: var(--surface);
                box-shadow: var(--shadow);
              }}
              .feature h3 {{ margin: 0 0 10px; font-size: 15px; letter-spacing: -0.01em; }}
              .feature p {{ margin: 0; color: var(--muted); line-height: 1.6; font-size: 14px; }}
              .feature .mini {{ margin-top: 14px; color: var(--text); font-size: 13px; }}
              .model-card {{
                padding: 16px;
                border-radius: 18px;
                border: 1px solid var(--line);
                background: var(--surface);
                display: grid;
                gap: 10px;
              }}
              .model-card .top {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
              .model-card .name {{ font-size: 15px; font-weight: 650; letter-spacing: -0.01em; }}
              .model-card .slug {{ font-size: 12px; color: var(--muted); word-break: break-word; }}
              .model-card .desc {{ color: var(--muted); font-size: 13px; line-height: 1.55; }}
              .pricing {{ display: grid; grid-template-columns: minmax(0, 1.06fr) minmax(0, 0.94fr); gap: 16px; }}
              .price-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
              .price {{
                padding: 16px;
                border-radius: 18px;
                border: 1px solid var(--line);
                background: var(--surface-strong);
              }}
              .price .k {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }}
              .price .v {{ margin-top: 8px; font-size: 28px; letter-spacing: -0.04em; font-weight: 750; }}
              .price .s {{ margin-top: 8px; color: var(--muted); line-height: 1.55; font-size: 13px; }}
              .faq {{ display: grid; gap: 12px; }}
              .faq-item {{
                border: 1px solid var(--line);
                border-radius: 18px;
                background: var(--surface);
                padding: 16px 18px;
              }}
              .faq-item summary {{ cursor: pointer; font-weight: 650; list-style: none; }}
              .faq-item summary::-webkit-details-marker {{ display: none; }}
              .faq-item p {{ margin: 10px 0 0; color: var(--muted); line-height: 1.6; }}
              .footer {{ padding: 30px 0 38px; color: var(--muted); font-size: 13px; }}
              .sidebar-layout {{ display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 18px; align-items: start; }}
              .sidebar {{
                position: sticky;
                top: 92px;
                display: grid;
                gap: 8px;
                padding: 12px;
                border-radius: var(--radius-lg);
                border: 1px solid var(--line);
                background: var(--surface);
                box-shadow: var(--shadow);
              }}
              .sidebar a {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                padding: 11px 12px;
                border-radius: 12px;
                color: var(--muted);
              }}
              .sidebar a.active, .sidebar a:hover {{ background: var(--surface-soft); color: var(--text); }}
              .dashboard-top {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                padding: 16px 18px;
                border: 1px solid var(--line);
                border-radius: var(--radius-lg);
                background: var(--surface);
                box-shadow: var(--shadow);
              }}
              .dashboard-top .left {{ display: grid; gap: 6px; }}
              .dashboard-top h1 {{ margin: 0; font-size: 24px; line-height: 1.1; letter-spacing: -0.03em; }}
              .dashboard-top p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
              .command-bar {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
              .search {{
                min-width: 280px;
                flex: 1 1 280px;
                border: 1px solid var(--line-strong);
                background: var(--surface-strong);
                border-radius: 12px;
                padding: 11px 14px;
                color: var(--text);
              }}
              .search:focus {{ outline: 0; border-color: rgba(31, 92, 255, 0.38); box-shadow: 0 0 0 4px rgba(31, 92, 255, 0.12); }}
              .kpi-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
              .kpi {{
                padding: 16px;
                border-radius: 18px;
                border: 1px solid var(--line);
                background: var(--surface);
              }}
              .kpi .k {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }}
              .kpi .v {{ margin-top: 8px; font-size: 28px; line-height: 1; font-weight: 760; letter-spacing: -0.04em; }}
              .kpi .s {{ margin-top: 7px; color: var(--muted); font-size: 13px; line-height: 1.5; }}
              .field {{ display: grid; gap: 7px; }}
              .field label {{ color: var(--muted); font-size: 13px; }}
              .field input, .field textarea, .field select {{
                width: 100%;
                border: 1px solid var(--line-strong);
                border-radius: 12px;
                background: var(--surface-strong);
                color: var(--text);
                padding: 11px 13px;
                outline: none;
              }}
              .field input:focus, .field textarea:focus, .field select:focus {{ border-color: rgba(31, 92, 255, 0.4); box-shadow: 0 0 0 4px rgba(31, 92, 255, 0.11); }}
              .field textarea {{ min-height: 136px; resize: vertical; line-height: 1.55; }}
              .table-wrap {{ overflow: auto; border-radius: 16px; border: 1px solid var(--line); }}
              .table {{ width: 100%; border-collapse: collapse; background: var(--surface); }}
              .table th, .table td {{ padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; font-size: 13px; vertical-align: top; }}
              .table th {{ color: var(--muted); font-weight: 600; background: var(--surface-soft); }}
              .table tr:last-child td {{ border-bottom: 0; }}
              .muted {{ color: var(--muted); }}
              .split {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 0.84fr); gap: 16px; }}
              .mini-list {{ display: grid; gap: 10px; }}
              .mini-item {{ display: flex; align-items: start; justify-content: space-between; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--line); }}
              .mini-item:last-child {{ border-bottom: 0; padding-bottom: 0; }}
              .mini-item .title {{ font-size: 14px; font-weight: 650; }}
              .mini-item .sub {{ color: var(--muted); font-size: 12px; margin-top: 4px; line-height: 1.45; }}
              .mini-item .meta {{ color: var(--muted); font-size: 12px; white-space: nowrap; }}
              .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
              .hidden {{ display: none !important; }}
              .reveal {{ animation: reveal 560ms cubic-bezier(0.2, 0.9, 0.2, 1) both; }}
              @keyframes reveal {{
                from {{ opacity: 0; transform: translateY(12px); }}
                to {{ opacity: 1; transform: translateY(0); }}
              }}
              @media (max-width: 1180px) {{
                .hero-grid, .sidebar-layout, .pricing, .split {{ grid-template-columns: 1fr; }}
                .grid-five {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
                .kpi-grid, .proof-bar, .preview-grid, .grid-three, .price-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
                .sidebar {{ position: static; }}
              }}
              @media (max-width: 760px) {{
                .container {{ padding: 0 16px; }}
                .topbar-inner {{ min-height: auto; padding: 14px 0; flex-wrap: wrap; }}
                .nav {{ width: 100%; }}
                .nav a, .nav button {{ width: 100%; justify-content: center; }}
                .hero {{ padding-top: 28px; }}
                h1 {{ max-width: 100%; }}
                .proof-bar, .kpi-grid, .grid-three, .grid-two, .preview-grid, .grid-five, .price-grid {{ grid-template-columns: 1fr; }}
                .command-bar {{ display: grid; }}
                .search {{ min-width: 0; width: 100%; }}
                .dashboard-top {{ flex-direction: column; align-items: stretch; }}
                .section-head {{ flex-direction: column; align-items: start; }}
              }}
            </style>
          </head>
          <body>
            <div class="shell">
              {body}
            </div>
            <script>{scripts}</script>
          </body>
        </html>
        '''
    ).strip()


def render_landing_page() -> str:
    body = f'''
      <header class="topbar">
        <div class="container topbar-inner">
          <div class="brand">
            <div class="brand-badge"></div>
            <div class="brand-mark">
              <strong>{SETTINGS.app_name}</strong>
              <span>Reload credits, keep a 5% fee, and route to the best open models</span>
            </div>
          </div>
          <nav class="nav">
            <a href="#models">Models</a>
            <a href="#pricing">Pricing</a>
            <a href="#faq">FAQ</a>
            <a href="/login">Login</a>
            <a class="button primary small" href="/signup">Get access</a>
          </nav>
        </div>
      </header>
      <main>
        <section class="hero">
          <div class="container hero-grid reveal">
            <div>
              <div class="eyebrow"><span class="eyebrow-dot"></span> OpenAI-compatible routing for open-weight models</div>
              <h1>The fastest way to sell OSS model access with credits.</h1>
              <p class="hero-copy">Users top up their account with credits, you collect a 5% platform fee on reloads, and they immediately start using the five OSS model families that matter: DeepSeek, Qwen, Llama, Mistral, and Gemma.</p>
              <div class="hero-actions">
                <a class="button primary" href="/signup">Create workspace</a>
                <a class="button" href="/login">Sign in</a>
                <a class="button ghost" href="#pricing">See pricing</a>
              </div>
              <div class="hero-points">
                <span class="badge accent"><strong>5%</strong> platform fee</span>
                <span class="badge success"><strong>Credits</strong> first checkout flow</span>
                <span class="badge"><strong>OpenAI</strong> SDK compatible</span>
              </div>
              <div class="proof-bar">
                <div class="proof-card"><div class="k">Model families</div><div class="v">5 OSS</div></div>
                <div class="proof-card"><div class="k">Checkout flow</div><div class="v">Reload</div></div>
                <div class="proof-card"><div class="k">Fee model</div><div class="v">5%</div></div>
                <div class="proof-card"><div class="k">API surface</div><div class="v">/v1</div></div>
              </div>
            </div>
            <aside class="preview">
              <div class="preview-head">
                <strong>What the customer sees</strong>
                <span class="badge">Top-up -> route -> use</span>
              </div>
              <div class="preview-body">
                <div class="preview-grid">
                  <div class="metric">
                    <div class="k">Credit balance</div>
                    <div class="v">$128.00</div>
                    <div class="s">Visible in the workspace as soon as the checkout webhook confirms payment.</div>
                  </div>
                  <div class="metric">
                    <div class="k">Platform fee</div>
                    <div class="v">5%</div>
                    <div class="s">Simple markup on reloads so the product stays easy to explain and easy to buy.</div>
                  </div>
                  <div class="metric">
                    <div class="k">Model access</div>
                    <div class="v">5 OSS</div>
                    <div class="s">Only the top open-weight families, so the UX stays focused and defensible.</div>
                  </div>
                </div>
                <pre class="terminal">curl {SETTINGS.base_url}/v1/chat/completions \
  -H "Authorization: Bearer or_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{{"model":"deepseek-v4-flash","messages":[{{"role":"user","content":"Ship a product roadmap"}}]}}'</pre>
              </div>
            </aside>
          </div>
        </section>

        <section class="section">
          <div class="container">
            <div class="section-head">
              <div>
                <h2>Built around the exact customer journey</h2>
                <p>One public landing page, one auth flow, one dashboard, and one API. The user reloads credits, you keep the 5% fee, and the model experience stays invisible.</p>
              </div>
            </div>
            <div class="grid-three">
              <article class="feature reveal">
                <h3>1. Acquire</h3>
                <p>Visitors land on a product that explains the value in one sentence: pay once, top up credits, and start using open models immediately.</p>
                <div class="mini">Clear CTA: create a workspace.</div>
              </article>
              <article class="feature reveal">
                <h3>2. Fund</h3>
                <p>The dashboard centers credit reloads with Dodo Payments. The platform fee is simple, visible, and easy to explain.</p>
                <div class="mini">Checkout amount, credit balance, fee retention.</div>
              </article>
              <article class="feature reveal">
                <h3>3. Run</h3>
                <p>Users create API keys and send OpenAI-compatible requests against your `/v1` endpoint without learning a new SDK.</p>
                <div class="mini">No custom client needed.</div>
              </article>
            </div>
          </div>
        </section>

        <section class="section" id="models">
          <div class="container">
            <div class="section-head">
              <div>
                <h2>Top five OSS model families</h2>
                <p>These are the five model families the product is built to sell. The dashboard pulls the active selector from the API, while the landing page communicates the broader catalog.</p>
              </div>
              <span class="badge">Open-weight only</span>
            </div>
            <div class="grid-five">
              {''.join(
                  f'''<article class="model-card reveal"><div class="top"><div class="name">{model['name']}</div><span class="badge {'success' if model['status'] == 'Live' else 'warning'}">{model['status']}</span></div><div class="slug">{model['slug']}</div><div class="desc">{model['description']}</div></article>'''
                  for model in MODEL_FAMILIES
              )}
            </div>
          </div>
        </section>

        <section class="section" id="pricing">
          <div class="container pricing">
            <div class="panel reveal">
              <div class="panel-head"><strong>Pricing posture</strong><span class="badge accent">5% fee on reload</span></div>
              <div class="panel-body stack">
                <div class="muted">Keep the business simple: the user tops up credits, your checkout collects a 5% platform fee, and the balance becomes available for model usage.</div>
                <div class="price-grid">
                  <div class="price"><div class="k">Starter reload</div><div class="v">$25</div><div class="s">A low-friction entry point for trials and first production workloads.</div></div>
                  <div class="price"><div class="k">Team reload</div><div class="v">$100</div><div class="s">The default pack for teams that want stable usage with clear spend control.</div></div>
                  <div class="price"><div class="k">Platform fee</div><div class="v">5%</div><div class="s">Transparent markup that keeps the product economics straightforward.</div></div>
                </div>
              </div>
            </div>
            <div class="panel reveal">
              <div class="panel-head"><strong>Why customers buy</strong><span class="badge">Fast onboarding</span></div>
              <div class="panel-body mini-list">
                <div class="mini-item"><div><div class="title">No procurement delay</div><div class="sub">Card-funded credit reloads remove the back-and-forth of invoices for small teams.</div></div><div class="meta">Immediate access</div></div>
                <div class="mini-item"><div><div class="title">Simple spend controls</div><div class="sub">Users can keep a working balance and top up as they consume tokens.</div></div><div class="meta">Predictable costs</div></div>
                <div class="mini-item"><div><div class="title">One API surface</div><div class="sub">They keep using OpenAI-compatible clients while you handle routing and billing behind the scenes.</div></div><div class="meta">Low switching cost</div></div>
              </div>
            </div>
          </div>
        </section>

        <section class="section" id="faq">
          <div class="container">
            <div class="section-head">
              <div>
                <h2>FAQ</h2>
                <p>Answer the questions buyers will ask before they register, reload credits, and start sending requests.</p>
              </div>
            </div>
            <div class="faq">
              <details class="faq-item reveal">
                <summary>How do users pay?</summary>
                <p>They open the dashboard, choose a credit pack, and complete checkout. The 5% fee is part of the platform economics, not a separate product.</p>
              </details>
              <details class="faq-item reveal">
                <summary>What models are available?</summary>
                <p>The product is focused on the top five open-weight families: DeepSeek, Qwen, Llama, Mistral, and Gemma.</p>
              </details>
              <details class="faq-item reveal">
                <summary>Can they use the OpenAI SDK?</summary>
                <p>Yes. The UI and API are built around the standard `/v1/chat/completions` flow so teams do not need a custom client.</p>
              </details>
            </div>
          </div>
        </section>

        <section class="section">
          <div class="container">
            <div class="panel reveal">
              <div class="panel-head"><strong>Ready to launch</strong><span class="badge accent">Reload credits, route requests</span></div>
              <div class="panel-body split">
                <div>
                  <h2 class="section-title">Open the workspace and start the first credit reload.</h2>
                  <p class="muted section-copy">The app is designed to move a visitor from curiosity to funded usage in one flow: create a workspace, top up credits, create a key, and call the API.</p>
                </div>
                <div class="hero-actions compact">
                  <a class="button primary" href="/signup">Create workspace</a>
                  <a class="button" href="/login">Sign in</a>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <footer class="footer"><div class="container">{SETTINGS.app_name} keeps the MVP narrow: one credit system, one fee model, and five OSS families for production routing.</div></footer>
    '''
    return _shell(SETTINGS.app_name, body)


def render_login_page() -> str:
    body = f'''
      <header class="topbar">
        <div class="container topbar-inner">
          <div class="brand">
            <div class="brand-badge"></div>
            <div class="brand-mark">
              <strong>{SETTINGS.app_name}</strong>
              <span>Sign in to reload credits and manage keys</span>
            </div>
          </div>
          <nav class="nav">
            <a href="/">Home</a>
            <a href="/signup">Create account</a>
          </nav>
        </div>
      </header>
      <main class="page">
        <div class="container grid-two">
          <section class="panel reveal">
            <div class="panel-head"><strong>Sign in</strong><span class="badge">Workspace access</span></div>
            <div class="panel-body stack">
              <p class="muted section-copy">Use the email and password tied to your workspace. Once signed in, you can load credits, create API keys, and start consuming the open model catalog.</p>
              <label class="field"><label for="login-email">Work email</label><input id="login-email" type="email" placeholder="name@company.com" autocomplete="email" /></label>
              <label class="field"><label for="login-password">Password</label><input id="login-password" type="password" placeholder="Enter your password" autocomplete="current-password" /></label>
              <div class="hero-actions"><button class="button primary" id="login-btn">Sign in</button><a class="button" href="/signup">Create workspace</a></div>
              <div class="muted" id="login-status" role="status" aria-live="polite"></div>
            </div>
          </section>
          <aside class="panel reveal">
            <div class="panel-head"><strong>What happens next</strong><span class="badge accent">Three steps</span></div>
            <div class="panel-body mini-list">
              <div class="mini-item"><div><div class="title">Load credits</div><div class="sub">Choose a pack and complete the checkout in seconds.</div></div><div class="meta">Step 1</div></div>
              <div class="mini-item"><div><div class="title">Create API keys</div><div class="sub">Issue unlimited keys for apps, environments, and services.</div></div><div class="meta">Step 2</div></div>
              <div class="mini-item"><div><div class="title">Start routing</div><div class="sub">Use the OpenAI SDK against your `/v1` endpoint and the live model selector.</div></div><div class="meta">Step 3</div></div>
            </div>
          </aside>
        </div>
      </main>
    '''
    scripts = '''
      const btn = document.getElementById('login-btn');
      const status = document.getElementById('login-status');
      btn.addEventListener('click', async () => {
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        if (!email || !password) {
          status.textContent = 'Enter email and password.';
          return;
        }
        status.textContent = 'Signing in...';
        const res = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        const payload = await res.json();
        if (!res.ok) {
          status.textContent = payload.detail || 'Login failed';
          return;
        }
        window.location.href = '/app';
      });
    '''
    return _shell(f'Login | {SETTINGS.app_name}', body, scripts)


def render_signup_page() -> str:
    body = f'''
      <header class="topbar">
        <div class="container topbar-inner">
          <div class="brand">
            <div class="brand-badge"></div>
            <div class="brand-mark">
              <strong>{SETTINGS.app_name}</strong>
              <span>Create a workspace and start a credit reload</span>
            </div>
          </div>
          <nav class="nav">
            <a href="/">Home</a>
            <a href="/login">Login</a>
          </nav>
        </div>
      </header>
      <main class="page">
        <div class="container grid-two">
          <section class="panel reveal">
            <div class="panel-head"><strong>Register</strong><span class="badge">Workspace owner</span></div>
            <div class="panel-body stack">
              <p class="muted section-copy">Create the workspace that will hold credits, keys, and usage. The sign-up flow is intentionally short so users get to funding and model usage quickly.</p>
              <label class="field"><label for="signup-name">Name</label><input id="signup-name" type="text" placeholder="Your name" autocomplete="name" /></label>
              <label class="field"><label for="signup-email">Work email</label><input id="signup-email" type="email" placeholder="name@company.com" autocomplete="email" /></label>
              <label class="field"><label for="signup-password">Password</label><input id="signup-password" type="password" placeholder="Create a password" autocomplete="new-password" /></label>
              <div class="hero-actions"><button class="button primary" id="signup-btn">Create workspace</button><a class="button" href="/login">I already have access</a></div>
              <div class="muted" id="signup-status" role="status" aria-live="polite"></div>
            </div>
          </section>
          <aside class="panel reveal">
            <div class="panel-head"><strong>Why this flow works</strong><span class="badge accent">Credits first</span></div>
            <div class="panel-body mini-list">
              <div class="mini-item"><div><div class="title">Fast registration</div><div class="sub">No lengthy setup forms or enterprise detours.</div></div><div class="meta">Low friction</div></div>
              <div class="mini-item"><div><div class="title">Immediate reload</div><div class="sub">Users can fund the account as soon as the workspace exists.</div></div><div class="meta">Monetize early</div></div>
              <div class="mini-item"><div><div class="title">Open model access</div><div class="sub">The workspace connects to the five OSS model families the product is built around.</div></div><div class="meta">Clear promise</div></div>
            </div>
          </aside>
        </div>
      </main>
    '''
    scripts = '''
      const btn = document.getElementById('signup-btn');
      const status = document.getElementById('signup-status');
      btn.addEventListener('click', async () => {
        const name = document.getElementById('signup-name').value.trim();
        const email = document.getElementById('signup-email').value.trim();
        const password = document.getElementById('signup-password').value;
        if (!email || !password) {
          status.textContent = 'Enter email and password.';
          return;
        }
        status.textContent = 'Creating workspace...';
        const res = await fetch('/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password }),
        });
        const payload = await res.json();
        if (!res.ok) {
          status.textContent = payload.detail || 'Registration failed';
          return;
        }
        window.location.href = '/app';
      });
    '''
    return _shell(f'Sign up | {SETTINGS.app_name}', body, scripts)


def render_app_page() -> str:
    packs_json = json.dumps(CREDIT_PACKS)
    model_family_json = json.dumps(MODEL_FAMILIES)
    body = f'''
      <header class="topbar">
        <div class="container topbar-inner">
          <div class="brand">
            <div class="brand-badge"></div>
            <div class="brand-mark">
              <strong>{SETTINGS.app_name}</strong>
              <span>Workspace dashboard for credits, keys, and model access</span>
            </div>
          </div>
          <div class="nav">
            <a href="/">Landing</a>
            <button class="button small" id="logout-btn">Logout</button>
          </div>
        </div>
      </header>
      <main class="page">
        <div class="container sidebar-layout">
          <aside class="sidebar" aria-label="Dashboard sections">
            <a class="active" href="#overview">Overview <span>01</span></a>
            <a href="#funding">Credits <span>02</span></a>
            <a href="#catalog">Models <span>03</span></a>
            <a href="#keys">API keys <span>04</span></a>
            <a href="#usage">Usage <span>05</span></a>
            <a href="#api">Quickstart <span>06</span></a>
          </aside>
          <section class="stack">
            <div class="dashboard-top reveal" id="overview">
              <div class="left">
                <div class="chips">
                  <span class="badge success">Signed in</span>
                  <span class="badge accent">5% fee on reload</span>
                  <span class="badge">OpenAI-compatible</span>
                </div>
                <h1>Manage credits, keys, and model access in one workspace.</h1>
                <p>Fund the account, keep a visible balance, and start routing requests through the top OSS families without leaving the app.</p>
              </div>
              <div class="command-bar">
                <input class="search" id="dashboard-search" type="search" placeholder="Search models, keys, or usage..." aria-label="Search dashboard" />
                <button class="button" id="refresh-btn">Refresh</button>
              </div>
            </div>

            <div class="kpi-grid reveal">
              <div class="kpi"><div class="k">Email</div><div class="v" id="account-email">-</div><div class="s">Current workspace owner.</div></div>
              <div class="kpi"><div class="k">Plan</div><div class="v" id="plan-value">-</div><div class="s">Access tier for this workspace.</div></div>
              <div class="kpi"><div class="k">Credits</div><div class="v" id="credits-value">-</div><div class="s">Available balance for model usage.</div></div>
              <div class="kpi"><div class="k">Rate limit</div><div class="v" id="rate-limit-value">-</div><div class="s">Protection against runaway usage.</div></div>
            </div>

            <div class="split">
              <section class="panel reveal" id="funding">
                <div class="panel-head"><strong>Reload credits</strong><span class="badge accent">Dodo Payments</span></div>
                <div class="panel-body stack">
                  <p class="muted section-copy">Choose a reload size. The customer pays once, the account is credited after confirmation, and the platform keeps the 5% fee from the reload flow.</p>
                  <div class="chips" id="credit-packs"></div>
                  <div class="muted" id="checkout-status" role="status" aria-live="polite"></div>
                </div>
              </section>

              <section class="panel reveal" id="catalog">
                <div class="panel-head"><strong>Model catalog</strong><span class="badge">Top 5 OSS families</span></div>
                <div class="panel-body stack">
                  <div class="mini-list" id="catalog-list"></div>
                </div>
              </section>
            </div>

            <div class="grid-two">
              <section class="panel reveal" id="keys">
                <div class="panel-head"><strong>API keys</strong><span class="badge">Unlimited</span></div>
                <div class="panel-body stack">
                  <div class="grid-two">
                    <label class="field"><label for="key-name">Key name</label><input id="key-name" type="text" placeholder="Production" /></label>
                    <div class="stack action-stack"><button class="button primary" id="create-key-btn">Create key</button></div>
                  </div>
                  <div class="muted" id="new-key-secret" role="status" aria-live="polite"></div>
                  <div class="table-wrap">
                    <table class="table">
                      <thead><tr><th>Name</th><th>Prefix</th><th>Status</th><th></th></tr></thead>
                      <tbody id="keys-body"><tr><td colspan="4" class="muted">Loading...</td></tr></tbody>
                    </table>
                  </div>
                </div>
              </section>

              <section class="panel reveal" id="usage">
                <div class="panel-head"><strong>Recent usage</strong><span class="badge">Token spend</span></div>
                <div class="panel-body stack">
                  <div class="table-wrap">
                    <table class="table">
                      <thead><tr><th>Model</th><th>Tokens</th><th>Cost</th></tr></thead>
                      <tbody id="usage-body"><tr><td colspan="3" class="muted">Loading...</td></tr></tbody>
                    </table>
                  </div>
                  <div class="mini-list">
                    <div class="mini-item"><div><div class="title">Cost visibility</div><div class="sub">Keep usage visible so the reload flow remains understandable and predictable.</div></div><div class="meta" id="usage-total">0 tokens</div></div>
                    <div class="mini-item"><div><div class="title">Billing posture</div><div class="sub">The platform fee is applied on reload, while the account balance covers model consumption.</div></div><div class="meta">5%</div></div>
                  </div>
                </div>
              </section>
            </div>

            <section class="panel reveal" id="api">
              <div class="panel-head"><strong>SDK quickstart</strong><span class="badge">OpenAI format</span></div>
              <div class="panel-body grid-two">
                <div class="stack">
                  <p class="muted section-copy">Create a key, paste it into your app, and point the OpenAI client at your `/v1` endpoint.</p>
                  <label class="field"><label for="model-select">Live model selector</label><select id="model-select"></select></label>
                  <label class="field"><label for="prompt">Prompt</label><textarea id="prompt" placeholder="Ask for a product spec, a code review, or a support reply."></textarea></label>
                  <div class="hero-actions">
                    <button class="button primary" id="send-btn">Send request</button>
                    <button class="button" id="copy-snippet-btn">Copy snippet</button>
                  </div>
                  <div class="muted" id="request-status" role="status" aria-live="polite"></div>
                </div>
                <div class="stack">
                  <pre class="terminal" id="sdk-snippet"></pre>
                  <pre class="terminal" id="output">Waiting for a request...</pre>
                </div>
              </div>
            </section>
          </section>
        </div>
      </main>
    '''
    scripts = f'''
      const PACKS = {packs_json};
      const MODEL_FAMILIES = {model_family_json};
      const status = document.getElementById('request-status');
      const checkoutStatus = document.getElementById('checkout-status');
      const newKeySecret = document.getElementById('new-key-secret');
      const keysBody = document.getElementById('keys-body');
      const usageBody = document.getElementById('usage-body');
      const usageTotal = document.getElementById('usage-total');
      const modelSelect = document.getElementById('model-select');
      const sdkSnippet = document.getElementById('sdk-snippet');
      const output = document.getElementById('output');
      const catalogList = document.getElementById('catalog-list');
      const packContainer = document.getElementById('credit-packs');
      const search = document.getElementById('dashboard-search');

      function money(cents) {{
        return '$' + (Number(cents || 0) / 100).toFixed(2);
      }}

      function renderSdkSnippet(key = 'YOUR_API_KEY') {{
        sdkSnippet.textContent = `from openai import OpenAI\n\nclient = OpenAI(\n  api_key="${{key}}",\n  base_url="{SETTINGS.base_url}/v1",\n)\n\nresponse = client.chat.completions.create(\n  model="deepseek-v4-flash",\n  messages=[{{"role": "user", "content": "Build me a launch page"}}],\n)\nprint(response.choices[0].message.content)`;
      }}

      async function ensureSession() {{
        const res = await fetch('/auth/me');
        if (!res.ok) {{
          window.location.href = '/login';
          return null;
        }}
        return await res.json();
      }}

      async function loadAccount() {{
        const me = await ensureSession();
        if (!me) return null;
        document.getElementById('account-email').textContent = me.email;
        document.getElementById('plan-value').textContent = me.plan;
        document.getElementById('credits-value').textContent = money(me.credits_cents);
        document.getElementById('rate-limit-value').textContent = String(me.rate_limit_per_minute) + '/min';
        status.textContent = 'Signed in';
        renderSdkSnippet(localStorage.getItem('openrouter_api_key') || 'YOUR_API_KEY');
        return me;
      }}

      async function loadModels() {{
        const res = await fetch('/v1/models', {{ headers: {{ 'X-API-Key': localStorage.getItem('openrouter_api_key') || '' }} }});
        const payload = await res.json();
        const models = payload.data || [];
        modelSelect.innerHTML = '';
        models.forEach((model) => {{
          const option = document.createElement('option');
          option.value = model.id;
          option.textContent = model.id;
          modelSelect.appendChild(option);
        }});
        if (!models.length) {{
          const option = document.createElement('option');
          option.value = 'deepseek-v4-flash';
          option.textContent = 'deepseek-v4-flash';
          modelSelect.appendChild(option);
        }}
      }}

      function renderCatalog() {{
        catalogList.innerHTML = '';
        MODEL_FAMILIES.forEach((model) => {{
          const row = document.createElement('div');
          row.className = 'mini-item';
          row.innerHTML = `
            <div>
              <div class="title">${{model.name}}</div>
              <div class="sub">${{model.slug}} · ${{model.description}}</div>
            </div>
            <div class="meta">${{model.status}}</div>
          `;
          catalogList.appendChild(row);
        }});
      }}

      function renderCreditPacks() {{
        packContainer.innerHTML = '';
        PACKS.forEach((amount) => {{
          const button = document.createElement('button');
          button.className = 'button';
          button.textContent = 'Reload ' + money(amount);
          button.addEventListener('click', async () => {{
            checkoutStatus.textContent = 'Creating checkout...';
            const res = await fetch('/v1/billing/checkout', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ amount_cents: amount }}),
            }});
            const payload = await res.json();
            if (!res.ok) {{
              checkoutStatus.textContent = payload.detail || 'Checkout failed';
              return;
            }}
            window.location.href = payload.checkout_url;
          }});
          packContainer.appendChild(button);
        }});
      }}

      async function loadKeys() {{
        const res = await fetch('/v1/api-keys');
        const payload = await res.json();
        const keys = payload.data || [];
        keysBody.innerHTML = '';
        if (!keys.length) {{
          keysBody.innerHTML = '<tr><td colspan="4" class="muted">No API keys yet.</td></tr>';
          return;
        }}
        keys.forEach((key) => {{
          const row = document.createElement('tr');
          row.dataset.searchText = [key.name, key.prefix, key.active ? 'active' : 'revoked'].join(' ').toLowerCase();
          row.innerHTML = `<td>${{key.name}}</td><td>${{key.prefix}}</td><td>${{key.active ? 'Active' : 'Revoked'}}</td><td>${{key.active ? '<button class="button tiny" data-id="' + key.id + '">Revoke</button>' : ''}}</td>`;
          keysBody.appendChild(row);
        }});
        keysBody.querySelectorAll('button[data-id]').forEach((button) => {{
          button.addEventListener('click', async () => {{
            await fetch('/v1/api-keys/' + button.dataset.id, {{ method: 'DELETE' }});
            await loadKeys();
          }});
        }});
      }}

      async function loadUsage() {{
        const res = await fetch('/v1/usage/recent?limit=5');
        const payload = await res.json();
        const items = payload.data || [];
        usageBody.innerHTML = '';
        const totalTokens = payload.total_tokens || 0;
        usageTotal.textContent = totalTokens ? String(totalTokens) + ' tokens' : '0 tokens';
        if (!items.length) {{
          usageBody.innerHTML = '<tr><td colspan="3" class="muted">No usage yet.</td></tr>';
          return;
        }}
        items.forEach((item) => {{
          const total = (item.tokens_in || 0) + (item.tokens_out || 0);
          const row = document.createElement('tr');
          row.dataset.searchText = [item.model, String(total), String(item.cost_cents || 0)].join(' ').toLowerCase();
          row.innerHTML = `<td>${{item.model}}</td><td>${{total}}</td><td>${{money(item.cost_cents || 0)}}</td>`;
          usageBody.appendChild(row);
        }});
      }}

      document.getElementById('create-key-btn').addEventListener('click', async () => {{
        const name = document.getElementById('key-name').value.trim() || 'Default';
        const res = await fetch('/v1/api-keys', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ name }}),
        }});
        const payload = await res.json();
        if (!res.ok) {{
          newKeySecret.textContent = payload.detail || 'Could not create key';
          return;
        }}
        localStorage.setItem('openrouter_api_key', payload.secret);
        newKeySecret.textContent = 'New secret created. Copy it now: ' + payload.secret;
        renderSdkSnippet(payload.secret);
        await loadKeys();
      }});

      document.getElementById('send-btn').addEventListener('click', async () => {{
        const model = modelSelect.value;
        const prompt = document.getElementById('prompt').value.trim();
        const apiKey = localStorage.getItem('openrouter_api_key') || '';
        if (!apiKey) {{
          output.textContent = 'Create an API key first.';
          return;
        }}
        if (!prompt) {{
          output.textContent = 'Enter a prompt.';
          return;
        }}
        status.textContent = 'Sending request...';
        const res = await fetch('/v1/chat/completions', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + apiKey,
          }},
          body: JSON.stringify({{ model, messages: [{{ role: 'user', content: prompt }}] }}),
        }});
        output.textContent = await res.text();
        status.textContent = res.ok ? 'Request complete' : 'Request failed';
        await Promise.all([loadUsage(), loadAccount()]);
      }});

      document.getElementById('copy-snippet-btn').addEventListener('click', async () => {{
        try {{
          await navigator.clipboard.writeText(sdkSnippet.textContent);
          status.textContent = 'Snippet copied';
        }} catch (_) {{
          status.textContent = 'Clipboard unavailable';
        }}
      }});

      document.getElementById('refresh-btn').addEventListener('click', async () => {{
        await Promise.all([loadAccount(), loadModels(), loadKeys(), loadUsage()]);
        status.textContent = 'Refreshed';
      }});

      document.getElementById('logout-btn').addEventListener('click', async () => {{
        await fetch('/auth/logout', {{ method: 'POST' }});
        window.location.href = '/';
      }});

      search.addEventListener('input', () => {{
        const query = search.value.trim().toLowerCase();
        document.querySelectorAll('[data-search-text]').forEach((node) => {{
          const text = node.dataset.searchText || '';
          node.classList.toggle('hidden', Boolean(query) && !text.includes(query));
        }});
      }});

      renderCreditPacks();
      renderCatalog();
      renderSdkSnippet(localStorage.getItem('openrouter_api_key') || 'YOUR_API_KEY');
      const checkoutState = new URLSearchParams(window.location.search).get('checkout');
      if (checkoutState === 'success') {{
        checkoutStatus.textContent = 'Checkout completed. Credits update after payment confirmation.';
      }} else if (checkoutState === 'cancelled') {{
        checkoutStatus.textContent = 'Checkout cancelled.';
      }}

      Promise.all([loadAccount(), loadModels(), loadKeys(), loadUsage()]).catch(() => {{
        window.location.href = '/login';
      }});
    '''
    return _shell(f'App | {SETTINGS.app_name}', body, scripts)
