from app.ui import render_app_page, render_landing_page, render_login_page, render_signup_page


def test_landing_page_contains_customer_ctas() -> None:
    html = render_landing_page()

    assert 'Get access' in html
    assert 'Sign in' in html
    assert 'Five OSS models only' in html


def test_login_page_contains_auth_flow() -> None:
    html = render_login_page()

    assert 'Sign in' in html
    assert 'session cookie' in html
    assert '/auth/login' in html


def test_signup_page_contains_onboarding_fields() -> None:
    html = render_signup_page()

    assert 'Create workspace' in html
    assert 'Work email' in html
    assert 'Password' in html


def test_app_page_contains_dashboard_panels() -> None:
    html = render_app_page()

    assert 'Workspace overview' in html
    assert 'API keys' in html
    assert 'Load credits' in html
    assert 'SDK quickstart' in html
