import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-prod"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")
    DATASTORE_CONFIG_PATH = os.path.join(BASE_DIR, "instance", "datastore.json")
    DATASTORE_CONFIGURED = False

    # ── Google OAuth2 ─────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Comma-separated list of Google account email addresses allowed to access
    # the admin panel. When empty in production, access is denied unless a local
    # dev override is explicitly enabled.
    ADMIN_ALLOWED_EMAILS = os.environ.get("ADMIN_ALLOWED_EMAILS", "")
    ADMIN_ALLOW_ANY = os.environ.get("ADMIN_ALLOW_ANY", "false").lower() in {"1", "true", "yes"}

    # Soft Google sign-in: keep the signed session so return visits skip the consent screen.
    SESSION_PERMANENT = True
    try:
        _session_days = int(os.environ.get("ADMIN_SESSION_DAYS", "14"))
    except (TypeError, ValueError):
        _session_days = 14
    PERMANENT_SESSION_LIFETIME = timedelta(days=max(1, _session_days))
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get(
        "SESSION_COOKIE_SECURE",
        "true" if (os.environ.get("FLASK_ENV") or "").lower() == "production" else "false",
    ).lower() in {"1", "true", "yes"}

    # Optional CARTO basemap key (https://carto.com/basemaps/apikey/). Empty = Esri dark gray (no key).
    CARTO_API_KEY = os.environ.get("CARTO_API_KEY", "")

    # PostHog web analytics. Empty key = snippet not loaded.
    POSTHOG_PROJECT_API_KEY = os.environ.get("POSTHOG_PROJECT_API_KEY", "")
    POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")
    POSTHOG_SESSION_REPLAY = os.environ.get("POSTHOG_SESSION_REPLAY", "false").lower() in {"1", "true", "yes"}
