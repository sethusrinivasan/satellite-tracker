import os

import pytest

from app import create_app, db


class TestConfig:
    SECRET_KEY = "test-secret-key"
    TESTING = True
    DATASTORE_CONFIGURED = True
    DATASTORE_ENGINE = "sqlite"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = "/tmp/sat_tracker_test_uploads"
    GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET = "test-client-secret"
    ADMIN_ALLOWED_EMAILS = ""
    ADMIN_ALLOW_ANY = False
    DATASTORE_CONFIG_PATH = "/tmp/sat_tracker_test_datastore.json"
    POSTHOG_PROJECT_API_KEY = ""
    POSTHOG_HOST = "https://us.i.posthog.com"
    POSTHOG_SESSION_REPLAY = False
    SESSION_PERMANENT = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


@pytest.fixture(autouse=True)
def overlay_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("OVERLAY_CACHE_DIR", str(tmp_path / "overlay_cache"))
    from app.services import overlay_cache

    overlay_cache._memory.clear()
    overlay_cache.reset_runtime_state()
    from app.services import overlay_http
    overlay_http.reset_runtime_state()


@pytest.fixture
def app():
    application = create_app(config_object=TestConfig)
    application.config["TESTING"] = True
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    with app.test_client() as test_client:
        yield test_client
