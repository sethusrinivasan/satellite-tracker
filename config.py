import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-prod"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "satellites.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")

    # ── Google OAuth2 ─────────────────────────────────────────────────────────
    # Set these in your environment (or a .env file).
    # Get credentials at: https://console.cloud.google.com/apis/credentials
    GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Comma-separated list of Google account email addresses allowed to access
    # the admin panel. When empty in production, access is denied unless a local
    # dev override is explicitly enabled.
    ADMIN_ALLOWED_EMAILS = os.environ.get("ADMIN_ALLOWED_EMAILS", "")
    ADMIN_ALLOW_ANY = os.environ.get("ADMIN_ALLOW_ANY", "false").lower() in {"1", "true", "yes"}
