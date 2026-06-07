from __future__ import annotations

import json
from textwrap import dedent

from app.settings import SETTINGS


CREDIT_PACKS = [1000, 2500, 5000]


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
                --text: #142033;
                --muted: #5a6980;
                --accent: #2256ff;
                --accent-strong: #1637a6;
                --success: #0f7b49;
                --warning: #8a5b00;
                --danger: #b42318;
                --shadow: 0 10px 30px rgba(20, 32, 51, 0.08);
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              }}
              * {{ box-sizing: border-box; }}
              html, body {{ margin: 0; min-height: 100%; background: var(--bg); color: var(--text); }}
              a {{ color: inherit; text-decoration: none; }}
              button, input, select, textarea {{ font: inherit; }}
              .container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}
              .topbar {{ position: sticky; top: 0; z-index: 20; background: rgba(245,247,251,0.86); backdrop-filter: blur(14px); border-bottom: 1px solid rgba(217,224,234,0.8); }}
              .topbar-inner {{ min-height: 70px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
              .brand {{ display: flex; align-items: center; gap: 12px; }}
              .logo {{ width: 36px; height: 36px; border-radius: 11px; background: linear-gradient(135deg, var(--accent), #47a0ff); }}
              .brand-mark {{ display: grid; gap: 2px; }}
              .brand-mark strong {{ font-size: 15px; line-height: 1.2; }}
              .brand-mark span {{ font-size: 12px; color: var(--muted); }}
              .nav {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
              .nav a {{ color: var(--muted); font-size: 13px; padding: 8px 10px; border-radius: 999px; }}
              .nav a:hover {{ background: #fff; color: var(--text); }}
              .button {{
                display: inline-flex; align-items: center; justify-content: center; gap: 8px;
                border: 1px solid var(--line); border-radius: 10px; padding: 11px 14px;
                background: #fff; color: var(--text); cursor: pointer;
              }}
              .button.primary {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
              .button.primary:hover {{ background: var(--accent-strong); border-color: var(--accent-strong); }}
              .button.small {{ padding: 8px 12px; font-size: 13px; }}
              .panel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow); overflow: hidden; }}
              .panel-head {{ padding: 14px 16px; background: var(--surface-2); border-bottom: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
              .panel-body {{ padding: 16px; }}
              .grid-two {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
              .grid-three {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
              .stack {{ display: grid; gap: 12px; }}
              .field {{ display: grid; gap: 6px; }}
              .field label {{ font-size: 13px; color: var(--muted); }}
              .field input, .field textarea, .field select {{ width: 100%; border: 1px solid var(--line); border-radius: 10px; background: #fff; padding: 11px 12px; color: var(--text); outline: none; }}
              .field input:focus, .field textarea:focus, .field select:focus {{ border-color: rgba(34,86,255,0.55); box-shadow: 0 0 0 3px rgba(34,86,255,0.1); }}
              .field textarea {{ min-height: 140px; resize: vertical; line-height: 1.45; }}
              .muted {{ color: var(--muted); }}
              .pill {{ display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 999px; background: #eef3ff; color: var(--accent-strong); font-size: 12px; }}
              .hero {{ padding: 52px 0 28px; border-bottom: 1px solid rgba(217,224,234,0.65); }}
              .hero-grid {{ display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr); gap: 24px; align-items: end; }}
              .eyebrow {{ display: inline-flex; align-items: center; gap: 8px; padding: 7px 11px; border-radius: 999px; background: #fff; border: 1px solid var(--line); color: var(--muted); font-size: 12px; }}
              .hero h1 {{ margin: 14px 0 0; font-size: clamp(40px, 5vw, 64px); line-height: 0.98; letter-spacing: -0.03em; max-width: 12ch; }}
              .hero p {{ margin: 16px 0 0; max-width: 58ch; font-size: 16px; line-height: 1.6; color: var(--muted); }}
              .hero-actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 22px; }}
              .hero-meta {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 18px; color: var(--muted); font-size: 13px; }}
              .preview {{ background: var(--surface); border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow); overflow: hidden; }}
              .preview-head {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 14px 16px; background: var(--surface-2); border-bottom: 1px solid var(--line); }}
              .preview-body {{ padding: 16px; display: grid; gap: 12px; }}
              .preview-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
              .preview-card {{ background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 12px; }}
              .preview-card .k {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
              .preview-card .v {{ margin-top: 8px; font-size: 18px; font-weight: 650; }}
              .terminal {{ background: #0d1521; color: #d7e4ff; border-radius: 12px; padding: 14px; font-size: 13px; line-height: 1.5; min-height: 220px; white-space: pre-wrap; word-break: break-word; }}
              .section {{ padding: 24px 0; }}
              .feature-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
              .feature {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 16px; box-shadow: var(--shadow); }}
              .feature h3 {{ margin: 0 0 10px; font-size: 15px; }}
              .feature p {{ margin: 0; color: var(--muted); line-height: 1.55; font-size: 14px; }}
              .table {{ width: 100%; border-collapse: collapse; }}
              .table th, .table td {{ padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: left; font-size: 13px; vertical-align: top; }}
              .table th {{ color: var(--muted); font-weight: 600; }}
              .stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
              .stat {{ background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 12px; }}
              .stat .k {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
              .stat .v {{ margin-top: 8px; font-size: 18px; font-weight: 650; word-break: break-word; }}
              .sidebar-layout {{ display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 16px; align-items: start; }}
              .sidebar {{ position: sticky; top: 90px; background: var(--surface); border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow); padding: 12px; display: grid; gap: 8px; }}
              .sidebar a {{ display: block; padding: 10px 12px; border-radius: 10px; color: var(--muted); font-size: 13px; }}
              .sidebar a.active, .sidebar a:hover {{ background: var(--surface-2); color: var(--text); }}
              .footer {{ padding: 28px 0 36px; color: var(--muted); font-size: 12px; }}
              .hidden {{ display: none !important; }}
              @media (max-width: 1080px) {{ .hero-grid, .grid-two, .grid-three, .sidebar-layout {{ grid-template-columns: 1fr; }} .feature-grid {{ grid-template-columns: 1fr; }} .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .sidebar {{ position: static; }} }}
              @media (max-width: 720px) {{ .container {{ padding: 0 14px; }} .topbar-inner {{ flex-wrap: wrap; padding: 12px 0; }} .stats, .preview-grid {{ grid-template-columns: 1fr; }} .nav {{ width: 100%; }} }}
            </style>
          </head>
          <body>
            {body}
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
            <p>{SETTINGS.app_name} gives your customers a place to register, load credits, manage unlimited API keys, and send requests through a simple OpenAI-compatible API.</p>
            <div class="hero-actions">
              <a class="button primary" href="/signup">Start a workspace</a>
              <a class="button" href="/login">Sign in</a>
            </div>
            <div class="hero-meta">
              <span>OpenAI-compatible API</span>
              <span>Usage tracking and billing</span>
              <span>Five OSS models only</span>
            </div>
          </div>
          <div class="preview">
            <div class="preview-head"><strong>Live routing view</strong><span class="pill">same API your app uses</span></div>
            <div class="preview-body">
              <div class="preview-grid">
                <div class="preview-card"><div class="k">Available models</div><div class="v">5</div></div>
                <div class="preview-card"><div class="k">Markup</div><div class="v">1-5%</div></div>
                <div class="preview-card"><div class="k">Billing</div><div class="v">Dodo</div></div>
              </div>
              <div class="terminal">curl https://your-domain/v1/chat/completions \
  -H "Authorization: Bearer or_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{{"model":"deepseek-v4-flash","messages":[{{"role":"user","content":"Hello"}}]}}'</div>
            </div>
          </div>
        </div>
      </section>
      <section class="section" id="features">
        <div class="container">
          <div class="feature-grid">
            <article class="feature"><h3>Customer accounts</h3><p>Users register, log in, and land in a dashboard that shows credits, usage, and API key management.</p></article>
            <article class="feature"><h3>Unlimited keys</h3><p>Each workspace can create as many API keys as it needs, with revocation and usage tracking.</p></article>
            <article class="feature"><h3>OpenAI SDK flow</h3><p>Customers use the normal OpenAI client format against your `/v1` endpoint.</p></article>
          </div>
        </div>
      </section>
      <section class="section" id="pricing">
        <div class="container grid-two">
          <div class="panel">
            <div class="panel-head"><strong>Pricing posture</strong><span class="pill">simple markup</span></div>
            <div class="panel-body stack">
              <div class="muted">Sell access at a thin markup on top of the OSS provider cost. Keep the product predictable.</div>
              <div class="stats">
                <div class="stat"><div class="k">DeepSeek</div><div class="v">~$0.25 / M</div></div>
                <div class="stat"><div class="k">Llama</div><div class="v">~$0.48 / M</div></div>
                <div class="stat"><div class="k">Qwen</div><div class="v">~$0.35 / M</div></div>
                <div class="stat"><div class="k">Models</div><div class="v">5 only</div></div>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-head"><strong>Customer journey</strong><span class="pill">landing → auth → app</span></div>
            <div class="panel-body stack">
              <div>1. Public landing page explains the offer.</div>
              <div>2. Login/signup creates a workspace.</div>
              <div>3. Dashboard handles credits, keys, and usage.</div>
              <div>4. API keys power SDK usage against your router.</div>
            </div>
          </div>
        </div>
      </section>
      <footer class="footer"><div class="container">{SETTINGS.app_name} keeps the MVP narrow: one product, five OSS models, one API surface, one customer flow.</div></footer>
    """
    return _shell(SETTINGS.app_name, body)


def render_login_page() -> str:
    body = f"""
      <header class="topbar"><div class="container topbar-inner"><div class="brand"><div class="logo"></div><div class="brand-mark"><strong>{SETTINGS.app_name}</strong><span>Sign in to your workspace</span></div></div><nav class="nav"><a href="/">Home</a><a href="/signup">Create account</a></nav></div></header>
      <main class="container" style="padding:36px 0 48px;">
        <div class="grid-two">
          <section class="panel">
            <div class="panel-head"><strong>Sign in</strong><span class="pill">session cookie</span></div>
            <div class="panel-body stack">
              <div class="muted">Use the email/password pair you registered with.</div>
              <label class="field"><label for="login-email">Work email</label><input id="login-email" type="email" placeholder="name@company.com" /></label>
              <label class="field"><label for="login-password">Password</label><input id="login-password" type="password" placeholder="••••••••" /></label>
              <div class="hero-actions"><button class="button primary" id="login-btn">Sign in</button><a class="button" href="/signup">Need an account?</a></div>
              <div class="muted" id="login-status"></div>
            </div>
          </section>
          <aside class="panel"><div class="panel-head"><strong>What happens next</strong><span class="pill">dashboard</span></div><div class="panel-body stack"><div>• View credits and usage.</div><div>• Buy more credits.</div><div>• Create API keys for SDK use.</div><div>• Send OpenAI-style requests through your router.</div></div></aside>
        </div>
      </main>
    """
    scripts = """
      const btn = document.getElementById('login-btn');
      const status = document.getElementById('login-status');
      btn.addEventListener('click', async () => {
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        if (!email || !password) { status.textContent = 'Enter email and password.'; return; }
        const res = await fetch('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
        const payload = await res.json();
        if (!res.ok) { status.textContent = payload.detail || 'Login failed'; return; }
        window.location.href = '/app';
      });
    """
    return _shell(f'Login | {SETTINGS.app_name}', body, scripts)


def render_signup_page() -> str:
    body = f"""
      <header class="topbar"><div class="container topbar-inner"><div class="brand"><div class="logo"></div><div class="brand-mark"><strong>{SETTINGS.app_name}</strong><span>Create your workspace</span></div></div><nav class="nav"><a href="/">Home</a><a href="/login">Login</a></nav></div></header>
      <main class="container" style="padding:36px 0 48px;">
        <div class="grid-two">
          <section class="panel">
            <div class="panel-head"><strong>Register</strong><span class="pill">workspace owner</span></div>
            <div class="panel-body stack">
              <label class="field"><label for="signup-name">Name</label><input id="signup-name" type="text" placeholder="Your name" /></label>
              <label class="field"><label for="signup-email">Work email</label><input id="signup-email" type="email" placeholder="name@company.com" /></label>
              <label class="field"><label for="signup-password">Password</label><input id="signup-password" type="password" placeholder="Create a password" /></label>
              <div class="hero-actions"><button class="button primary" id="signup-btn">Create workspace</button><a class="button" href="/login">I already have access</a></div>
              <div class="muted" id="signup-status"></div>
            </div>
          </section>
          <aside class="panel"><div class="panel-head"><strong>Customer flow</strong><span class="pill">landing → auth → app</span></div><div class="panel-body stack"><div>• Register a new workspace.</div><div>• Load credits in the dashboard.</div><div>• Issue unlimited API keys.</div><div>• Use the SDK with your new key.</div></div></aside>
        </div>
      </main>
    """
    scripts = """
      const btn = document.getElementById('signup-btn');
      const status = document.getElementById('signup-status');
      btn.addEventListener('click', async () => {
        const name = document.getElementById('signup-name').value.trim();
        const email = document.getElementById('signup-email').value.trim();
        const password = document.getElementById('signup-password').value;
        if (!email || !password) { status.textContent = 'Enter email and password.'; return; }
        const res = await fetch('/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, email, password }) });
        const payload = await res.json();
        if (!res.ok) { status.textContent = payload.detail || 'Registration failed'; return; }
        window.location.href = '/app';
      });
    """
    return _shell(f'Sign up | {SETTINGS.app_name}', body, scripts)


def render_app_page() -> str:
    packs_json = json.dumps(CREDIT_PACKS)
    body = f"""
      <header class="topbar"><div class="container topbar-inner"><div class="brand"><div class="logo"></div><div class="brand-mark"><strong>{SETTINGS.app_name}</strong><span>Workspace dashboard</span></div></div><div class="nav"><a href="/">Landing</a><button class="button small" id="logout-btn">Logout</button></div></div></header>
      <main class="container" style="padding:24px 0 48px;">
        <div class="sidebar-layout">
          <aside class="sidebar">
            <a class="active" href="#overview">Overview</a>
            <a href="#credits">Credits</a>
            <a href="#keys">API Keys</a>
            <a href="#usage">Usage</a>
            <a href="#api">SDK</a>
          </aside>
          <section class="stack">
            <div class="panel" id="overview">
              <div class="panel-head"><strong>Workspace overview</strong><span class="pill" id="session-status">Checking session</span></div>
              <div class="panel-body stack">
                <div class="stats">
                  <div class="stat"><div class="k">Email</div><div class="v" id="account-email">-</div></div>
                  <div class="stat"><div class="k">Plan</div><div class="v" id="plan-value">-</div></div>
                  <div class="stat"><div class="k">Credits</div><div class="v" id="credits-value">-</div></div>
                  <div class="stat"><div class="k">Rate limit</div><div class="v" id="rate-limit-value">-</div></div>
                </div>
              </div>
            </div>

            <div class="grid-two">
              <div class="panel" id="credits">
                <div class="panel-head"><strong>Load credits</strong><span class="pill">Dodo Payments</span></div>
                <div class="panel-body stack">
                  <div class="muted">Pick a credit pack and send the customer to checkout. The webhook will add the credits after payment succeeds.</div>
                  <div class="hero-actions" id="credit-packs"></div>
                  <div class="muted" id="checkout-status"></div>
                </div>
              </div>

              <div class="panel" id="keys">
                <div class="panel-head"><strong>API keys</strong><span class="pill">unlimited</span></div>
                <div class="panel-body stack">
                  <div class="grid-two">
                    <label class="field"><label for="key-name">Key name</label><input id="key-name" type="text" placeholder="Production" /></label>
                    <div class="stack" style="justify-content:end; display:flex;"><button class="button primary" id="create-key-btn">Create key</button></div>
                  </div>
                  <div class="muted" id="new-key-secret"></div>
                  <table class="table">
                    <thead><tr><th>Name</th><th>Prefix</th><th>Status</th><th></th></tr></thead>
                    <tbody id="keys-body"><tr><td colspan="4" class="muted">Loading...</td></tr></tbody>
                  </table>
                </div>
              </div>
            </div>

            <div class="grid-two">
              <div class="panel" id="usage">
                <div class="panel-head"><strong>Recent usage</strong><span class="pill">logged requests</span></div>
                <div class="panel-body stack">
                  <table class="table"><thead><tr><th>Model</th><th>Tokens</th><th>Cost</th></tr></thead><tbody id="usage-body"><tr><td colspan="3" class="muted">Loading...</td></tr></tbody></table>
                </div>
              </div>

              <div class="panel" id="api">
                <div class="panel-head"><strong>SDK quickstart</strong><span class="pill">OpenAI format</span></div>
                <div class="panel-body stack">
                  <div class="muted">Use any key generated here with the OpenAI client. The endpoint stays compatible with `/v1/chat/completions`.</div>
                  <pre class="terminal" id="sdk-snippet"></pre>
                  <label class="field"><label for="model-select">Model</label><select id="model-select"></select></label>
                  <label class="field"><label for="prompt">Prompt</label><textarea id="prompt" placeholder="Ask your model something short."></textarea></label>
                  <div class="hero-actions"><button class="button primary" id="send-btn">Send request</button><button class="button" id="refresh-btn">Refresh data</button></div>
                  <pre class="terminal" id="output">Waiting for request...</pre>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    """
    scripts = f"""
      const PACKS = {packs_json};
      const sessionStatus = document.getElementById('session-status');
      const keysBody = document.getElementById('keys-body');
      const usageBody = document.getElementById('usage-body');
      const modelSelect = document.getElementById('model-select');
      const output = document.getElementById('output');
      const accountEmail = document.getElementById('account-email');
      const planValue = document.getElementById('plan-value');
      const creditsValue = document.getElementById('credits-value');
      const rateLimitValue = document.getElementById('rate-limit-value');
      const sdkSnippet = document.getElementById('sdk-snippet');
      const checkoutStatus = document.getElementById('checkout-status');
      const newKeySecret = document.getElementById('new-key-secret');
      const packContainer = document.getElementById('credit-packs');

      function money(cents) {{ return '$' + (Number(cents || 0) / 100).toFixed(2); }}
      function getSessionEmail() {{ return localStorage.getItem('openrouter_account_email') || ''; }}

      function renderSdkSnippet(key='YOUR_API_KEY') {{
        sdkSnippet.textContent = `from openai import OpenAI\n\nclient = OpenAI(\n  api_key="${{key}}",\n  base_url="{SETTINGS.base_url}/v1",\n)\n\nresponse = client.chat.completions.create(\n  model="deepseek-v4-flash",\n  messages=[{{"role": "user", "content": "Hello"}}],\n)\nprint(response.choices[0].message.content)`;
      }}

      async function ensureSession() {{
        const res = await fetch('/auth/me');
        if (!res.ok) {{ window.location.href = '/login'; return null; }}
        return await res.json();
      }}

      async function loadAccount() {{
        const me = await ensureSession();
        if (!me) return;
        accountEmail.textContent = me.email;
        planValue.textContent = me.plan;
        creditsValue.textContent = money(me.credits_cents);
        rateLimitValue.textContent = String(me.rate_limit_per_minute) + '/min';
        sessionStatus.textContent = 'Signed in';
        sessionStatus.style.background = '#e9f7ef';
        sessionStatus.style.color = '#0f7b49';
        localStorage.setItem('openrouter_account_email', me.email);
        renderSdkSnippet(localStorage.getItem('openrouter_api_key') || 'YOUR_API_KEY');
      }}

      async function loadModels() {{
        const res = await fetch('/v1/models', {{ headers: {{ 'X-API-Key': localStorage.getItem('openrouter_api_key') || '' }} }});
        const payload = await res.json();
        const models = payload.data || [];
        modelSelect.innerHTML = '';
        models.forEach((model) => {{
          const opt = document.createElement('option');
          opt.value = model.id;
          opt.textContent = model.id;
          modelSelect.appendChild(opt);
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
          row.innerHTML = `<td>${{key.name}}</td><td>${{key.prefix}}</td><td>${{key.active ? 'Active' : 'Revoked'}}</td><td>${{key.active ? '<button class="button small" data-id="' + key.id + '">Revoke</button>' : ''}}</td>`;
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
        if (!items.length) {{
          usageBody.innerHTML = '<tr><td colspan="3" class="muted">No usage yet.</td></tr>';
          return;
        }}
        items.forEach((item) => {{
          const total = (item.tokens_in || 0) + (item.tokens_out || 0);
          const row = document.createElement('tr');
          row.innerHTML = `<td>${{item.model}}</td><td>${{total}}</td><td>${{money(item.cost_cents || 0)}}</td>`;
          usageBody.appendChild(row);
        }});
      }}

      function renderCreditPacks() {{
        packContainer.innerHTML = '';
        PACKS.forEach((amount) => {{
          const button = document.createElement('button');
          button.className = 'button';
          button.textContent = 'Add ' + money(amount);
          button.addEventListener('click', async () => {{
            checkoutStatus.textContent = 'Creating checkout...';
            const res = await fetch('/v1/billing/checkout', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ amount_cents: amount }}),
            }});
            const payload = await res.json();
            if (!res.ok) {{ checkoutStatus.textContent = payload.detail || 'Checkout failed'; return; }}
            window.location.href = payload.checkout_url;
          }});
          packContainer.appendChild(button);
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
        if (!res.ok) {{ newKeySecret.textContent = payload.detail || 'Could not create key'; return; }}
        localStorage.setItem('openrouter_api_key', payload.secret);
        newKeySecret.textContent = 'New secret created. Copy it now: ' + payload.secret;
        renderSdkSnippet(payload.secret);
        await loadKeys();
      }});

      document.getElementById('send-btn').addEventListener('click', async () => {{
        const model = modelSelect.value;
        const prompt = document.getElementById('prompt').value.trim();
        const apiKey = localStorage.getItem('openrouter_api_key') || '';
        if (!apiKey) {{ output.textContent = 'Create an API key first.'; return; }}
        if (!prompt) {{ output.textContent = 'Enter a prompt.'; return; }}
        const res = await fetch('/v1/chat/completions', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey }},
          body: JSON.stringify({{ model, messages: [{{ role: 'user', content: prompt }}] }}),
        }});
        output.textContent = await res.text();
        await Promise.all([loadUsage(), loadAccount()]);
      }});

      document.getElementById('refresh-btn').addEventListener('click', async () => {{
        await Promise.all([loadAccount(), loadModels(), loadKeys(), loadUsage()]);
      }});

      document.getElementById('logout-btn').addEventListener('click', async () => {{
        await fetch('/auth/logout', {{ method: 'POST' }});
        window.location.href = '/';
      }});

      renderCreditPacks();
      const checkoutState = new URLSearchParams(window.location.search).get('checkout');
      if (checkoutState === 'success') {{ checkoutStatus.textContent = 'Checkout completed. Credits update after payment confirmation.'; }}
      if (checkoutState === 'cancelled') {{ checkoutStatus.textContent = 'Checkout cancelled.'; }}
      Promise.all([loadAccount(), loadModels(), loadKeys(), loadUsage()]).catch(() => {{ window.location.href = '/login'; }});
      renderSdkSnippet(localStorage.getItem('openrouter_api_key') || 'YOUR_API_KEY');
    """
    return _shell(f'App | {SETTINGS.app_name}', body, scripts)
