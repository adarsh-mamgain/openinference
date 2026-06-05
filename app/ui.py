from __future__ import annotations

from textwrap import dedent

from app.settings import SETTINGS


MODEL_PRICE_MAP = {
    'deepseek-v4-flash': 20,
    'qwen3-32b': 35,
    'llama-4-scout': 40,
}


def _shell(title: str, body: str, scripts: str = '') -> str:
    return dedent(
        f"""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>{title}</title>
            <style>
              :root {{
                color-scheme: light;
                --bg: #f5f7fb;
                --surface: #ffffff;
                --surface-2: #eef2f7;
                --line: #d9e0ea;
                --line-strong: #c5cedb;
                --text: #142033;
                --muted: #5a6980;
                --accent: #2256ff;
                --accent-strong: #1637a6;
                --success: #0f7b49;
                --warn: #a15c00;
                --danger: #b42318;
                --shadow: 0 10px 30px rgba(20, 32, 51, 0.08);
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              }}
              * {{ box-sizing: border-box; }}
              html, body {{ margin: 0; min-height: 100%; background: var(--bg); color: var(--text); }}
              a {{ color: inherit; text-decoration: none; }}
              button, input, select, textarea {{ font: inherit; }}
              .app-shell {{ min-height: 100vh; }}
              .container {{ max-width: 1240px; margin: 0 auto; padding: 0 24px; }}
              .topbar {{
                position: sticky;
                top: 0;
                z-index: 20;
                backdrop-filter: blur(16px);
                background: rgba(245, 247, 251, 0.82);
                border-bottom: 1px solid rgba(217, 224, 234, 0.7);
              }}
              .topbar-inner {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 72px; }}
              .brand {{ display: flex; align-items: center; gap: 12px; }}
              .logo {{
                width: 36px; height: 36px; border-radius: 10px;
                background: linear-gradient(135deg, var(--accent), #47a0ff);
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.2);
              }}
              .brand-mark {{ display: grid; gap: 2px; }}
              .brand-mark strong {{ font-size: 15px; line-height: 1.2; }}
              .brand-mark span {{ font-size: 12px; color: var(--muted); }}
              .nav {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
              .nav a {{ font-size: 13px; color: var(--muted); padding: 8px 10px; border-radius: 999px; }}
              .nav a:hover {{ background: rgba(255,255,255,0.8); color: var(--text); }}
              .button {{
                display: inline-flex; align-items: center; justify-content: center; gap: 8px;
                border: 1px solid var(--line); border-radius: 10px; padding: 11px 14px;
                background: #fff; color: var(--text); cursor: pointer;
              }}
              .button:hover {{ border-color: var(--line-strong); }}
              .button.primary {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
              .button.primary:hover {{ background: var(--accent-strong); border-color: var(--accent-strong); }}
              .button.ghost {{ background: transparent; }}
              .button.small {{ padding: 8px 12px; font-size: 13px; }}
              .hero {{
                padding: 48px 0 24px;
                border-bottom: 1px solid rgba(217, 224, 234, 0.65);
                background:
                  radial-gradient(circle at top right, rgba(34, 86, 255, 0.14), transparent 35%),
                  radial-gradient(circle at bottom left, rgba(18, 170, 94, 0.08), transparent 30%);
              }}
              .hero-grid {{ display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr); gap: 28px; align-items: end; }}
              .eyebrow {{ display: inline-flex; align-items: center; gap: 8px; padding: 7px 11px; border-radius: 999px; background: rgba(255,255,255,0.7); border: 1px solid var(--line); color: var(--muted); font-size: 12px; }}
              h1, h2, h3 {{ margin: 0; }}
              .hero h1 {{ font-size: clamp(38px, 5vw, 64px); line-height: 0.98; letter-spacing: -0.03em; max-width: 12ch; margin-top: 14px; }}
              .hero p {{ margin: 16px 0 0; max-width: 58ch; font-size: 16px; line-height: 1.6; color: var(--muted); }}
              .hero-actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 22px; }}
              .hero-meta {{ display: flex; gap: 18px; flex-wrap: wrap; margin-top: 20px; color: var(--muted); font-size: 13px; }}
              .hero-meta span {{ display: inline-flex; align-items: center; gap: 8px; }}
              .preview {{
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 16px;
                box-shadow: var(--shadow);
                overflow: hidden;
              }}
              .preview-head {{
                display: flex; align-items: center; justify-content: space-between; gap: 12px;
                padding: 14px 16px; background: var(--surface-2); border-bottom: 1px solid var(--line);
              }}
              .preview-head strong {{ font-size: 13px; }}
              .preview-body {{ padding: 16px; display: grid; gap: 12px; }}
              .preview-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
              .preview-card {{ background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 12px; }}
              .preview-card .k {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
              .preview-card .v {{ margin-top: 8px; font-size: 18px; font-weight: 650; }}
              .terminal {{ background: #0d1521; color: #d7e4ff; border-radius: 12px; padding: 14px; font-size: 13px; line-height: 1.5; min-height: 220px; white-space: pre-wrap; word-break: break-word; }}
              .section {{ padding: 24px 0; }}
              .section-head {{ display: flex; align-items: end; justify-content: space-between; gap: 16px; margin-bottom: 16px; }}
              .section-head p {{ margin: 0; color: var(--muted); max-width: 52ch; line-height: 1.6; }}
              .feature-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
              .feature {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 16px; box-shadow: var(--shadow); }}
              .feature h3 {{ font-size: 15px; margin-bottom: 10px; }}
              .feature p {{ margin: 0; color: var(--muted); line-height: 1.55; font-size: 14px; }}
              .feature .tag {{ display: inline-flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 12px; color: var(--muted); }}
              .panel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow); overflow: hidden; }}
              .panel-head {{ padding: 14px 16px; background: var(--surface-2); border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
              .panel-body {{ padding: 16px; }}
              .grid-two {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
              .muted {{ color: var(--muted); }}
              .pill {{ display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 999px; background: #eef3ff; color: var(--accent-strong); font-size: 12px; }}
              .field {{ display: grid; gap: 6px; }}
              .field label {{ font-size: 13px; color: var(--muted); }}
              .field input, .field textarea, .field select {{
                width: 100%; border: 1px solid var(--line); border-radius: 10px; background: #fff; color: var(--text);
                padding: 11px 12px; outline: none;
              }}
              .field input:focus, .field textarea:focus, .field select:focus {{ border-color: rgba(34,86,255,0.55); box-shadow: 0 0 0 3px rgba(34,86,255,0.1); }}
              .field textarea {{ min-height: 160px; resize: vertical; line-height: 1.45; }}
              .stack {{ display: grid; gap: 12px; }}
              .stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
              .stat {{ background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 12px; }}
              .stat .k {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
              .stat .v {{ margin-top: 8px; font-size: 18px; font-weight: 650; word-break: break-word; }}
              .footer {{ padding: 28px 0 36px; color: var(--muted); font-size: 12px; }}
              .table {{ width: 100%; border-collapse: collapse; }}
              .table th, .table td {{ padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: left; font-size: 13px; }}
              .table th {{ color: var(--muted); font-weight: 600; }}
              .sidebar-layout {{ display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 16px; align-items: start; }}
              .sidebar {{ position: sticky; top: 92px; background: var(--surface); border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow); padding: 12px; display: grid; gap: 8px; }}
              .sidebar a {{ display: block; padding: 10px 12px; border-radius: 10px; color: var(--muted); font-size: 13px; }}
              .sidebar a.active, .sidebar a:hover {{ background: var(--surface-2); color: var(--text); }}
              .hidden {{ display: none !important; }}
              @media (max-width: 1080px) {{ .hero-grid, .grid-two, .sidebar-layout {{ grid-template-columns: 1fr; }} .sidebar {{ position: static; }} .feature-grid {{ grid-template-columns: 1fr; }} .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
              @media (max-width: 720px) {{ .container {{ padding: 0 14px; }} .topbar-inner {{ flex-wrap: wrap; padding: 12px 0; }} .stats, .preview-grid {{ grid-template-columns: 1fr; }} .nav {{ width: 100%; }} .nav a {{ padding-left: 0; }} }}
            </style>
          </head>
          <body>
            <div class="app-shell">{body}</div>
            <script>{scripts}</script>
          </body>
        </html>
        """
    ).strip()


def render_landing_page() -> str:
    body = f"""
      <header class="topbar">
        <div class="container topbar-inner">
          <div class="brand">
            <div class="logo"></div>
            <div class="brand-mark">
              <strong>{SETTINGS.app_name}</strong>
              <span>Open-weight model router for product teams</span>
            </div>
          </div>
          <nav class="nav">
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href="/login">Login</a>
            <a class="button primary small" href="/signup">Get access</a>
          </nav>
        </div>
      </header>

      <section class="hero">
        <div class="container hero-grid">
          <div>
            <div class="eyebrow">Self-hosted OpenAI-compatible routing for open-weight models</div>
            <h1>Ship model access without building a routing stack from scratch.</h1>
            <p>
              {SETTINGS.app_name} gives your customers one place to sign in, get keys, see usage, and send requests
              through open models with a simple pricing layer on top.
            </p>
            <div class="hero-actions">
              <a class="button primary" href="/signup">Start a workspace</a>
              <a class="button" href="/login">Sign in</a>
            </div>
            <div class="hero-meta">
              <span>OpenAI-compatible API</span>
              <span>Usage tracking and billing</span>
              <span>Model routing and fallbacks</span>
            </div>
          </div>
          <div class="preview">
            <div class="preview-head">
              <strong>Live routing view</strong>
              <span class="pill">same API your app uses</span>
            </div>
            <div class="preview-body">
              <div class="preview-grid">
                <div class="preview-card"><div class="k">Available models</div><div class="v">3+</div></div>
                <div class="preview-card"><div class="k">Avg markup</div><div class="v">1-5%</div></div>
                <div class="preview-card"><div class="k">Route mode</div><div class="v">cheapest + fast</div></div>
              </div>
              <div class="terminal">POST /v1/chat/completions
X-API-Key: ********
model: deepseek-v4-flash

Response streams back through your router
with usage logging and billing hooks.</div>
            </div>
          </div>
        </div>
      </section>

      <section class="section" id="features">
        <div class="container">
          <div class="section-head">
            <div>
              <h2>Built for the early customer-facing version</h2>
              <p>Minimal pages. Real API endpoints. Enough surface area to sell access and keep the product honest.</p>
            </div>
          </div>
          <div class="feature-grid">
            <article class="feature">
              <div class="tag">1. Router</div>
              <h3>OpenAI-compatible model access</h3>
              <p>Customers use the same chat completions shape they already know, routed through your selected OSS providers.</p>
            </article>
            <article class="feature">
              <div class="tag">2. Account</div>
              <h3>Login, workspace, and billing pages</h3>
              <p>Public site, auth shell, and inner app shell are all in the repo so you can iterate without a front-end rewrite later.</p>
            </article>
            <article class="feature">
              <div class="tag">3. Control plane</div>
              <h3>Usage and rate limits</h3>
              <p>The dashboard can show credits, recent usage, and model availability from the same API and repositories that power requests.</p>
            </article>
          </div>
        </div>
      </section>

      <section class="section" id="pricing">
        <div class="container grid-two">
          <div class="panel">
            <div class="panel-head"><strong>Pricing posture</strong><span class="pill">simple markup</span></div>
            <div class="panel-body stack">
              <div class="muted">Sell access at a thin markup on top of open-weight provider cost.</div>
              <div class="stats">
                <div class="stat"><div class="k">DeepSeek</div><div class="v">~$0.25 / M</div></div>
                <div class="stat"><div class="k">Llama</div><div class="v">~$0.48 / M</div></div>
                <div class="stat"><div class="k">Qwen</div><div class="v">~$0.35 / M</div></div>
                <div class="stat"><div class="k">Markup</div><div class="v">1-5%</div></div>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-head"><strong>First customer flow</strong><span class="pill">what they see</span></div>
            <div class="panel-body stack">
              <div>1. Landing page explains the product.</div>
              <div>2. Login page captures access and routes them into the app.</div>
              <div>3. Inner app shows models, usage, and API access.</div>
              <div>4. Requests go through the same billing-aware API the dashboard uses.</div>
            </div>
          </div>
        </div>
      </section>

      <footer class="footer">
        <div class="container">{SETTINGS.app_name} is tuned for the MVP path: simple, direct, and built around the APIs you already have.</div>
      </footer>
    """
    return _shell(SETTINGS.app_name, body)


def render_login_page() -> str:
    body = f"""
      <header class="topbar">
        <div class="container topbar-inner">
          <div class="brand">
            <div class="logo"></div>
            <div class="brand-mark">
              <strong>{SETTINGS.app_name}</strong>
              <span>Sign in to your workspace</span>
            </div>
          </div>
          <nav class="nav">
            <a href="/">Home</a>
            <a href="/signup">Create account</a>
          </nav>
        </div>
      </header>
      <main class="container" style="padding: 36px 24px 48px;">
        <div class="grid-two" style="align-items: stretch;">
          <section class="panel">
            <div class="panel-head"><strong>Sign in</strong><span class="pill">API-key backed</span></div>
            <div class="panel-body stack">
              <div class="muted">Use the access key issued to your workspace. This keeps the current MVP flow working end-to-end.</div>
              <label class="field">
                <label for="email">Work email</label>
                <input id="email" type="email" placeholder="name@company.com" />
              </label>
              <label class="field">
                <label for="key">Access key</label>
                <input id="key" type="password" placeholder="X-API-Key value" />
              </label>
              <div class="actions" style="display:flex; gap:12px; flex-wrap:wrap;">
                <button class="button primary" id="signin-btn">Sign in</button>
                <a class="button ghost" href="/signup">New workspace</a>
              </div>
              <div class="muted" id="login-status"></div>
            </div>
          </section>
          <aside class="panel">
            <div class="panel-head"><strong>What happens next</strong><span class="pill">inner app</span></div>
            <div class="panel-body stack">
              <div>• Dashboard with models, usage, and credits.</div>
              <div>• OpenAI-compatible request console.</div>
              <div>• Billing rail through Dodo Payments.</div>
              <div>• Rate limiting and usage logging from the same control plane.</div>
            </div>
          </aside>
        </div>
      </main>
    """
    scripts = """
      const signinBtn = document.getElementById('signin-btn');
      const email = document.getElementById('email');
      const key = document.getElementById('key');
      const status = document.getElementById('login-status');
      const presetEmail = new URLSearchParams(window.location.search).get('email');
      if (presetEmail) email.value = presetEmail;
      signinBtn.addEventListener('click', () => {
        const accessKey = key.value.trim();
        if (!accessKey) {
          status.textContent = 'Enter your access key.';
          return;
        }
        localStorage.setItem('openrouter_api_key', accessKey);
        if (email.value.trim()) localStorage.setItem('openrouter_account_email', email.value.trim());
        window.location.href = '/app';
      });
    """
    return _shell(f'Login | {SETTINGS.app_name}', body, scripts)


def render_signup_page() -> str:
    body = f"""
      <header class="topbar">
        <div class="container topbar-inner">
          <div class="brand">
            <div class="logo"></div>
            <div class="brand-mark">
              <strong>{SETTINGS.app_name}</strong>
              <span>Create a workspace</span>
            </div>
          </div>
          <nav class="nav">
            <a href="/">Home</a>
            <a href="/login">Login</a>
          </nav>
        </div>
      </header>
      <main class="container" style="padding: 36px 24px 48px;">
        <div class="grid-two" style="align-items: stretch;">
          <section class="panel">
            <div class="panel-head"><strong>Request access</strong><span class="pill">customer onboarding</span></div>
            <div class="panel-body stack">
              <label class="field"><label for="name">Name</label><input id="name" type="text" placeholder="Your name" /></label>
              <label class="field"><label for="company">Company</label><input id="company" type="text" placeholder="Company name" /></label>
              <label class="field"><label for="work-email">Work email</label><input id="work-email" type="email" placeholder="name@company.com" /></label>
              <label class="field"><label for="use-case">Use case</label><textarea id="use-case" placeholder="RAG, agents, coding assistant, internal tooling..."></textarea></label>
              <div class="actions" style="display:flex; gap:12px; flex-wrap:wrap;">
                <button class="button primary" id="create-btn">Continue</button>
                <a class="button ghost" href="/login">I already have access</a>
              </div>
              <div class="muted" id="signup-status">This MVP currently routes signup into the login flow so you can keep shipping the product shell.</div>
            </div>
          </section>
          <aside class="panel">
            <div class="panel-head"><strong>Customer journey</strong><span class="pill">landing → login → app</span></div>
            <div class="panel-body stack">
              <div>• Landing page sells the product.</div>
              <div>• Signup captures interest and hands off to login.</div>
              <div>• The app shows billing, usage, and API controls.</div>
              <div>• Everything still rides on the same backend APIs.</div>
            </div>
          </aside>
        </div>
      </main>
    """
    scripts = """
      const btn = document.getElementById('create-btn');
      const status = document.getElementById('signup-status');
      btn.addEventListener('click', () => {
        const email = document.getElementById('work-email').value.trim();
        const company = document.getElementById('company').value.trim();
        if (email) localStorage.setItem('openrouter_signup_email', email);
        if (company) localStorage.setItem('openrouter_signup_company', company);
        status.textContent = 'Saved your details locally. Continue to login to enter an access key.';
        window.location.href = '/login' + (email ? ('?email=' + encodeURIComponent(email)) : '');
      });
    """
    return _shell(f'Sign up | {SETTINGS.app_name}', body, scripts)


def render_app_page() -> str:
    body = f"""
      <header class="topbar">
        <div class="container topbar-inner">
          <div class="brand">
            <div class="logo"></div>
            <div class="brand-mark">
              <strong>{SETTINGS.app_name}</strong>
              <span>Workspace dashboard</span>
            </div>
          </div>
          <nav class="nav">
            <a href="/">Landing</a>
            <a href="/login">Login</a>
            <a class="button primary small" href="/signup">New workspace</a>
          </nav>
        </div>
      </header>

      <main class="container" style="padding: 24px 24px 48px;">
        <div class="sidebar-layout">
          <aside class="sidebar">
            <a class="active" href="#overview">Overview</a>
            <a href="#models">Models</a>
            <a href="#usage">Usage</a>
            <a href="#billing">Billing</a>
            <a href="#api">API console</a>
          </aside>

          <section class="stack">
            <div class="panel" id="overview">
              <div class="panel-head">
                <strong>Workspace overview</strong>
                <span class="pill" id="session-status">Checking session</span>
              </div>
              <div class="panel-body stack">
                <div class="stats">
                  <div class="stat"><div class="k">Plan</div><div class="v" id="plan-value">-</div></div>
                  <div class="stat"><div class="k">Credits</div><div class="v" id="credits-value">-</div></div>
                  <div class="stat"><div class="k">Rate limit</div><div class="v" id="rate-limit-value">-</div></div>
                  <div class="stat"><div class="k">Recent spend</div><div class="v" id="spend-value">-</div></div>
                </div>
                <div class="muted" id="account-email">No account loaded.</div>
              </div>
            </div>

            <div class="grid-two">
              <div class="panel" id="models">
                <div class="panel-head"><strong>Available models</strong><span class="pill">/v1/models</span></div>
                <div class="panel-body stack">
                  <table class="table">
                    <thead>
                      <tr><th>Model</th><th>Tier</th><th>Status</th></tr>
                    </thead>
                    <tbody id="models-body">
                      <tr><td colspan="3" class="muted">Loading...</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="panel" id="usage">
                <div class="panel-head"><strong>Recent usage</strong><span class="pill">logged requests</span></div>
                <div class="panel-body stack">
                  <table class="table">
                    <thead>
                      <tr><th>Model</th><th>Tokens</th><th>Cost</th></tr>
                    </thead>
                    <tbody id="usage-body">
                      <tr><td colspan="3" class="muted">Loading...</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div class="grid-two">
              <div class="panel" id="billing">
                <div class="panel-head"><strong>Billing</strong><span class="pill">Dodo Payments</span></div>
                <div class="panel-body stack">
                  <div class="muted">This MVP stores credit balances in the control plane and uses Dodo Payments for the checkout rail.</div>
                  <div class="stats">
                    <div class="stat"><div class="k">API key</div><div class="v" id="key-state">Missing</div></div>
                    <div class="stat"><div class="k">Usage window</div><div class="v">Live</div></div>
                    <div class="stat"><div class="k">Invoice status</div><div class="v">Tracked</div></div>
                    <div class="stat"><div class="k">Support</div><div class="v">Email</div></div>
                  </div>
                </div>
              </div>

              <div class="panel" id="api">
                <div class="panel-head"><strong>API console</strong><span class="pill">OpenAI-compatible</span></div>
                <div class="panel-body stack">
                  <label class="field">
                    <label for="model-select">Model</label>
                    <select id="model-select"></select>
                  </label>
                  <label class="field">
                    <label for="prompt">Prompt</label>
                    <textarea id="prompt" placeholder="Ask your model something short."></textarea>
                  </label>
                  <div class="grid-two">
                    <label class="field"><label for="temperature">Temperature</label><input id="temperature" type="number" min="0" max="2" step="0.1" value="0.2" /></label>
                    <label class="field"><label for="max-tokens">Max tokens</label><input id="max-tokens" type="number" min="1" step="1" value="512" /></label>
                  </div>
                  <div class="actions" style="display:flex; gap:12px; flex-wrap:wrap;">
                    <button class="button primary" id="send-btn">Send request</button>
                    <button class="button" id="refresh-btn">Refresh data</button>
                  </div>
                  <pre class="terminal" id="output">Waiting for request...</pre>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    """
    scripts = """
      const output = document.getElementById('output');
      const sessionStatus = document.getElementById('session-status');
      const modelsBody = document.getElementById('models-body');
      const usageBody = document.getElementById('usage-body');
      const modelSelect = document.getElementById('model-select');
      const accountEmail = document.getElementById('account-email');
      const planValue = document.getElementById('plan-value');
      const creditsValue = document.getElementById('credits-value');
      const rateLimitValue = document.getElementById('rate-limit-value');
      const spendValue = document.getElementById('spend-value');
      const keyState = document.getElementById('key-state');
      const sendBtn = document.getElementById('send-btn');
      const refreshBtn = document.getElementById('refresh-btn');
      const MODEL_PRICE_MAP = __MODEL_PRICE_MAP__;

      function accessKey() {
        return localStorage.getItem('openrouter_api_key') || '';
      }

      function money(cents) {
        return '$' + (Number(cents || 0) / 100).toFixed(2);
      }

      function requireAuth() {
        const key = accessKey();
        if (!key) {
          sessionStatus.textContent = 'Login required';
          sessionStatus.style.background = '#fff3cd';
          sessionStatus.style.color = '#7a4b00';
          output.textContent = 'No access key stored. Redirecting to login...';
          setTimeout(() => { window.location.href = '/login'; }, 400);
          return false;
        }
        keyState.textContent = 'Loaded';
        return true;
      }

      async function loadModels() {
        const res = await fetch('/v1/models');
        const payload = await res.json();
        const models = payload.data || [];
        modelSelect.innerHTML = '';
        modelsBody.innerHTML = '';
        for (const model of models) {
          const option = document.createElement('option');
          option.value = model.id;
          option.textContent = model.id;
          modelSelect.appendChild(option);
          const row = document.createElement('tr');
          row.innerHTML = `<td>${model.id}</td><td>OSS route</td><td>Ready</td>`;
          modelsBody.appendChild(row);
        }
        if (models.length === 0) {
          modelsBody.innerHTML = '<tr><td colspan="3" class="muted">No models configured.</td></tr>';
        }
      }

      async function loadAccount() {
        const res = await fetch('/v1/me', { headers: { 'X-API-Key': accessKey() } });
        if (!res.ok) throw new Error('Unable to load account');
        const me = await res.json();
        accountEmail.textContent = me.email || localStorage.getItem('openrouter_account_email') || 'No email on file';
        planValue.textContent = me.plan;
        creditsValue.textContent = money(me.credits_cents);
        rateLimitValue.textContent = String(me.rate_limit_per_minute) + '/min';
      }

      async function loadUsage() {
        const res = await fetch('/v1/usage/recent?limit=5', { headers: { 'X-API-Key': accessKey() } });
        if (!res.ok) throw new Error('Unable to load usage');
        const payload = await res.json();
        const items = payload.data || [];
        usageBody.innerHTML = '';
        spendValue.textContent = money(payload.total_cost_cents || 0);
        if (items.length === 0) {
          usageBody.innerHTML = '<tr><td colspan="3" class="muted">No usage yet.</td></tr>';
          return;
        }
        for (const item of items) {
          const row = document.createElement('tr');
          const total = (item.tokens_in || 0) + (item.tokens_out || 0);
          row.innerHTML = `<td>${item.model}</td><td>${total}</td><td>${money(item.cost_cents || 0)}</td>`;
          usageBody.appendChild(row);
        }
      }

      async function refreshAll() {
        if (!requireAuth()) return;
        await Promise.all([loadModels(), loadAccount(), loadUsage()]);
        sessionStatus.textContent = 'Signed in';
        sessionStatus.style.background = '#e9f7ef';
        sessionStatus.style.color = '#0f7b49';
      }

      async function sendRequest() {
        if (!requireAuth()) return;
        const model = modelSelect.value;
        const prompt = document.getElementById('prompt').value.trim();
        const temperature = Number(document.getElementById('temperature').value || 0.2);
        const maxTokens = Number(document.getElementById('max-tokens').value || 512);
        if (!prompt) {
          output.textContent = 'Enter a prompt first.';
          return;
        }
        output.textContent = 'Sending request...';
        const res = await fetch('/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': accessKey(),
          },
          body: JSON.stringify({
            model,
            messages: [
              { role: 'system', content: 'You are a concise assistant.' },
              { role: 'user', content: prompt },
            ],
            temperature,
            max_tokens: maxTokens,
          }),
        });
        const text = await res.text();
        output.textContent = text;
        await loadUsage().catch(() => null);
      }

      refreshBtn.addEventListener('click', () => refreshAll().catch(err => { output.textContent = String(err); }));
      sendBtn.addEventListener('click', () => sendRequest().catch(err => { output.textContent = String(err); }));

      refreshAll().catch(err => {
        output.textContent = String(err);
        sessionStatus.textContent = 'Needs login';
      });
    """.replace("__MODEL_PRICE_MAP__", repr(MODEL_PRICE_MAP))
    return _shell(f'App | {SETTINGS.app_name}', body, scripts)
