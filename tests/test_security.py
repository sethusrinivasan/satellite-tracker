import pytest

from app import create_app, db
from app.routes.auth import is_admin_email_allowed
from app.services.query_cache import (
    cache_user_verified_query,
    get_cached_query,
    validate_sql_for_cache,
)


class TestConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = "/tmp/sat_tracker_test_uploads"
    GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET = "test-client-secret"
    ADMIN_ALLOWED_EMAILS = ""
    ADMIN_ALLOW_ANY = False


@pytest.fixture
def app():
    app = create_app(config_object=TestConfig)
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


def test_validate_sql_for_cache_rejects_mutation_sql():
    assert validate_sql_for_cache("SELECT norad_cat_id FROM satellites LIMIT 10")
    assert not validate_sql_for_cache("UPDATE satellites SET name = 'x'")
    assert not validate_sql_for_cache("SELECT 1; DROP TABLE satellites")
    assert not validate_sql_for_cache("DELETE FROM satellites")


def test_cache_user_verified_query_allows_safe_sql(app):
    with app.app_context():
        entry = cache_user_verified_query(
            "Find Starlink satellites",
            "SELECT norad_cat_id FROM satellites WHERE name LIKE '%Starlink%' LIMIT 5",
            category="user_verified",
        )
        assert entry["verified"] is True
        cached = get_cached_query("Find Starlink satellites")
        assert cached is not None
        assert cached["sql"].startswith("SELECT")


def test_cache_user_verified_query_rejects_unsafe_sql(app):
    with app.app_context():
        with pytest.raises(ValueError, match="Only read-only SELECT SQL may be cached"):
            cache_user_verified_query("bad prompt", "DROP TABLE satellites")


def test_admin_allowlist_fails_closed(app):
    with app.test_request_context("/"):
        assert not is_admin_email_allowed("someone@example.com")


def test_cache_feedback_requires_admin_login(client):
    response = client.post(
        "/api/ai/cache-feedback",
        json={
            "prompt": "Find Starlink satellites",
            "sql": "SELECT norad_cat_id FROM satellites LIMIT 5",
            "feedback": "positive",
        },
    )
    assert response.status_code == 302
    assert "/auth/login" in response.headers.get("Location", "")
