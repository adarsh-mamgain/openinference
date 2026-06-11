from app.ui import render_app_page, render_landing_page, render_login_page, render_signup_page


def test_landing_page_shows_models_pricing_and_cta() -> None:
    html = render_landing_page()

    assert 'Five model families. One endpoint.' in html
    assert 'Top up credits' in html
    assert 'Common questions' in html
    assert 'Start for free' in html
    assert '/signup' in html


def test_login_page_focuses_on_workspace_access() -> None:
    html = render_login_page()

    assert 'Sign in' in html
    assert 'Access your workspace, keys, and usage logs.' in html
    assert 'Create a workspace' in html


def test_signup_page_moves_users_into_funding_flow() -> None:
    html = render_signup_page()

    assert 'Create workspace' in html
    assert 'No card needed to register.' in html
    assert 'Usage logs and spend tracking' in html


def test_dashboard_page_emphasizes_credits_keys_and_models() -> None:
    html = render_app_page()

    assert 'Top up credits' in html
    assert 'Available models' in html
    assert 'API Keys' in html
    assert 'Python snippet' in html
    assert 'Recent requests' in html
