from app.ui import render_app_page, render_landing_page, render_login_page, render_signup_page


def test_landing_page_contains_customer_ctas() -> None:
    html = render_landing_page()

    assert 'Get access' in html
    assert 'Sign in' in html
    assert 'OpenAI-compatible' in html


def test_login_page_contains_access_key_flow() -> None:
    html = render_login_page()

    assert 'Access key' in html
    assert 'Sign in' in html
    assert '/app' in html


def test_signup_page_contains_onboarding_fields() -> None:
    html = render_signup_page()

    assert 'Request access' in html
    assert 'Work email' in html
    assert 'Use case' in html


def test_app_page_contains_dashboard_panels() -> None:
    html = render_app_page()

    assert 'Workspace overview' in html
    assert 'Recent usage' in html
    assert 'API console' in html
