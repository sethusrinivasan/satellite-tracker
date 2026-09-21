import inspect
from datetime import timedelta

from app.routes import auth
from config import Config


def test_google_oauth_does_not_force_account_picker():
    source = inspect.getsource(auth.init_oauth)
    assert "select_account" not in source
    assert "prompt" not in source
    assert "openid email profile" in source


def test_signed_in_admin_skips_google_login(client):
    with client.session_transaction() as sess:
        sess["admin_user"] = {
            "email": "dev-admin@localhost",
            "name": "Dev Admin",
            "is_dev_bypass": True,
        }
    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 302
    assert "/admin" in response.headers.get("Location", "")


def test_login_page_offers_local_skip_and_does_not_auto_google(app, client):
    app.config["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
    response = client.get("/auth/login", headers={"Host": "0.0.0.0:5000"})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "accounts.google.com" not in html
    assert "OAuth Not Configured" not in html
    assert "Continue without sign-in" in html
    assert 'id="local-admin-continue-btn"' in html
    assert "Not for production" in html
    assert 'id="google-signin-btn"' not in html


def test_placeholder_google_client_ids_are_rejected():
    assert not auth.is_valid_google_client_id("your-google-client-id.apps.googleusercontent.com")
    assert not auth.is_valid_google_client_id("test-client-id.apps.googleusercontent.com")
    assert not auth.is_valid_google_client_id("")
    assert auth.is_valid_google_client_id("1234567890-abcdef.apps.googleusercontent.com")


def test_login_hides_skip_when_not_local(app, client, monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    app.config["GOOGLE_CLIENT_ID"] = ""
    response = client.get("/auth/login", headers={"Host": "example.com"})
    html = response.get_data(as_text=True)
    assert "Continue without sign-in" not in html
    assert "not available" in html


def test_is_local_dev_accepts_zero_bind_host(app):
    with app.test_request_context("/", headers={"Host": "0.0.0.0:5000"}):
        assert auth.is_local_dev() is True


def test_admin_session_lifetime_defaults_to_fourteen_days():
    assert Config.SESSION_PERMANENT is True
    assert Config.PERMANENT_SESSION_LIFETIME == timedelta(days=14)
    assert Config.SESSION_COOKIE_HTTPONLY is True
    assert Config.SESSION_COOKIE_SAMESITE == "Lax"
